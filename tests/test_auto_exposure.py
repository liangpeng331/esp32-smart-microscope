"""自动曝光模块单元测试。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import auto_exposure


class FakeCam:
    def __init__(self, brightness=0.5):
        self._brightness = brightness

    def capture(self):
        mean_val = self._brightness * 160 + 40
        data = bytes([int(mean_val)] * 1000)
        return data


class FakeLed:
    def __init__(self):
        self._on = True
        self._brightness = 50

    def on(self):
        self._on = True

    def off(self):
        self._on = False

    def set_brightness(self, pct):
        self._brightness = max(0, min(100, pct))

    def get_state(self):
        return {"on": self._on, "brightness": self._brightness}


class TestAutoExposure(unittest.TestCase):

    def setUp(self):
        self.led = FakeLed()
        self.ae = auto_exposure.AutoExposure(FakeCam(), self.led)

    def test_adjust_once_returns_dict(self):
        result = self.ae.adjust_once()
        self.assertIn("brightness", result)
        self.assertIn("image_brightness", result)

    def test_dark_image_increases_brightness(self):
        cam = FakeCam(brightness=0.1)  # 暗
        ae = auto_exposure.AutoExposure(cam, self.led)
        self.led.set_brightness(30)
        result = ae.adjust_once()
        self.assertGreater(result["brightness"], 30)

    def test_bright_image_decreases_brightness(self):
        cam = FakeCam(brightness=0.9)  # 亮
        ae = auto_exposure.AutoExposure(cam, self.led)
        self.led.set_brightness(80)
        result = ae.adjust_once()
        self.assertLess(result["brightness"], 80)

    def test_dead_zone_no_change(self):
        cam = FakeCam(brightness=0.5)  # 正好在目标值
        ae = auto_exposure.AutoExposure(cam, self.led)
        self.led.set_brightness(50)
        result = ae.adjust_once()
        self.assertEqual(result["brightness"], 50)

    def test_start_stop(self):
        self.ae.start()
        self.assertTrue(self.ae.is_active())
        self.ae.stop()
        self.assertFalse(self.ae.is_active())

    def test_process_returns_none_when_inactive(self):
        result = self.ae.process()
        self.assertIsNone(result)

    def test_process_returns_dict_when_active(self):
        self.ae.start()
        result = self.ae.process()
        self.assertIsNotNone(result)
        self.ae.stop()

    def test_convergence(self):
        cam = FakeCam(brightness=0.5)
        ae = auto_exposure.AutoExposure(cam, self.led)
        ae.start()
        ae.process()
        self.assertTrue(ae.is_converged())
        ae.stop()

    def test_brightness_clamped(self):
        self.led.set_brightness(2)
        cam = FakeCam(brightness=0.05)
        ae = auto_exposure.AutoExposure(cam, self.led)
        result = ae.adjust_once()
        self.assertGreaterEqual(result["brightness"], auto_exposure.AutoExposure.MIN_LED)

    def test_get_state(self):
        state = self.ae.get_state()
        self.assertFalse(state["active"])
        self.assertFalse(state["converged"])


if __name__ == "__main__":
    unittest.main()
