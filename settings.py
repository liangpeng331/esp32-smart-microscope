"""
系统设置持久化

用户配置保存在 /sd/settings.json，启动时自动恢复。
包含：速度档位、点动步长、LED 亮度、摄像头参数。
"""

import json


SETTINGS_FILE = "/sd/settings.json"

DEFAULTS = {
    "speed": "中",
    "step_size": 100,
    "led_brightness": 50,
    "cam_width": 800,
    "cam_height": 600,
    "cam_fps": 15,
    "autofocus_range": (-500, 500),
    "autofocus_step": 50,
    "timelapse_interval": 5,
    "timelapse_count": 10,
    "language": "zh",
}


def load(filepath=SETTINGS_FILE):
    """从 JSON 文件加载设置，缺失键用默认值补全。

    Returns:
        dict: 设置字典
    """
    settings = dict(DEFAULTS)
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        settings.update(data)
    except (OSError, ValueError):
        pass
    return settings


def save(settings, filepath=SETTINGS_FILE):
    """将设置字典写入 JSON 文件。

    Args:
        settings: 要保存的设置字典
        filepath: 文件路径
    """
    try:
        with open(filepath, "w") as f:
            json.dump(settings, f)
        return True
    except OSError:
        return False


def update(key, value, filepath=SETTINGS_FILE):
    """更新单个设置项并持久化。

    Args:
        key: 设置键名
        value: 新值
        filepath: 文件路径
    """
    settings = load(filepath)
    settings[key] = value
    return save(settings, filepath)


def reset(filepath=SETTINGS_FILE):
    """恢复默认设置。"""
    return save(dict(DEFAULTS), filepath)