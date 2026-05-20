"""
自动对焦模块

基于图像清晰度评价 (Laplacian 方差法) 的自动对焦。
Z 轴移动扫描，取最大清晰度位置为合焦点。

清晰度算法参考：
  - Laplacian 方差: Var(Laplacian(I))，数值越大越清晰
  - 对 RGB565/JPEG 帧计算近似梯度
"""

import time

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class Autofocus:
    """自动对焦控制器。

    扫描 Z 轴，在每个位置计算图像清晰度，
    取清晰度最大值为合焦点。
    """

    def __init__(self, stage_controller, camera_controller, z_range=(-500, 500), step=50):
        """
        Args:
            stage_controller: StageController 实例
            camera_controller: CameraController 实例
            z_range: Z 轴扫描范围 (μm)，(下界, 上界)
            step: 扫描步长 (μm)
        """
        self._stage = stage_controller
        self._cam = camera_controller
        self._z_range = z_range
        self._step = step

    # ====== 自动对焦 ======

    def focus(self, callback=None):
        """执行自动对焦：Z 轴扫描 → 找最佳清晰度 → 移动到合焦点。

        Args:
            callback: 每步回调 callback(z_pos, sharpness)

        Returns:
            dict: {"position": z_μm, "sharpness": max_score}
        """
        best_z = self._stage.get_position()["z"]
        best_score = -1
        z_min, z_max = self._z_range
        current_z = best_z

        # 快速回退到扫描起点
        self._stage.move_rel(dz=z_min)

        # 逐步扫描 Z 轴
        steps = int(abs(z_max - z_min) / self._step)
        for i in range(steps + 1):
            target_z = z_min + i * self._step
            self._stage.move_to(z=target_z)

            # 短暂等待相机稳定
            _sleep_ms(100)

            # 采集图像并计算清晰度
            img = self._cam.capture()
            score = self._evaluate_sharpness(img)

            if callback:
                callback(target_z, score)

            if score > best_score:
                best_score = score
                best_z = target_z

        # 移动到最佳位置
        self._stage.move_to(z=best_z)
        print(f"[Autofocus] 最佳焦点: Z={best_z:.0f}μm 清晰度={best_score:.1f}")

        return {"position": best_z, "sharpness": best_score}

    def focus_around(self, center_z, spread=200, step=25):
        """在当前 Z 位置附近精细对焦。

        Args:
            center_z: 当前 Z 位置
            spread: 扫描范围 (μm)，±spread
            step: 步长 (μm)
        """
        saved_range = self._z_range
        saved_step = self._step
        self._z_range = (center_z - spread, center_z + spread)
        self._step = step
        result = self.focus()
        self._z_range = saved_range
        self._step = saved_step
        return result

    # ====== 清晰度评价 ======

    def _evaluate_sharpness(self, img_data):
        """计算图像清晰度分数。

        对 JPEG 数据做近似梯度计算，数值越大越清晰。
        JPEG 本身不含像素级梯度信息，使用 DCT 系数能量
        或频域分析近似；也可用 RGB 数据做 Sobel。

        Args:
            img_data: JPEG bytes 或 RGB565 bytes

        Returns:
            float: 清晰度分数
        """
        if img_data is None:
            return 0.0

        if len(img_data) < 100:
            return 0.0

        # JPEG 近似：高频分量越多 = 越清晰
        # 使用相邻字节差分的方差作为近似
        total = 0.0
        count = 0
        for i in range(1, len(img_data)):
            diff = abs(img_data[i] - img_data[i - 1])
            total += diff * diff
            count += 1

        if count == 0:
            return 0.0
        return total / count

    def _evaluate_sharpness_rgb565(self, rgb_data, width, height):
        """对 RGB565 数据计算 Laplacian 方差。

        精确但成本高，需逐像素卷积。
        """
        if rgb_data is None:
            return 0.0

        data = bytearray(rgb_data)
        total = 0.0
        count = 0

        # 简化的 3×3 Laplacian 核: [0 -1 0; -1 4 -1; 0 -1 0]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = (y * width + x) * 2  # RGB565 每像素 2 字节
                # 将 RGB565 转为灰度近似
                c = (data[idx] << 8 | data[idx + 1]) & 0xFFFF
                g = ((c >> 11) * 77 + ((c >> 5) & 0x3F) * 150 + (c & 0x1F) * 29) // 256

                top = ((data[((y - 1) * width + x) * 2] << 8 | data[((y - 1) * width + x) * 2 + 1]) & 0xFFFF)
                bot = ((data[((y + 1) * width + x) * 2] << 8 | data[((y + 1) * width + x) * 2 + 1]) & 0xFFFF)
                left = ((data[(y * width + (x - 1)) * 2] << 8 | data[(y * width + (x - 1)) * 2 + 1]) & 0xFFFF)
                right = ((data[(y * width + (x + 1)) * 2] << 8 | data[(y * width + (x + 1)) * 2 + 1]) & 0xFFFF)

                tg = ((top >> 11) * 77 + ((top >> 5) & 0x3F) * 150 + (top & 0x1F) * 29) // 256
                bg = ((bot >> 11) * 77 + ((bot >> 5) & 0x3F) * 150 + (bot & 0x1F) * 29) // 256
                lg = ((left >> 11) * 77 + ((left >> 5) & 0x3F) * 150 + (left & 0x1F) * 29) // 256
                rg = ((right >> 11) * 77 + ((right >> 5) & 0x3F) * 150 + (right & 0x1F) * 29) // 256

                lap = (4 * g - tg - bg - lg - rg)
                total += lap * lap
                count += 1

        if count == 0:
            return 0.0
        return total / count

    # ====== 状态 ======

    def get_state(self):
        return {
            "z_range": self._z_range,
            "step": self._step,
        }
