"""
led_controller.py 单元测试 — 使用 Mock PWM 验证调光逻辑。

运行方式:
    python -m unittest tests.test_led_controller -v
"""

import sys
import unittest

# ---- Mock machine.PWM ----

class MockPWM:
    """记录 PWM 占空比和频率，不做实际输出。"""

    def __init__(self, pin, freq=1000, duty=0):
        self.pin = pin
        self.freq = freq
        self._duty = duty

    def duty(self, value=None):
        if value is None:
            return self._duty
        self._duty = value

    def freq(self, value=None):
        if value is None:
            return self._freq
        self._freq = value

    def deinit(self):
        pass


class MockPin:
    OUT = 1

    def __init__(self, number, mode=None):
        self.number = number
        self.mode = mode


# 注入 Mock
sys.modules['machine'] = type(sys)('machine')
sys.modules['machine'].Pin = MockPin
sys.modules['machine'].PWM = MockPWM

from led_controller import LedController


class TestLedController(unittest.TestCase):

    def setUp(self):
        self.led = LedController(pin=21, freq=1000, max_duty=1023)

    # ====== 初始状态 ======

    def test_initial_state_is_off(self):
        state = self.led.get_state()
        self.assertFalse(state["on"])
        self.assertEqual(state["brightness"], 0)

    def test_initial_pwm_duty_is_zero(self):
        self.assertEqual(self.led._pwm.duty(), 0)

    # ====== 开关控制 ======

    def test_on_sets_is_on_true(self):
        self.led.on()
        self.assertTrue(self.led.get_state()["on"])

    def test_off_sets_is_on_false(self):
        self.led.on()
        self.led.off()
        self.assertFalse(self.led.get_state()["on"])

    def test_off_sets_pwm_duty_to_zero(self):
        self.led.set_brightness(80)
        self.led.on()
        self.led.off()
        self.assertEqual(self.led._pwm.duty(), 0)

    def test_toggle_flips_state(self):
        self.led.toggle()
        self.assertTrue(self.led.get_state()["on"])
        self.led.toggle()
        self.assertFalse(self.led.get_state()["on"])

    def test_on_restores_brightness(self):
        """关灯→开灯后亮度恢复到之前的值"""
        self.led.set_brightness(60)
        self.led.on()
        self.led.off()
        self.assertEqual(self.led._pwm.duty(), 0)
        self.led.on()
        expected_duty = int(60 / 100.0 * 1023)
        self.assertEqual(self.led._pwm.duty(), expected_duty)

    # ====== 亮度控制 ======

    def test_set_brightness_0(self):
        self.led.set_brightness(0)
        self.led.on()
        self.assertEqual(self.led._pwm.duty(), 0)

    def test_set_brightness_100(self):
        self.led.set_brightness(100)
        self.led.on()
        self.assertEqual(self.led._pwm.duty(), 1023)

    def test_set_brightness_50(self):
        self.led.set_brightness(50)
        self.led.on()
        self.assertEqual(self.led._pwm.duty(), 511)

    def test_set_brightness_75(self):
        self.led.set_brightness(75)
        self.led.on()
        self.assertEqual(self.led._pwm.duty(), 767)

    def test_brightness_applied_only_when_on(self):
        """关灯时调亮度不改变 PWM 输出"""
        self.led.off()
        self.led.set_brightness(90)
        self.assertEqual(self.led._pwm.duty(), 0)

    def test_brightness_applies_immediately_when_on(self):
        self.led.on()
        self.led.set_brightness(30)
        expected = int(30 / 100.0 * 1023)
        self.assertEqual(self.led._pwm.duty(), expected)

    # ====== 边界值 ======

    def test_brightness_clamped_at_0(self):
        self.led.on()
        self.led.set_brightness(-10)
        self.assertEqual(self.led._brightness, 0)

    def test_brightness_clamped_at_100(self):
        self.led.on()
        self.led.set_brightness(150)
        self.assertEqual(self.led._brightness, 100)

    # ====== 预设档位 ======

    def test_preset_暗(self):
        self.led.on()
        self.led.preset("暗")
        expected = int(20 / 100.0 * 1023)
        self.assertEqual(self.led._pwm.duty(), expected)

    def test_preset_中(self):
        self.led.on()
        self.led.preset("中")
        expected = int(50 / 100.0 * 1023)
        self.assertEqual(self.led._pwm.duty(), expected)

    def test_preset_亮(self):
        self.led.on()
        self.led.preset("亮")
        expected = int(80 / 100.0 * 1023)
        self.assertEqual(self.led._pwm.duty(), expected)

    def test_preset_最亮(self):
        self.led.on()
        self.led.preset("最亮")
        self.assertEqual(self.led._pwm.duty(), 1023)

    def test_preset_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            self.led.preset("不存在的档位")

    def test_get_presets(self):
        presets = self.led.get_presets()
        self.assertIn("暗", presets)
        self.assertIn("中", presets)
        self.assertIn("亮", presets)
        self.assertIn("最亮", presets)

    # ====== get_state ======

    def test_get_state_reflects_changes(self):
        self.led.set_brightness(55)
        self.led.on()
        state = self.led.get_state()
        self.assertTrue(state["on"])
        self.assertEqual(state["brightness"], 55)

    def test_get_state_after_off(self):
        self.led.set_brightness(70)
        self.led.on()
        self.led.off()
        state = self.led.get_state()
        self.assertFalse(state["on"])
        self.assertEqual(state["brightness"], 70)  # 亮度记忆保留


if __name__ == '__main__':
    unittest.main()
