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
    led.set_brightness(50)
    led.on()
    log("LED 照明初始化完成")
    return led


def _init_camera():
    """初始化摄像头。"""
    from camera_controller import CameraController

    cam = CameraController(
        width=config.CAM_DEFAULT_WIDTH,
        height=config.CAM_DEFAULT_HEIGHT,
        fmt=config.CAM_DEFAULT_FORMAT,
        fps=config.CAM_FPS,
    )
    cam.init(
        xclk_pin=config.CAM_PIN_XCLK,
        siod_pin=config.CAM_PIN_SIOD,
        sioc_pin=config.CAM_PIN_SIOC,
        d7_pin=config.CAM_PIN_D7,
        d6_pin=config.CAM_PIN_D6,
        d5_pin=config.CAM_PIN_D5,
        d4_pin=config.CAM_PIN_D4,
        d3_pin=config.CAM_PIN_D3,
        d2_pin=config.CAM_PIN_D2,
        d1_pin=config.CAM_PIN_D1,
        d0_pin=config.CAM_PIN_D0,
        vsync_pin=config.CAM_PIN_VSYNC,
        href_pin=config.CAM_PIN_HREF,
        pclk_pin=config.CAM_PIN_PCLK,
        pwdn_pin=config.CAM_PIN_PWDN,
    )
    log("摄像头初始化完成")
    return cam


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


def _start_wifi_server(system_mgr, stage, led, cam=None, ae=None, ca=None):
    """在后台线程启动 WiFi HTTP 服务器。"""
    from wifi_server import WifiServer

    server = WifiServer(system_mgr, stage, led, cam, ae, ca)
    try:
        _thread.start_new_thread(server._serve, ())
        log(f"HTTP API 服务器已启动 (端口 {config.HTTP_PORT})")
    except Exception as e:
        log(f"警告: WiFi 服务器线程启动失败 ({e})")
    return server


# ====== 阶段4: UI 启动 ======

def _init_ui(stage, led, sys_mgr, cam=None, voice=None, ae=None):
    """创建并返回 TouchUI 实例。"""
    try:
        import lvgl as lv
        from touch_ui import TouchUI

        ui = TouchUI(stage, led, sys_mgr, cam, voice, ae)
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
    log("版本 1.2.0")

    # 阶段1: 显示和触控
    _init_display()
    _init_touch()

    # 阶段2: 系统模块
    stage = _init_stage()
    led = _init_led()
    cam = _init_camera()
    sys_mgr = _init_system(stage, led)

    # 加载用户设置
    try:
        import settings
        prefs = settings.load()
        stage.set_speed(prefs["speed"])
        led.set_brightness(prefs["led_brightness"])
        if prefs["led_brightness"] > 0:
            led.on()
        if cam._initialized:
            cam.set_resolution(prefs["cam_width"], prefs["cam_height"])
        log(f"用户设置已加载 (速度={prefs['speed']}, LED={prefs['led_brightness']}%)")
    except Exception as e:
        log(f"警告: 设置加载失败 ({e})")

    # 语音控制（可选）
    voice = None
    try:
        from voice_controller import VoiceController
        voice = VoiceController(sys_mgr, stage, led, cam)
        voice.init()
        log("语音控制初始化完成")
    except Exception as e:
        log(f"警告: 语音控制初始化失败 ({e})")

    # 细胞分析（可选）
    ca = None
    try:
        from cell_analyzer import CellAnalyzer
        ca = CellAnalyzer(cam)
        log("细胞分析模块初始化完成")
    except Exception as e:
        log(f"警告: 细胞分析初始化失败 ({e})")

    # 阶段3: WiFi 服务
    ip = _init_wifi()
    if ip:
        _start_wifi_server(sys_mgr, stage, led, cam, ae, ca)

    # 自动曝光（可选）
    ae = None
    try:
        from auto_exposure import AutoExposure
        ae = AutoExposure(cam, led)
        log("自动曝光就绪")
    except Exception as e:
        log(f"警告: 自动曝光初始化失败 ({e})")

    # 阶段4: UI
    ui = _init_ui(stage, led, sys_mgr, cam, voice, ae)

    # ====== 主事件循环 ======
    log("系统就绪")

    if ui is not None:
        try:
            import lvgl as lv
            while True:
                lv.timer_handler_run_in_period(5)
                # 自动曝光处理
                if ae is not None and ae.is_active():
                    ae.process()
                time.sleep_ms(5)
        except KeyboardInterrupt:
            log("用户中断")
        except Exception as e:
            log(f"事件循环异常: {e}")
    else:
        log("运行在无屏模式，按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("用户中断")

    # ====== 清理 ======
    log("正在关机...")
    # 保存用户设置
    try:
        import settings
        settings.update("speed", stage._speed if hasattr(stage, '_speed') else "中")
        settings.update("led_brightness", led.get_state()["brightness"])
        settings.update("cam_width", cam._width)
        settings.update("cam_height", cam._height)
        log("用户设置已保存")
    except Exception:
        pass
    try:
        cam.deinit()
    except Exception:
        pass
    try:
        stage.release_all()
    except Exception:
        pass
    log("安全关机完成")


# MicroPython 自动执行
if __name__ == "__main__":
    main()
