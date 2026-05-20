"""
摄像头采集模块

支持 OV2640 / OV5640 传感器，DVP 和 MIPI CSI 接口。
提供静态捕获、实时取景、基本参数控制。

在 CPython 环境自动降级为模拟模式，不影响测试。
"""

import time

try:
    import camera
    _HAS_CAMERA = True
except ImportError:
    try:
        from machine import Pin
        _HAS_CAMERA = False  # 有 machine 但无 camera 模块（ESP32-P4 可能用 esp.camera）
    except ImportError:
        _HAS_CAMERA = False


class CameraController:
    """摄像头控制器，封装硬件初始化和图像采集。"""

    # 支持的分辨率
    RESOLUTIONS = {
        "QVGA":   (320, 240),
        "VGA":    (640, 480),
        "SVGA":   (800, 600),
        "XGA":    (1024, 768),
        "HD":     (1280, 720),
        "UXGA":   (1600, 1200),
        "QXGA":   (2048, 1536),
        "QSXGA":  (2592, 1944),
    }

    def __init__(self, width=800, height=600, fmt="JPEG", fps=15):
        """
        Args:
            width: 图像宽度
            height: 图像高度
            fmt: 像素格式 ("JPEG" | "RGB565" | "GRAYSCALE")
            fps: 帧率
        """
        self._width = width
        self._height = height
        self._fmt = fmt
        self._fps = fps
        self._initialized = False
        self._previewing = False
        self._brightness = 0    # -2 ~ 2
        self._contrast = 0      # -2 ~ 2
        self._saturation = 0    # -2 ~ 2
        self._flip_h = False
        self._flip_v = False

    # ====== 生命周期 ======

    def init(self, **kwargs):
        """初始化摄像头硬件。

        在 MicroPython 上调用 camera.init()，
        CPython 环境跳过。
        """
        if _HAS_CAMERA:
            cfg = {
                "xclk_pin": kwargs.pop("xclk_pin", 43),
                "siod_pin": kwargs.pop("siod_pin", 44),
                "sioc_pin": kwargs.pop("sioc_pin", 45),
                "d7_pin": kwargs.pop("d7_pin", 39),
                "d6_pin": kwargs.pop("d6_pin", 40),
                "d5_pin": kwargs.pop("d5_pin", 41),
                "d4_pin": kwargs.pop("d4_pin", 42),
                "d3_pin": kwargs.pop("d3_pin", 11),
                "d2_pin": kwargs.pop("d2_pin", 12),
                "d1_pin": kwargs.pop("d1_pin", 13),
                "d0_pin": kwargs.pop("d0_pin", 14),
                "vsync_pin": kwargs.pop("vsync_pin", 47),
                "href_pin": kwargs.pop("href_pin", 38),
                "pclk_pin": kwargs.pop("pclk_pin", 8),
                "pwdn_pin": kwargs.pop("pwdn_pin", -1),
                "pixel_format": getattr(camera, self._fmt, camera.JPEG),
                "frame_size": getattr(camera, f"FRAME_{self._fmt}", camera.FRAME_VGA),
                "fb_count": 2,
                "jpeg_quality": 12,
            }
            cfg.update(kwargs)

            try:
                camera.init(**cfg)
            except Exception as e:
                print(f"[Camera] 硬件初始化失败: {e}")
                return False

        self._initialized = True
        print(f"[Camera] 初始化完成 {self._width}x{self._height} {self._fmt} @{self._fps}fps")
        return True

    def deinit(self):
        """释放摄像头资源。"""
        self.stop_preview()
        if _HAS_CAMERA:
            try:
                camera.deinit()
            except Exception:
                pass
        self._initialized = False

    # ====== 图像捕获 ======

    def capture(self):
        """捕获单帧图像。

        Returns:
            bytes: JPEG 数据，或 None
        """
        if not self._initialized:
            return None
        if _HAS_CAMERA:
            try:
                return camera.capture()
            except Exception as e:
                print(f"[Camera] 捕获失败: {e}")
                return None
        return None

    def capture_to_file(self, path):
        """捕获并保存到文件。

        Args:
            path: 保存路径 (如 "/sd/photo.jpg")

        Returns:
            bool: 成功 True
        """
        data = self.capture()
        if data is None:
            return False
        try:
            with open(path, "wb") as f:
                f.write(data)
            return True
        except OSError as e:
            print(f"[Camera] 写入文件失败: {e}")
            return False

    # ====== 实时取景 ======

    def start_preview(self, display_callback=None):
        """启动实时取景。

        Args:
            display_callback: 可选的回调函数，每帧调用并传入 JPEG 数据
        """
        if not self._initialized:
            return False

        self._previewing = True
        self._preview_cb = display_callback
        print(f"[Camera] 实时取景已启动")
        return True

    def stop_preview(self):
        """停止实时取景。"""
        self._previewing = False
        self._preview_cb = None

    def preview_frame(self):
        """取景循环中获取一帧，调用回调。

        Returns:
            bytes 或 None
        """
        if not self._previewing:
            return None
        data = self.capture()
        if self._preview_cb:
            self._preview_cb(data)
        return data

    # ====== 参数设置 ======

    def set_resolution(self, width, height):
        """设置分辨率。"""
        self._width = width
        self._height = height
        if _HAS_CAMERA and self._initialized:
            try:
                camera.framesize(self._find_framesize(width, height))
            except Exception:
                pass

    def set_brightness(self, level):
        """亮度 -2~2。"""
        self._brightness = max(-2, min(2, level))
        self._apply_cam_setting("brightness", self._brightness)

    def set_contrast(self, level):
        """对比度 -2~2。"""
        self._contrast = max(-2, min(2, level))
        self._apply_cam_setting("contrast", self._contrast)

    def set_saturation(self, level):
        """饱和度 -2~2。"""
        self._saturation = max(-2, min(2, level))
        self._apply_cam_setting("saturation", self._saturation)

    def flip_horizontal(self, flip=True):
        """水平翻转。"""
        self._flip_h = flip
        if _HAS_CAMERA:
            try:
                camera.flip(1 if flip else 0)
            except Exception:
                pass

    def flip_vertical(self, flip=True):
        """垂直翻转。"""
        self._flip_v = flip
        if _HAS_CAMERA:
            try:
                camera.mirror(1 if flip else 0)
            except Exception:
                pass

    def get_state(self):
        """返回当前状态字典。"""
        return {
            "initialized": self._initialized,
            "previewing": self._previewing,
            "resolution": f"{self._width}x{self._height}",
            "format": self._fmt,
            "fps": self._fps,
            "brightness": self._brightness,
            "contrast": self._contrast,
            "saturation": self._saturation,
            "flip_h": self._flip_h,
            "flip_v": self._flip_v,
        }

    # ====== 内部 ======

    def _find_framesize(self, w, h):
        """根据分辨率找最接近的 frame_size 常量。"""
        pixel_count = w * h
        best = 10  # 默认 FRAME_VGA
        best_diff = float('inf')
        sizes = [
            (0, 96, 96), (1, 160, 120), (2, 176, 144),
            (3, 240, 176), (4, 240, 240), (5, 320, 240),
            (6, 400, 296), (7, 480, 320), (8, 640, 480),
            (9, 800, 600), (10, 1024, 768), (11, 1280, 720),
            (12, 1600, 1200), (13, 2048, 1536), (14, 2592, 1944),
        ]
        for idx, sw, sh in sizes:
            diff = abs(sw * sh - pixel_count)
            if diff < best_diff:
                best_diff = diff
                best = idx
        return best

    def _apply_cam_setting(self, name, value):
        """应用摄像头参数。"""
        if _HAS_CAMERA and self._initialized:
            try:
                getattr(camera, name)(value)
            except Exception:
                pass
