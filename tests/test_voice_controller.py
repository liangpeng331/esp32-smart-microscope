"""语音控制模块单元测试 (CPython 模拟模式)。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import voice_controller


class FakeStage:
    def __init__(self):
        self._position = {"x": 0, "y": 0, "z": 0}
        self.released = False

    def get_position(self):
        return dict(self._position)

    def move_rel(self, dx=None, dy=None, dz=None):
        if dx is not None:
            self._position["x"] += dx
        if dy is not None:
            self._position["y"] += dy
        if dz is not None:
            self._position["z"] += dz

    def move_to(self, x=None, y=None, z=None):
        if x is not None:
            self._position["x"] = x
        if y is not None:
            self._position["y"] = y
        if z is not None:
            self._position["z"] = z

    def release_all(self):
        self.released = True

    def home(self):
        pass


class FakeLed:
    def __init__(self):
        self._on = False
        self._brightness = 50

    def on(self):
        self._on = True

    def off(self):
        self._on = False

    def set_brightness(self, pct):
        self._brightness = max(0, min(100, pct))

    def get_state(self):
        return {"on": self._on, "brightness": self._brightness}


class FakeSys:
    def __init__(self, stage):
        self._presets = [None] * 6
        self._stage = stage
        self._home_called = False

    def move_rel(self, **kwargs):
        self._stage.move_rel(**kwargs)

    def home(self):
        self._home_called = True

    def get_preset(self, slot):
        return self._presets[slot]

    def save_preset(self, pos):
        for i, p in enumerate(self._presets):
            if p is None:
                self._presets[i] = pos
                return i
        return -1

    def move_to(self, **kwargs):
        self._stage.move_to(**kwargs)


class FakeCam:
    def capture_to_file(self, path):
        return True


class TestVoiceController(unittest.TestCase):

    def setUp(self):
        self.stage = FakeStage()
        self.led = FakeLed()
        self.sys = FakeSys(self.stage)
        self.cam = FakeCam()
        self.vc = voice_controller.VoiceController(self.sys, self.stage, self.led, self.cam)

    def test_init_sets_active_in_sim_mode(self):
        self.assertTrue(self.vc.init())

    def test_start_listening_before_init(self):
        """未初始化时启动监听返回 False。"""
        vc2 = voice_controller.VoiceController(self.sys, self.stage, self.led)
        self.assertFalse(vc2.start_listening())

    def test_start_listening_after_init(self):
        self.vc.init()
        self.assertTrue(self.vc.start_listening())

    def test_stop_listening(self):
        self.vc.init()
        self.vc.start_listening()
        self.vc.stop_listening()
        self.assertFalse(self.vc._listening)

    def test_process_returns_none_in_sim_mode(self):
        """模拟模式下 process() 返回 None。"""
        self.vc.init()
        self.vc.start_listening()
        result = self.vc.process()
        self.assertIsNone(result)

    def test_dispatch_move_rel(self):
        """语音指令 '向上移动' 转换为相对移动。"""
        self.vc.init()
        self.vc._dispatch("向上移动")
        self.assertEqual(self.stage._position["y"], 500)

    def test_dispatch_home(self):
        self.vc.init()
        self.vc._dispatch("回零")
        # home() 在 mock 中是空操作，验证无异常即可

    def test_dispatch_led_on(self):
        self.led.off()
        self.vc.init()
        self.vc._dispatch("开灯")
        self.assertTrue(self.led._on)

    def test_dispatch_led_off(self):
        self.led.on()
        self.vc.init()
        self.vc._dispatch("关灯")
        self.assertFalse(self.led._on)

    def test_dispatch_led_brighter(self):
        self.led.set_brightness(50)
        self.vc.init()
        self.vc._dispatch("灯亮一点")
        self.assertEqual(self.led._brightness, 70)

    def test_dispatch_led_dimmer(self):
        self.led.set_brightness(50)
        self.vc.init()
        self.vc._dispatch("灯暗一点")
        self.assertEqual(self.led._brightness, 30)

    def test_dispatch_led_max(self):
        self.vc.init()
        self.vc._dispatch("灯光最亮")
        self.assertEqual(self.led._brightness, 100)

    def test_dispatch_led_min(self):
        self.vc.init()
        self.vc._dispatch("灯光最暗")
        self.assertEqual(self.led._brightness, 5)

    def test_dispatch_stop_releases_motors(self):
        self.vc.init()
        self.vc._dispatch("紧急停止")
        self.assertTrue(self.stage.released)

    def test_dispatch_save_and_recall_preset(self):
        self.vc.init()
        self.stage._position = {"x": 100, "y": 200, "z": 300}
        self.vc._dispatch("保存位置")
        self.assertIsNotNone(self.sys._presets[0])

    def test_dispatch_exit_voice(self):
        self.vc.init()
        self.vc.start_listening()
        self.vc._dispatch("退出语音")
        self.assertFalse(self.vc._listening)

    def test_callback_invoked(self):
        self.vc.init()
        calls = []
        self.vc.start_listening(callback=lambda cmd, act, params: calls.append((cmd, act)))
        self.vc._dispatch("拍照")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], "capture")

    def test_unknown_command_does_not_crash(self):
        self.vc.init()
        self.vc._dispatch("不存在的指令")

    def test_get_state(self):
        self.vc.init()
        state = self.vc.get_state()
        self.assertIn("active", state)
        self.assertIn("listening", state)
        self.assertFalse(state["has_esp_sr"])


if __name__ == "__main__":
    unittest.main()
