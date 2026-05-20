"""
ESP32-P4 智能显微镜 — 全局配置
"""

# ====== GPIO 引脚定义 ======

# X 轴 (ULN2003 IN1-4)
X_AXIS_PINS = (4, 5, 6, 7)
# Y 轴 (ULN2003 IN1-4)
Y_AXIS_PINS = (8, 9, 10, 11)
# Z 轴 (ULN2003 IN1-4)
Z_AXIS_PINS = (12, 13, 14, 15)

# LED PWM
LED_PIN = 21

# 限位开关（常开，触发=低电平）
LIMIT_X_PIN = 2
LIMIT_Y_PIN = 3

# ====== 步进电机参数 ======

# 半步模式每转步数 (28BYJ-48)
STEPS_PER_REV = 4096

# 默认步间延迟 (ms)，数值越大越慢
# 28BYJ-48 最高约 600Hz → 最小延迟约 1.7ms
SPEED_PRESETS = {
    "快": 2,
    "中": 4,
    "慢": 8,
}
DEFAULT_SPEED = "中"

# ====== 运动学校准 ======

# 丝杆导程 (mm/转) — 取决于具体机械结构，参考 OpenFlexure
LEAD_SCREW_PITCH_MM = 0.8

# 校准系数 (μm/步)
# 0.8mm / 4096步 ≈ 0.195μm/步
UM_PER_STEP = (LEAD_SCREW_PITCH_MM * 1000) / STEPS_PER_REV

# 行程范围 (μm)，默认 ±10mm
TRAVEL_LIMIT_UM = {
    "x": (-10000, 10000),
    "y": (-10000, 10000),
    "z": (-5000, 5000),  # Z 轴对焦行程较短
}

# 回零方向（向限位开关移动）：-1 或 1
HOME_DIRECTION = {"x": -1, "y": -1, "z": -1}

# 回零后初始位置 (μm)
HOME_POSITION_UM = {"x": 0, "y": 0, "z": 5000}

# ====== LED 参数 ======

PWM_FREQ = 1000        # 1kHz 无闪烁
PWM_MAX_DUTY = 1023     # 10 位分辨率

LED_PRESETS = {
    "暗": 20,
    "中": 50,
    "亮": 80,
    "最亮": 100,
}

# ====== WiFi 参数 ======

# 从 /sd/security.json 加载，如果不存在则使用以下默认值
WIFI_SSID = "Microscope"
WIFI_PASSWORD = "12345678"
WIFI_SECURITY_FILE = "/sd/security.json"
HTTP_PORT = 80

def _load_wifi_settings():
    """从安全配置文件加载 WiFi 设置，失败则用默认值。"""
    try:
        import json
        with open(WIFI_SECURITY_FILE, "r") as f:
            cfg = json.load(f)
        return cfg.get("wifi_ssid", WIFI_SSID), cfg.get("wifi_password", WIFI_PASSWORD)
    except Exception:
        return WIFI_SSID, WIFI_PASSWORD

# 模块级属性 — MicroPython 启动时自动加载
try:
    WIFI_SSID, WIFI_PASSWORD = _load_wifi_settings()
except Exception:
    pass

# ====== 系统参数 ======

MAX_PRESETS = 6
PRESETS_FILE = "/sd/presets.json"

# ====== 摄像头参数 ======

# DVP 接口引脚 (OV2640 / OV5640)
CAM_PIN_XCLK = 43
CAM_PIN_SIOD = 44   # I2C SDA
CAM_PIN_SIOC = 45   # I2C SCL
CAM_PIN_D7 = 39
CAM_PIN_D6 = 40
CAM_PIN_D5 = 41
CAM_PIN_D4 = 42
CAM_PIN_D3 = 11
CAM_PIN_D2 = 12
CAM_PIN_D1 = 13
CAM_PIN_D0 = 14
CAM_PIN_VSYNC = 47
CAM_PIN_HREF = 38
CAM_PIN_PCLK = 8
CAM_PIN_PWDN = -1   # -1 = 不使用

# 默认分辨率
CAM_DEFAULT_WIDTH = 800
CAM_DEFAULT_HEIGHT = 600
CAM_DEFAULT_FORMAT = "JPEG"  # JPEG / RGB565

# 自动曝光和白平衡
CAM_AUTO_EXPOSURE = True
CAM_AUTO_WHITE_BALANCE = True

# 帧率
CAM_FPS = 15
