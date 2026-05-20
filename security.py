"""
安全模块 — 输入校验、密码管理、令牌认证。

ESP32-P4 资源有限，HTTPS 不可行，采用以下措施:
    - WiFi 密码从文件加载（可修改，不复用默认密码）
    - API 令牌认证（简单共享密钥）
    - 输入净化（防路径穿越、JSON 注入）
    - 速率限制（防暴力破解）
"""

import json
import time

# MicroPython / CPython 兼容
if hasattr(time, 'time'):
    _time = time.time
else:
    _time = lambda: 0


# ====== 密码管理 ======

SECURITY_FILE = "/sd/security.json"

DEFAULT_CONFIG = {
    "wifi_ssid": "Microscope",
    "wifi_password": "12345678",
    "api_token": "",           # 空 = 不启用令牌认证
    "token_required": False,
}


def load_security(filepath=SECURITY_FILE):
    """加载安全配置。不存在时返回默认值。"""
    try:
        with open(filepath, "r") as f:
            saved = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(saved)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_security(cfg, filepath=SECURITY_FILE):
    """保存安全配置。"""
    try:
        with open(filepath, "w") as f:
            json.dump(cfg, f)
        return True
    except Exception:
        return False


def update_password(new_password: str, filepath=SECURITY_FILE):
    """修改 WiFi 密码。

    Args:
        new_password: 新密码 (8-63 字符 ASCII)
    """
    if len(new_password) < 8:
        raise ValueError("密码至少 8 位")
    if len(new_password) > 63:
        raise ValueError("密码最长 63 位")
    if not all(32 <= ord(c) < 127 for c in new_password):
        raise ValueError("密码只能包含 ASCII 可打印字符")

    cfg = load_security(filepath)
    cfg["wifi_password"] = new_password
    return save_security(cfg, filepath)


def update_ssid(new_ssid: str, filepath=SECURITY_FILE):
    """修改 WiFi SSID。

    Args:
        new_ssid: 新 SSID (1-32 字符)
    """
    stripped = new_ssid.strip()
    if len(stripped) < 1 or len(stripped) > 32:
        raise ValueError("SSID 长度须在 1-32 字符之间")
    cfg = load_security(filepath)
    cfg["wifi_ssid"] = stripped
    return save_security(cfg, filepath)


def update_api_token(new_token: str, filepath=SECURITY_FILE):
    """设置 API 令牌。空字符串 = 禁用令牌认证。"""
    if new_token and (len(new_token) < 8 or len(new_token) > 128):
        raise ValueError("令牌长度须在 8-128 字符之间")
    cfg = load_security(filepath)
    cfg["api_token"] = new_token
    cfg["token_required"] = bool(new_token)
    return save_security(cfg, filepath)


# ====== 输入校验 ======

def sanitize_filename(name: str) -> str:
    """净化文件名，移除危险字符。

    Returns:
        安全文件名，如果输入非法返回空字符串。
    """
    if not name or len(name) > 255:
        return ""

    # 禁止路径穿越
    if ".." in name or "/" in name or "\\" in name:
        return ""

    # 禁止控制字符
    for ch in name:
        if ord(ch) < 32:
            return ""

    return name


def validate_command(cmd: str, allowed: set) -> bool:
    """检查语音命令是否在白名单内。"""
    return cmd in allowed


def sanitize_json_key(key: str, max_len=64) -> str:
    """净化 JSON 键名。"""
    if len(key) > max_len:
        return ""
    if not key.replace("_", "").replace("-", "").isalnum():
        return ""
    return key


def validate_ip(ip: str) -> bool:
    """验证 IPv4 地址格式。"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        try:
            n = int(p)
            if n < 0 or n > 255:
                return False
        except ValueError:
            return False
    return True


# ====== 令牌认证 ======

class TokenAuth:
    """简单令牌认证中间件。

    Args:
        token: 共享密钥令牌，空 = 不启用
    """

    def __init__(self, token=""):
        self._token = token

    @property
    def enabled(self):
        return bool(self._token)

    def check(self, request_headers: dict) -> bool:
        """校验请求是否带有有效令牌。

        支持两种传递方式:
            - Authorization: Bearer <token>
            - X-API-Token: <token>
        """
        if not self._token:
            return True

        auth = request_headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth[7:] == self._token:
            return True

        if request_headers.get("X-API-Token", "") == self._token:
            return True

        return False


# ====== 速率限制 ======

class RateLimiter:
    """简易速率限制器（基于时间窗口计数）。

    Args:
        max_requests: 窗口内最大请求数
        window_sec: 时间窗口 (秒)
    """

    def __init__(self, max_requests=30, window_sec=60):
        self._max_requests = max_requests
        self._window_sec = window_sec
        self._counters = {}  # key → [count, window_start]

    def allow(self, key="global") -> bool:
        """检查是否允许此次请求。"""
        now = _time()
        count, window_start = self._counters.get(key, (0, now))

        if now - window_start > self._window_sec:
            count = 0
            window_start = now

        if count >= self._max_requests:
            return False

        self._counters[key] = (count + 1, window_start)
        return True

    def reset(self, key="global"):
        self._counters.pop(key, None)
