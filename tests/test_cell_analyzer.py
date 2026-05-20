"""设备端细胞分析桥接模块单元测试。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
import os
import tempfile
import json
from unittest.mock import MagicMock

import cell_analyzer


# ---- 用于 cell_analyzer 的最小 JPEG ----
def _make_minimal_jpeg():
    """生成最小的有效 JPEG 字节 (1x1 灰色像素)。"""
    # 最小 JPEG 数据 (SOI + DQT + SOF + DHT + SOS + EOI)
    data = bytes([
        0xFF, 0xD8,                     # SOI
        0xFF, 0xDB, 0x00, 0x43, 0x00,   # DQT (简化)
        0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07,
        0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14,
        0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12, 0x13,
        0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A,
        0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20, 0x22,
        0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C,
        0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39,
        0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32,
        0xFF, 0xC0, 0x00, 0x0B, 0x08,   # SOF (8-bit)
        0x00, 0x01, 0x00, 0x01, 0x01,
        0x01, 0x11, 0x00,
        0xFF, 0xC4, 0x00, 0x1F, 0x00,   # DHT (霍夫曼表，简化)
        0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
        0x07, 0x08, 0x09, 0x0A, 0x0B,
        0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0x7F, 0xD9,  # SOS + 图像数据
        0xFF, 0xD9,                     # EOI
    ])
    return data


class FakeCamera:
    """模拟 CameraController。"""
    def __init__(self, initialized=True, capture_data=_make_minimal_jpeg(), capture_to_file_ok=True):
        self._initialized = initialized
        self._capture_data = capture_data
        self._capture_to_file_ok = capture_to_file_ok

    def capture(self):
        return self._capture_data

    def capture_to_file(self, filename):
        if self._capture_to_file_ok:
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            with open(filename, "wb") as f:
                f.write(self._capture_data)
            return True
        return False


class TestCellAnalyzer(unittest.TestCase):

    def setUp(self):
        self.tmpfile = os.path.join(tempfile.gettempdir(), "test_cell_analysis.json")
        self.cam = FakeCamera()
        self.ca = cell_analyzer.CellAnalyzer(self.cam, self.tmpfile)

    def tearDown(self):
        try:
            os.remove(self.tmpfile)
        except OSError:
            pass

    # ---- 初始化 ----

    def test_initialization(self):
        self.assertIsNone(self.ca._last_result)
        self.assertEqual(self.ca._analysis_count, 0)

    def test_init_without_camera(self):
        ca = cell_analyzer.CellAnalyzer(None)
        self.assertIsNotNone(ca)

    # ---- capture_for_analysis ----

    def test_capture_returns_file_info(self):
        out = os.path.join(tempfile.gettempdir(), "test_cell.jpg")
        result = self.ca.capture_for_analysis(out)
        self.assertIn("file", result)
        self.assertIn("size", result)
        self.assertEqual(self.ca._analysis_count, 1)

    def test_capture_failure_result(self):
        cam = FakeCamera(capture_to_file_ok=False)
        ca = cell_analyzer.CellAnalyzer(cam)
        out = os.path.join(tempfile.gettempdir(), "test_nonexist.jpg")
        result = ca.capture_for_analysis(out)
        self.assertIn("error", result)

    def test_capture_when_camera_not_initialized(self):
        cam = FakeCamera(initialized=False)
        ca = cell_analyzer.CellAnalyzer(cam)
        result = ca.capture_for_analysis()
        self.assertIn("error", result)

    def test_capture_when_camera_none(self):
        ca = cell_analyzer.CellAnalyzer(None)
        result = ca.capture_for_analysis()
        self.assertIn("error", result)

    def test_capture_failure(self):
        cam = FakeCamera(capture_to_file_ok=False)
        ca = cell_analyzer.CellAnalyzer(cam)
        out = os.path.join(tempfile.gettempdir(), "test_willfail.jpg")
        result = ca.capture_for_analysis(out)
        self.assertIn("error", result)

    def test_capture_increments_count(self):
        for i in range(3):
            out = os.path.join(tempfile.gettempdir(), f"test_cell_{i}.jpg")
            self.ca.capture_for_analysis(out)
        self.assertEqual(self.ca._analysis_count, 3)

    # ---- save_result / get_last_result ----

    def test_save_and_get_result(self):
        data = {"count": 42, "sizes": [10, 20, 30]}
        self.ca.save_result(data)
        self.assertEqual(self.ca.get_last_result(), data)

    def test_get_last_result_from_memory_first(self):
        data = {"count": 5}
        self.ca.save_result(data)
        # 即使文件有新数据，内存中的数据优先
        result = self.ca.get_last_result()
        self.assertEqual(result, data)

    def test_get_last_result_returns_none_when_empty(self):
        result = self.ca.get_last_result()
        self.assertIsNone(result)

    # ---- get_state ----

    def test_get_state_initial(self):
        state = self.ca.get_state()
        self.assertEqual(state["analysis_count"], 0)
        self.assertIsNone(state["last_result"])

    def test_get_state_after_analysis(self):
        self.ca.save_result({"count": 3})
        state = self.ca.get_state()
        self.assertEqual(state["last_result"]["count"], 3)

    # ---- simple_count ----

    def test_simple_count_with_synthetic_data(self):
        data = _make_minimal_jpeg()
        result = self.ca.simple_count(data)
        self.assertIn("estimated_count", result)
        self.assertIn("dark_ratio", result)
        self.assertIn("image_mean", result)
        self.assertEqual(result["method"], "simple_threshold")

    def test_simple_count_without_data_uses_camera(self):
        result = self.ca.simple_count()
        self.assertIn("estimated_count", result)
        self.assertIn("dark_ratio", result)

    def test_simple_count_saves_result(self):
        data = _make_minimal_jpeg()
        self.ca.simple_count(data)
        last = self.ca.get_last_result()
        self.assertIsNotNone(last)
        self.assertIn("estimated_count", last)

    def test_simple_count_with_none_camera(self):
        ca = cell_analyzer.CellAnalyzer(None)
        result = ca.simple_count()
        self.assertIn("error", result)

    def test_simple_count_with_none_data_and_data_is_none(self):
        cam = FakeCamera(capture_data=None)
        ca = cell_analyzer.CellAnalyzer(cam)
        result = ca.simple_count()
        self.assertIn("error", result)

    def test_simple_count_with_none_camera_and_data(self):
        ca = cell_analyzer.CellAnalyzer(None)
        result = ca.simple_count(None)
        self.assertIn("error", result)

    # ---- _find_sos ----

    def test_find_sos_positive(self):
        data = _make_minimal_jpeg()
        idx = self.ca._find_sos(data)
        self.assertGreater(idx, 0)

    def test_find_sos_negative(self):
        data = bytes([0x00] * 100)  # 无 SOS 标记
        idx = self.ca._find_sos(data)
        self.assertEqual(idx, -1)

    # ---- 边界条件 ----

    def test_simple_count_with_tiny_data(self):
        result = self.ca.simple_count(bytes([0xFF, 0xD8, 0xFF, 0xD9]))  # 仅 SOI+EOI
        self.assertIn("error", result)

    def test_results_file_persists(self):
        data = {"count": 99, "test": True}
        self.ca.save_result(data)

        # 新实例从文件读取
        ca2 = cell_analyzer.CellAnalyzer(self.cam, self.tmpfile)
        result = ca2.get_last_result()
        self.assertEqual(result, data)


if __name__ == "__main__":
    unittest.main()
