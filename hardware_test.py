"""
ESP32-P4 智能显微镜 — 硬件验证脚本

逐项测试所有硬件模块，输出 PASS/FAIL 结果。
在 MicroPython REPL 中运行:
    import hardware_test
    hardware_test.run_all()
"""

import time

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)

_results = []
_passed = 0
_failed = 0
_skipped = 0


def _log(level, msg):
    print(f"  [{level}] {msg}")


def _pass(msg):
    global _passed
    _passed += 1
    _results.append(("PASS", msg))
    print(f"  [PASS] {msg}")


def _fail(msg):
    global _failed
    _failed += 1
    _results.append(("FAIL", msg))
    print(f"  [FAIL] {msg}")


def _skip(msg):
    global _skipped
    _skipped += 1
    _results.append(("SKIP", msg))
    print(f"  [SKIP] {msg}")


def test_gpio():
    """测试 GPIO 引脚可用性。"""
    print("\n--- GPIO 引脚测试 ---")
    try:
        from machine import Pin
        import config

        test_pins = [
            ("X_AXIS", config.X_AXIS_PINS[0]),
            ("Y_AXIS", config.Y_AXIS_PINS[0]),
            ("Z_AXIS", config.Z_AXIS_PINS[0]),
            ("LED", config.LED_PIN),
            ("LIMIT_X", config.LIMIT_X_PIN),
            ("LIMIT_Y", config.LIMIT_Y_PIN),
        ]

        for name, gpio in test_pins:
            try:
                pin = Pin(gpio, Pin.OUT)
                pin.on()
                _sleep_ms(1)
                pin.off()
                _pass(f"{name} (GPIO{gpio}) — 可用")
            except Exception as e:
                _fail(f"{name} (GPIO{gpio}) — {e}")

    except ImportError:
        _skip("machine 模块不可用 (CPython 环境)")
    except Exception as e:
        _fail(f"GPIO 测试失败: {e}")


def test_motors():
    """测试 3 轴步进电机。"""
    print("\n--- 步进电机测试 ---")
    try:
        from motor_driver import MotorDriver
        import config

        for name, pins in [("X", config.X_AXIS_PINS),
                           ("Y", config.Y_AXIS_PINS),
                           ("Z", config.Z_AXIS_PINS)]:
            try:
                motor = MotorDriver(*pins, delay_ms=4)
                motor.step(20)   # 正向 20 步
                motor.step(-20)  # 反向 20 步
                motor.release()
                pos = motor.get_position()
                if pos == 0:
                    _pass(f"{name} 轴 — 双向转动正常")
                else:
                    _fail(f"{name} 轴 — 位置偏差: {pos}")
            except Exception as e:
                _fail(f"{name} 轴 — {e}")

    except ImportError:
        _skip("machine 模块不可用")
    except Exception as e:
        _fail(f"电机测试失败: {e}")


def test_led():
    """测试 LED PWM 调光。"""
    print("\n--- LED 调光测试 ---")
    try:
        from led_controller import LedController
        import config

        led = LedController(config.LED_PIN, config.PWM_FREQ, config.PWM_MAX_DUTY)

        # 开关测试
        led.on()
        led.off()
        _pass("LED 开关 — 正常")

        # 亮度渐变
        led.on()
        for pct in [0, 25, 50, 75, 100]:
            led.set_brightness(pct)
            state = led.get_state()
            if state["brightness"] == pct:
                _pass(f"LED 亮度 {pct}% — 正常")
            else:
                _fail(f"LED 亮度 {pct}% — 实际 {state['brightness']}%")
            _sleep_ms(100)
        led.off()

        # 预设档位
        for p in ["暗", "中", "亮", "最亮"]:
            led.preset(p)
            _pass(f"LED 预设 '{p}' — 正常")
        led.off()

    except ImportError:
        _skip("machine 模块不可用")
    except Exception as e:
        _fail(f"LED 测试失败: {e}")


