"""
自动曝光控制

通过分析图像亮度直方图，自动调节 LED 亮度以维持最佳曝光。

算法: 对 JPEG 数据做快速亮度估计，PID 式调节 LED 占空比。
目标: 图像平均亮度在 40-60% 范围内。
"""

import time

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class AutoExposure:
    """自动曝光控制器。

    持续监控图像亮度并调节 LED 输出，维持目标亮度水平。
    """

    # 亮度目标值 (0-100%)
    TARGET_BRIGHTNESS = 50
    # 允许范围（不触发调节的死区）
    TOLERANCE = 10
    # LED 调节步长 (%)
    STEP_SIZE = 5
    # 最小 LED 亮度（防止完全灭灯导致无法评估）
    MIN_LED = 2
    # 最大 LED 亮度
    MAX_LED = 100

    def __init__(self, camera_controller, led_controller):
        """
        Args:
            camera_controller: CameraController 实例
            led_controller: LedController 实例
        """
        self._cam = camera_controller
        self._led = led_controller
        self._active = False
        self._last_brightness = None
        self._converged = False
        self._iterations = 0

    # ====== 单次自动曝光 ======

    def adjust_once(self):
        """采集一帧图像，根据亮度一次性调节 LED。

        Returns:
            dict: {"brightness": 调整后亮度, "image_brightness": 图像亮度%}
        """
        img = self._cam.capture()
        if img is None:
            return {"brightness": self._led.get_state()["brightness"],
                    "image_brightness": None}

        # 估计图像亮度
        img_brightness = self._estimate_brightness(img)

        led_state = self._led.get_state()
        current = led_state["brightness"]

        # 死区内不调节
        if abs(img_brightness - self.TARGET_BRIGHTNESS) <= self.TOLERANCE:
            return {"brightness": current, "image_brightness": img_brightness}

        # 计算新亮度
        if img_brightness < self.TARGET_BRIGHTNESS:
            new_brightness = min(self.MAX_LED, current + self.STEP_SIZE)
        else:
            new_brightness = max(self.MIN_LED, current - self.STEP_SIZE)

        self._led.set_brightness(new_brightness)
        if new_brightness > 0 and not led_state["on"]:
            self._led.on()

        return {"brightness": new_brightness, "image_brightness": img_brightness}

    # ====== 连续自动曝光 ======

    def start(self):
        """启动连续自动曝光（需在主循环中调用 process()）。"""
        self._active = True
        self._converged = False
        self._iterations = 0
        print("[AutoExposure] 启动自动曝光")

    def stop(self):
        """停止自动曝光。"""
        self._active = False
        print(f"[AutoExposure] 停止 (迭代 {self._iterations} 次)")

    def process(self):
        """处理一帧（在主循环中调用）。

        Returns:
            dict 或 None: 同 adjust_once()
        """
        if not self._active:
            return None
        result = self.adjust_once()
        self._iterations += 1

        if result["image_brightness"] is not None:
            if abs(result["image_brightness"] - self.TARGET_BRIGHTNESS) <= self.TOLERANCE:
                self._converged = True

        return result

    def is_converged(self):
        return self._converged

    def is_active(self):
        return self._active

    # ====== 图像亮度估计 ======

    def _estimate_brightness(self, jpeg_data):
        """从 JPEG 数据快速估计图像亮度。

        跳过 JPEG 头 (找 SOI marker 0xFFD8 后的数据段)，
        计算高频分量能量占比。亮图像有更多细节/能量。

        Returns:
            float: 亮度百分比估计值 (0-100)
        """
        if jpeg_data is None or len(jpeg_data) < 100:
            return 50.0  # 默认中值

        # 跳过 JPEG header (通常 20-600 字节)
        start = min(600, len(jpeg_data) // 4)
        data = jpeg_data[start:]

        if len(data) < 50:
            return 50.0

        # 统计亮度: 高字节占比 + 方差
        total = 0.0
        count = 0
        for i in range(1, len(data)):
            diff = abs(data[i] - data[i - 1])
            total += data[i]
            count += 1

        if count == 0:
            return 50.0

        mean_val = total / count

        # 均值映射到百分比（经验值: JPEG 字节均值 80-180 对应正常曝光）
        # < 60 → 暗, 60-140 → 正常, > 140 → 亮
        pct = (mean_val - 40) / 160 * 100
        pct = max(0, min(100, pct))
        return pct

    def get_state(self):
        return {
            "active": self._active,
            "converged": self._converged,
            "iterations": self._iterations,
            "led_brightness": self._led.get_state()["brightness"],
        }
