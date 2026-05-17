"""
ESP32-P4 智能显微镜 — 主入口

Waveshare ESP32-P4-WIFI6-Touch-LCD-4B:
- 4" 720×720 IPS + GT911 触控
- ESP32-C6 WiFi 6 协处理
- 3 × 28BYJ-48 + ULN2003 步进电机驱动
- LED PWM 照明

启动流程: 硬件初始化 → 系统自检 → WiFi 启动 → UI 就绪 → 事件循环
"""

import time
import _thread
import config

# ====== 日志 ======

def log(msg):
    print(f"[显微镜] {msg}")


# ====== 阶段1: 显示和触控初始化 ======

def _init_display():
    """初始化 720×720 IPS 显示屏。

    Waveshare 提供 lvgl 绑定的显示驱动，具体初始化取决于
    MicroPython 固件配置。此处为典型初始化流程。
    """
    try:
        import lvgl as lv

        # 如果固件已预初始化显示，直接获取屏幕对象
        scr = lv.screen_active()
        if scr:
            log("显示已预初始化")
            return

        # 否则手动初始化（依赖固件提供的 display 模块）
        import display
        display.init()
        log("显示初始化完成")
    except ImportError:
        log("警告: lvgl/display 模块未找到，运行在无屏模式")


def _init_touch():
    """初始化 GT911 电容触摸 (I2C 地址 0x5D)。"""
    try:
        import touch
        touch.init()
        log("GT911 触摸初始化完成")
    except ImportError:
        log("警告: touch 模块未找到，无触控输入")
    except Exception as e:
        log(f"警告: 触摸初始化失败 ({e})")


# ====== 阶段2: 系统模块初始化 ======

def _init_stage():
    """初始化 3 轴电动云台。"""
    from stage_controller import StageController

    stage = StageController(
        x_pins=config.X_AXIS_PINS,
        y_pins=config.Y_AXIS_PINS,
        z_pins=config.Z_AXIS_PINS,
        limit_x_pin=config.LIMIT_X_PIN,
        limit_y_pin=config.LIMIT_Y_PIN,
    )
    log("3 轴云台初始化完成")
    return stage


def _init_led():
    """初始化 LED 照明。"""
    from led_controller import LedController

    led = LedController(
        pin=config.LED_PIN,
        freq=config.PWM_FREQ,
        max_duty=config.PWM_MAX_DUTY,
    )
    # 启动时点亮到中档亮度
    led.set_brightness(50)
    led.on()
    log("LED 照明初始化完成")
    return led


def _init_system(stage, led):
    """初始化系统管理器。"""
    from system_manager import SystemManager

    sys_mgr = SystemManager(stage, led, presets_file=config.PRESETS_FILE)
    log("系统管理器初始化完成")
    return sys_mgr


# ====== 阶段3: WiFi 服务 ======

def _init_wifi():
    """初始化 WiFi 并返回本机 IP。"""
    try:
        import network

        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=config.WIFI_SSID, password=config.WIFI_PASSWORD,
                   authmode=network.AUTH_WPA_WPA2_PSK)
        # 等待 AP 就绪
        for _ in range(20):
            if ap.active():
                break
            time.sleep(0.5)

        if ap.active():
            ip = ap.ifconfig()[0]
            log(f"WiFi AP 就绪: {config.WIFI_SSID} @ {ip}")
            return ip
        else:
            log("警告: WiFi AP 启动超时")
            return None
    except ImportError:
        log("警告: network 模块未找到，WiFi 不可用")
        return None
    except Exception as e:
        log(f"警告: WiFi 初始化失败 ({e})")
        return None


def _start_wifi_server(system_mgr, stage, led):
    """在后台线程启动 WiFi HTTP 服务器。"""
    from wifi_server import WifiServer

    server = WifiServer(system_mgr, stage, led)
    try:
        _thread.start_new_thread(server._serve, ())
        log(f"HTTP API 服务器已启动 (端口 {config.HTTP_PORT})")
    except Exception as e:
        log(f"警告: WiFi 服务器线程启动失败 ({e})")
    return server


# ====== 阶段4: UI 启动 ======

def _init_ui(stage, led, sys_mgr):
    """创建并返回 TouchUI 实例。"""
    try:
        import lvgl as lv
        from touch_ui import TouchUI

        ui = TouchUI(stage, led, sys_mgr)
        log("触摸界面就绪")
        return ui
    except ImportError:
        log("警告: 无法加载 UI，运行在无屏模式")
        return None
    except Exception as e:
        log(f"警告: UI 初始化失败 ({e})")
        return None


# ====== 主入口 ======

def main():
    log("ESP32-P4 智能显微镜 启动中...")
    log(f"版本 1.0.0 — 广东童园科技有限公司")

    # 阶段1: 显示和触控
    _init_display()
    _init_touch()

    # 阶段2: 系统模块
    stage = _init_stage()
    led = _init_led()
    sys_mgr = _init_system(stage, led)

    # 阶段3: WiFi 服务
    ip = _init_wifi()
    if ip:
        _start_wifi_server(sys_mgr, stage, led)

    # 阶段4: UI
    ui = _init_ui(stage, led, sys_mgr)

    # ====== 主事件循环 ======
    log("系统就绪")

    if ui is not None:
        # LVGL 事件循环模式
        try:
            import lvgl as lv
            while True:
                lv.timer_handler_run_in_period(5)  # ±5ms
                time.sleep_ms(5)
        except KeyboardInterrupt:
            log("用户中断")
        except Exception as e:
            log(f"事件循环异常: {e}")
    else:
        # 无屏模式：仅保持 WiFi 服务运行
        log("运行在无屏模式，按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("用户中断")

    # ====== 清理 ======
    log("正在关机...")
    try:
        stage.release_all()
    except Exception:
        pass
    log("安全关机完成")


# MicroPython 自动执行
if __name__ == "__main__":
    main()