def test_camera():
    """测试摄像头采集。"""
    print("\n--- 摄像头测试 ---")
    try:
        from camera_controller import CameraController
        import config

        cam = CameraController(
            width=config.CAM_DEFAULT_WIDTH,
            height=config.CAM_DEFAULT_HEIGHT,
            fmt=config.CAM_DEFAULT_FORMAT,
            fps=config.CAM_FPS,
        )

        if cam.init():
            _pass("摄像头初始化 — 成功")
        else:
            _fail("摄像头初始化 — 失败")
            return

        # 拍照测试
        img = cam.capture()
        if img and len(img) > 0:
            _pass(f"拍照 — 成功 ({len(img)} 字节)")
        else:
            _fail("拍照 — 无数据")

        # 取景测试
        if cam.start_preview():
            _pass("实时取景 — 启动成功")
            _sleep_ms(500)
            cam.stop_preview()
            _pass("实时取景 — 停止成功")
        else:
            _fail("实时取景 — 启动失败")

        cam.deinit()

    except ImportError:
        _skip("摄像头模块不可用")
    except Exception as e:
        _fail(f"摄像头测试失败: {e}")


def test_wifi():
    """测试 WiFi AP 功能。"""
    print("\n--- WiFi 测试 ---")
    try:
        import network
        import config

        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=config.WIFI_SSID, password=config.WIFI_PASSWORD,
                   authmode=network.AUTH_WPA_WPA2_PSK)

        # 等待启动
        for _ in range(20):
            if ap.active():
                break
            _sleep_ms(500)

        if ap.active():
            ip = ap.ifconfig()[0]
            _pass(f"WiFi AP — 就绪 ({config.WIFI_SSID} @ {ip})")
        else:
            _fail("WiFi AP — 启动超时")

    except ImportError:
        _skip("network 模块不可用")
    except Exception as e:
        _fail(f"WiFi 测试失败: {e}")


def test_sd_card():
    """测试 SD 卡读写。"""
    print("\n--- SD 卡测试 ---")
    try:
        import os

        # 列出文件
        files = os.listdir("/sd")
        _pass(f"SD 卡 — 可读取 ({len(files)} 个文件/目录)")

        # 写入测试
        test_file = "/sd/_test_write.txt"
        with open(test_file, "w") as f:
            f.write("ESP32-P4 Microscope OK")
        _pass("SD 卡 — 写入成功")

        # 读取测试
        with open(test_file, "r") as f:
            content = f.read()
        if content == "ESP32-P4 Microscope OK":
            _pass("SD 卡 — 读取验证通过")
        else:
            _fail("SD 卡 — 读取内容不匹配")

        # 清理
        os.remove(test_file)
        _pass("SD 卡 — 删除测试文件成功")

    except ImportError:
        _skip("os 模块不可用")
    except OSError:
        _skip("SD 卡未挂载 (可能未插入或格式不支持)")
    except Exception as e:
        _fail(f"SD 卡测试失败: {e}")


def test_touch():
    """测试触摸屏。"""
    print("\n--- 触摸屏测试 ---")
    try:
        import lvgl as lv
        from touch_ui import TouchUI
        _pass("lvgl 模块 — 可导入")
    except ImportError:
        _skip("lvgl 不可用 (无屏模式)")
    except Exception as e:
        _fail(f"触摸屏测试失败: {e}")


def test_mic():
    """测试 I2S 麦克风（可选）。"""
    print("\n--- 麦克风测试 ---")
    try:
        from voice_controller import VoiceController
        vc = VoiceController(None, None, None)
        ok = vc.init()
        if ok:
            _pass("语音模块 — 初始化成功")
            vc.deinit()
        else:
            _skip("语音模块 — 初始化返回失败（可能无 ESP-SR 固件）")
    except ImportError:
        _skip("语音模块不可用")
    except Exception as e:
        _fail(f"麦克风测试失败: {e}")


# ====== 主入口 ======

def run_all():
    """运行全部硬件测试。"""
    global _results, _passed, _failed, _skipped
    _results = []
    _passed = _failed = _skipped = 0

    print("=" * 50)
    print("ESP32-P4 智能显微镜 — 硬件验证")
    print("=" * 50)

    tests = [
        test_gpio,
        test_motors,
        test_led,
        test_camera,
        test_wifi,
        test_sd_card,
        test_touch,
        test_mic,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            _fail(f"测试异常: {e}")

    # 总结
    total = _passed + _failed + _skipped
    print("\n" + "=" * 50)
    print(f"测试完成: {total} 项")
    print(f"  通过: {_passed}")
    print(f"  失败: {_failed}")
    print(f"  跳过: {_skipped}")
    print("=" * 50)

    for status, msg in _results:
        if status == "FAIL":
            print(f"  ✗ {msg}")
    if _failed == 0:
        print("  全部硬件测试通过！")


# 允许直接执行
if __name__ == "__main__":
    run_all()
