"""
ESP32-P4 端细胞分析桥接模块。

设备端负责:
    1. 拍照采集图像
    2. 将 JPEG 字节传给桌面端 CellCounter 分析
    3. 返回统计结果

桌面端负责:
    1. 接收 JPEG，运行 OpenCV 分析管线
    2. 返回 JSON 计数报告

WiFi 交互模式:
    设备端 POST /api/analyze/cells → 桌面端下载图像并分析
    桌面端 GET  /api/analyze/cells → 获取最近分析结果
"""

import time
import json

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class CellAnalyzer:
    """设备端细胞分析桥接。

    Args:
        camera: CameraController 实例
        results_file: 分析结果缓存路径（SD 卡）
    """

    def __init__(self, camera, results_file="/sd/cell_analysis.json"):
        self._cam = camera
        self._results_file = results_file
        self._last_result = None
        self._analysis_count = 0

    def capture_for_analysis(self, filename=None):
        """拍照并保存到 SD 卡，供桌面端下载分析。

        Returns:
            dict: {"file": 文件路径, "size": 字节数}
            失败返回 {"error": 错误信息}
        """
        if self._cam is None or not getattr(self._cam, '_initialized', False):
            return {"error": "摄像头未初始化"}

        if filename is None:
            t = int(time.time() if hasattr(time, 'time') else 0)
            filename = f"/sd/cell_{t:010d}.jpg"
        elif not filename.startswith("/"):
            filename = "/sd/" + filename

        ok = self._cam.capture_to_file(filename)
        if not ok:
            return {"error": "拍照失败"}

        try:
            import os
            stat = os.stat(filename)
            size = stat[6]
        except Exception:
            size = 0

        self._analysis_count += 1
        return {
            "file": filename,
            "size": size,
            "index": self._analysis_count,
        }

    def save_result(self, result):
        """保存分析结果到本地缓存。"""
        self._last_result = result
        try:
            with open(self._results_file, "w") as f:
                json.dump(result, f)
        except Exception:
            pass

    def get_last_result(self):
        """获取最近一次分析结果。"""
        if self._last_result is not None:
            return self._last_result
        try:
            with open(self._results_file, "r") as f:
                self._last_result = json.load(f)
            return self._last_result
        except Exception:
            return None

    def get_state(self):
        """返回分析器状态。"""
        last = self.get_last_result()
        return {
            "analysis_count": self._analysis_count,
            "last_result": last,
        }

    # ---- 内建简易计数 (不依赖 OpenCV) ----

    def simple_count(self, jpeg_data=None):
        """在设备端对 JPEG 做简易的亮度阈值计数。

        仅适用于高对比度样本（染色细胞/荧光标记）。
        原理: JPEG 字节均值作为阈值，统计暗像素占比。

        Returns:
            dict: 粗略估计的细胞数量及暗区占比
        """
        if jpeg_data is None:
            jpeg_data = self._cam.capture() if self._cam else None

        if jpeg_data is None:
            return {"error": "无图像数据"}

        # 跳过 JPEG 头部 (找 SOI + SOS 标记)
        data = jpeg_data if isinstance(jpeg_data, bytes) else bytes(jpeg_data)

        if len(data) < 50:
            return {"error": "图像数据过小"}

        sos_idx = self._find_sos(data)
        if sos_idx < 0:
            sos_idx = len(data) // 4  # 粗略跳过头部

        # 统计暗像素比例
        pixels = data[sos_idx:]
        if len(pixels) < 10:
            return {"error": "无法解析 JPEG 像素数据"}

        mean = sum(pixels) / len(pixels)
        dark_count = sum(1 for b in pixels if b < mean * 0.6)
        dark_ratio = dark_count / len(pixels) if len(pixels) > 0 else 0

        # 粗略估计: 假设每个暗区平均 200 字节
        est_cells = int(dark_count / 200)

        result = {
            "estimated_count": est_cells,
            "dark_ratio": round(dark_ratio, 3),
            "image_mean": round(mean, 1),
            "method": "simple_threshold",
        }
        self.save_result(result)
        return result

    @staticmethod
    def _find_sos(data):
        """查找 JPEG SOS (Start of Scan) 标记 FF DA。"""
        for i in range(len(data) - 1):
            if data[i] == 0xFF and data[i + 1] == 0xDA:
                return i + 2
        return -1
