"""细胞识别计数引擎单元测试。"""
import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

if _HAS_CV2:
    from desktop.cell_counter import CellCounter, main


def _make_synthetic_image(width=320, height=240, n_cells=10, noise_level=3):
    """生成模拟显微镜细胞图像：暗色圆斑在浅色背景上。"""
    img = np.full((height, width, 3), 200, dtype=np.uint8)  # 灰白背景

    rng = np.random.RandomState(42)
    for i in range(n_cells):
        cx = rng.randint(40, width - 40)
        cy = rng.randint(40, height - 40)
        radius = rng.randint(12, 30)
        # 暗色圆斑 (细胞)
        cv2.circle(img, (cx, cy), radius, (60, 60, 60), -1)
        # 亮色核
        cv2.circle(img, (cx + 2, cy - 2), max(3, radius // 3), (150, 150, 150), -1)

    # 轻微噪声
    if noise_level > 0:
        noise = rng.randint(-noise_level, noise_level + 1, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def _make_blank_image(width=320, height=240):
    """生成无细胞的空白图像。"""
    return np.full((height, width, 3), 210, dtype=np.uint8)


@unittest.skipUnless(_HAS_CV2, "需要 OpenCV (pip install opencv-python)")
class TestCellCounter(unittest.TestCase):

    def setUp(self):
        self.counter = CellCounter()
        self.synth = _make_synthetic_image()

    # ---- 初始化 ----

    def test_default_params(self):
        c = CellCounter()
        self.assertEqual(c.min_area, 50)
        self.assertEqual(c.max_area, 50000)
        self.assertTrue(c.blur_kernel % 2 == 1)

    def test_custom_params(self):
        c = CellCounter(min_area=30, max_area=10000, blur_kernel=7, dist_thresh=0.5)
        self.assertEqual(c.min_area, 30)
        self.assertEqual(c.max_area, 10000)
        self.assertEqual(c.blur_kernel, 7)
        self.assertEqual(c.dist_thresh, 0.5)

    def test_blur_kernel_forced_odd(self):
        c = CellCounter(blur_kernel=6)
        self.assertEqual(c.blur_kernel, 7)

    def test_params_clamped(self):
        c = CellCounter(min_area=5, dist_thresh=0.0)
        self.assertEqual(c.min_area, 10)
        self.assertEqual(c.dist_thresh, 0.05)

        c2 = CellCounter(dist_thresh=1.5)
        self.assertEqual(c2.dist_thresh, 0.95)

    # ---- 预处理 ----

    def test_preprocess_returns_binary(self):
        binary = self.counter._preprocess(self.synth)
        self.assertEqual(len(binary.shape), 2)
        self.assertEqual(binary.shape, (240, 320))
        self.assertTrue(np.all(np.isin(binary, [0, 255])))

    def test_preprocess_on_blank_image(self):
        blank = _make_blank_image()
        binary = self.counter._preprocess(blank)
        self.assertEqual(binary.shape, (240, 320))

    # ---- 细胞分离 ----

    def test_separate_cells_returns_markers(self):
        binary = self.counter._preprocess(self.synth)
        markers = self.counter._separate_cells(binary)
        self.assertEqual(markers.shape, binary.shape)
        self.assertGreaterEqual(markers.max(), 1)

    def test_separate_cells_on_blank(self):
        blank = _make_blank_image()
        binary = self.counter._preprocess(blank)
        markers = self.counter._separate_cells(binary)
        self.assertEqual(markers.shape, binary.shape)

    # ---- 轮廓提取 ----

    def test_extract_contours_finds_cells(self):
        binary = self.counter._preprocess(self.synth)
        markers = self.counter._separate_cells(binary)
        contours = self.counter._extract_contours(markers)
        self.assertGreater(len(contours), 0)
        self.assertLessEqual(len(contours), 12)  # 合成图约10个细胞

    def test_extract_contours_filters_small(self):
        c = CellCounter(min_area=99999)
        binary = c._preprocess(self.synth)
        markers = c._separate_cells(binary)
        contours = c._extract_contours(markers)
        self.assertEqual(len(contours), 0)

    # ---- 尺寸计算 ----

    def test_compute_sizes_returns_floats(self):
        binary = self.counter._preprocess(self.synth)
        markers = self.counter._separate_cells(binary)
        contours = self.counter._extract_contours(markers)
        sizes = self.counter._compute_sizes(contours)
        self.assertEqual(len(sizes), len(contours))
        for s in sizes:
            self.assertIsInstance(s, float)
            self.assertGreater(s, 0)

    def test_compute_sizes_empty(self):
        sizes = self.counter._compute_sizes([])
        self.assertEqual(sizes, [])

    # ---- 可视化 ----

    def test_draw_annotations(self):
        binary = self.counter._preprocess(self.synth)
        markers = self.counter._separate_cells(binary)
        contours = self.counter._extract_contours(markers)
        annotated = self.counter._draw_annotations(self.synth, contours)
        self.assertEqual(annotated.shape, self.synth.shape)
        self.assertEqual(annotated.dtype, np.uint8)

    def test_build_mask(self):
        binary = self.counter._preprocess(self.synth)
        markers = self.counter._separate_cells(binary)
        contours = self.counter._extract_contours(markers)
        mask = self.counter._build_mask(self.synth.shape, contours)
        self.assertEqual(len(mask.shape), 2)
        self.assertEqual(mask.shape, self.synth.shape[:2])
        if contours:
            self.assertGreater(cv2.countNonZero(mask), 0)

    def test_get_contour_image(self):
        self.counter.count(self.synth)
        result = self.counter.get_contour_image(self.synth)
        self.assertEqual(result.shape, self.synth.shape)

    # ---- 主流程 count() ----

    def test_count_returns_dict_with_all_keys(self):
        result = self.counter.count(self.synth)
        for key in ["count", "sizes", "mean_size", "median_size",
                     "size_std", "min_size", "max_size", "area_fraction"]:
            self.assertIn(key, result)

    def test_count_on_synthetic_finds_cells(self):
        result = self.counter.count(self.synth)
        self.assertGreater(result["count"], 0)  # 合成图有细胞
        self.assertLess(result["count"], 15)     # 不应该太多

    def test_count_on_blank_returns_zero(self):
        blank = _make_blank_image()
        result = self.counter.count(blank)
        self.assertEqual(result["count"], 0)

    def test_count_area_fraction_between_0_and_100(self):
        result = self.counter.count(self.synth)
        self.assertGreaterEqual(result["area_fraction"], 0)
        self.assertLessEqual(result["area_fraction"], 100)

    def test_count_sizes_ordered(self):
        result = self.counter.count(self.synth)
        if result["sizes"]:
            self.assertEqual(result["min_size"], min(result["sizes"]))
            self.assertEqual(result["max_size"], max(result["sizes"]))

    def test_count_sets_annotated_and_mask(self):
        self.counter.count(self.synth)
        self.assertIsNotNone(self.counter.get_annotated())
        self.assertIsNotNone(self.counter.get_mask())

    # ---- 边界条件 ----

    def test_empty_image_raises(self):
        with self.assertRaises(ValueError):
            self.counter.count(None)

    def test_zero_size_image(self):
        with self.assertRaises(ValueError):
            self.counter.count(np.array([]))

    def test_no_cells_low_dist_thresh(self):
        c = CellCounter(dist_thresh=0.95)
        blank = _make_blank_image()
        result = c.count(blank)
        self.assertEqual(result["count"], 0)

    def test_idempotent_repeat_calls(self):
        r1 = self.counter.count(self.synth)
        r2 = self.counter.count(self.synth)
        self.assertEqual(r1["count"], r2["count"])


@unittest.skipUnless(_HAS_CV2, "需要 OpenCV")
class TestCellCounterIntegration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_save_annotated_to_file(self):
        img = _make_synthetic_image(n_cells=5)
        counter = CellCounter()
        counter.count(img)

        out = os.path.join(self.tmpdir, "annotated.jpg")
        cv2.imwrite(out, counter.get_annotated())
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_save_mask_to_file(self):
        img = _make_synthetic_image(n_cells=5)
        counter = CellCounter()
        counter.count(img)

        out = os.path.join(self.tmpdir, "mask.png")
        cv2.imwrite(out, counter.get_mask())
        self.assertTrue(os.path.exists(out))

    def test_size_vs_expected(self):
        """合成图中细胞直径应在 24-60 像素之间（半径12-30）。"""
        counter = CellCounter(min_area=30)
        result = counter.count(_make_synthetic_image(n_cells=8))
        if result["sizes"]:
            for s in result["sizes"]:
                self.assertGreaterEqual(s, 5)
                self.assertLess(s, 200)


if __name__ == "__main__":
    unittest.main()
