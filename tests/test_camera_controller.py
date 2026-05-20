"""摄像头控制器单元测试 (CPython 模拟模式)。"""
import unittest
import sys
import os

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import camera_controller


class TestCameraController(unittest.TestCase):

    def setUp(self):
        self.cam = camera_controller.CameraController(width=800, height=600)

    def test_init_state_not_initialized(self):
        """初始化前 _initialized 应为 False。"""
        self.assertFalse(self.cam._initialized)

    def test_capture_returns_none_before_init(self):
        """未初始化时捕获返回 None。"""
        result = self.cam.capture()
        self.assertIsNone(result)

    def test_capture_to_file_returns_false_before_init(self):
        """未初始化时保存文件返回 False。"""
        result = self.cam.capture_to_file("/sd/test.jpg")
        self.assertFalse(result)

    def test_init_sets_initialized_cpython_mode(self):
        """CPython 模式下 init() 也会标记为已初始化。"""
        result = self.cam.init()
        self.assertTrue(result)
        self.assertTrue(self.cam._initialized)

    def test_deinit_sets_not_initialized(self):
        """deinit 后标记为未初始化。"""
        self.cam.init()
        self.cam.deinit()
        self.assertFalse(self.cam._initialized)

    def test_start_preview_before_init_returns_false(self):
        """未初始化时启动预览返回 False。"""
        result = self.cam.start_preview()
        self.assertFalse(result)

    def test_start_preview_after_init(self):
        """初始化后可启动预览。"""
        self.cam.init()
        result = self.cam.start_preview()
        self.assertTrue(result)
        self.assertTrue(self.cam._previewing)

    def test_stop_preview(self):
        """停止预览关闭预览标志。"""
        self.cam.init()
        self.cam.start_preview()
        self.cam.stop_preview()
        self.assertFalse(self.cam._previewing)

    def test_preview_frame_returns_none_when_stopped(self):
        """预览停止时取景返回 None。"""
        self.cam.init()
        self.cam.start_preview()
        self.cam.stop_preview()
        self.assertIsNone(self.cam.preview_frame())

    def test_set_brightness_in_range(self):
        self.cam.set_brightness(1)
        self.assertEqual(self.cam._brightness, 1)

    def test_set_brightness_clamped_upper(self):
        self.cam.set_brightness(5)
        self.assertEqual(self.cam._brightness, 2)

    def test_set_brightness_clamped_lower(self):
        self.cam.set_brightness(-5)
        self.assertEqual(self.cam._brightness, -2)

    def test_set_contrast_clamped(self):
        self.cam.set_contrast(3)
        self.assertEqual(self.cam._contrast, 2)
        self.cam.set_contrast(-4)
        self.assertEqual(self.cam._contrast, -2)

    def test_set_saturation_clamped(self):
        self.cam.set_saturation(10)
        self.assertEqual(self.cam._saturation, 2)
        self.cam.set_saturation(-10)
        self.assertEqual(self.cam._saturation, -2)

    def test_flip_horizontal(self):
        self.assertFalse(self.cam._flip_h)
        self.cam.flip_horizontal(True)
        self.assertTrue(self.cam._flip_h)
        self.cam.flip_horizontal(False)
        self.assertFalse(self.cam._flip_h)

    def test_flip_vertical(self):
        self.assertFalse(self.cam._flip_v)
        self.cam.flip_vertical(True)
        self.assertTrue(self.cam._flip_v)

    def test_get_state(self):
        self.cam.init()
        state = self.cam.get_state()
        self.assertTrue(state["initialized"])
        self.assertEqual(state["resolution"], "800x600")

    def test_set_resolution_updates_state(self):
        self.cam.set_resolution(640, 480)
        state = self.cam.get_state()
        self.assertEqual(state["resolution"], "640x480")

    def test_preview_callback_is_called(self):
        """预览回调在 CPython 模式下被调用（capture 返回 None）。"""
        self.cam.init()
        called = []

        def cb(data):
            called.append(data)

        self.cam.start_preview(cb)
        result = self.cam.preview_frame()
        self.assertEqual(len(called), 1)
        self.assertIsNone(called[0])


if __name__ == "__main__":
    unittest.main()
