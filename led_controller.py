"""
LED 照明 PWM 调光控制器

通过 MOSFET 驱动高亮 LED，支持 0-100% 无级调光和预设档位。
PWM 频率 1kHz，10 位分辨率（0-1023）。
"""

from machine import Pin, PWM


class LedController:
    """LED 照明控制。"""

    def __init__(self, pin, freq=1000, max_duty=1023):
        """
        Args:
            pin: GPIO 引脚编号
            freq: PWM 频率 (Hz)
            max_duty: 最大占空比值
        """
        self._pin = Pin(pin, Pin.OUT)
        self._pwm = PWM(self._pin, freq=freq, duty=0)
        self._max_duty = max_duty
        self._brightness = 0    # 0-100
        self._is_on = False
        self._presets = {
            "暗": 20,
            "中": 50,
            "亮": 80,
            "最亮": 100,
        }

    def on(self):
        """开灯（恢复到上次亮度）。"""
        self._is_on = True
        self._apply_brightness()

    def off(self):
        """关灯。"""
        self._is_on = False
        self._pwm.duty(0)

    def toggle(self):
        """切换开关状态。"""
        if self._is_on:
            self.off()
        else:
            self.on()

    def set_brightness(self, percent):
        """设置亮度百分比 0-100。"""
        percent = max(0, min(100, percent))
        self._brightness = percent
        if self._is_on:
            self._apply_brightness()

    def preset(self, name):
        """应用预设亮度档位。

        Args:
            name: "暗" | "中" | "亮" | "最亮"
        """
        if name not in self._presets:
            raise ValueError(f"未知预设: {name}，可选: {list(self._presets.keys())}")
        self.set_brightness(self._presets[name])

    def get_state(self):
        """返回当前状态字典。"""
        return {
            "on": self._is_on,
            "brightness": self._brightness,
        }

    def get_presets(self):
        """返回所有预设档位名称。"""
        return list(self._presets.keys())

    def _apply_brightness(self):
        """将百分比亮度映射为 PWM 占空比并输出。"""
        duty = int(self._brightness / 100.0 * self._max_duty)
        self._pwm.duty(duty)
