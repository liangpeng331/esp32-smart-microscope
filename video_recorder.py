"""
显微镜视频录制模块。

支持两种模式:
    ESP32-P4 端  — 连续拍照保存为 JPEG 序列（设备能力有限）
    桌面端        — 将 JPEG 序列编码为 MP4/H.264 视频

用法:
    # 设备端
    from video_recorder import VideoRecorder
    vr = VideoRecorder(camera, fps=10)
    vr.start()
    time.sleep(30)     # 录制 30 秒
    vr.stop()

    # 桌面端合成
    python3 video_recorder.py --compose /sd/record_001/ --output video.mp4 --fps 10
"""

import time
import os
import sys
import _thread

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class VideoRecorder:
    """设备端视频录制器。

    持续从摄像头采集 JPEG 帧，写入 SD 卡指定目录。
    录制期间不阻塞主线程（使用独立线程）。

    Args:
        camera: CameraController 实例
        fps: 录制帧率 (1-30)
        output_dir: 帧保存目录 (SD 卡)
        max_duration: 最长录制秒数 (0 = 不限)
    """

    MIN_FPS = 1
    MAX_FPS = 30

    def __init__(self, camera, fps=10, output_dir="/sd/video_frames", max_duration=0):
        self._cam = camera
        self._fps = max(self.MIN_FPS, min(self.MAX_FPS, fps))
        self._output_dir = output_dir.rstrip("/")
        self._max_duration = max_duration
        self._running = False
        self._paused = False
        self._frame_count = 0
        self._start_time = 0
        self._error_count = 0
        self._thread = None

    # ====== 生命周期 ======

    def start(self):
        """开始录制（后台线程）。"""
        if self._running:
            return False

        if self._cam is None or not getattr(self._cam, '_initialized', False):
            return False

        # 确保输出目录存在
        try:
            self._ensure_dir(self._output_dir)
        except OSError:
            return False

        self._running = True
        self._paused = False
        self._frame_count = 0
        self._error_count = 0
        self._start_time = time.time() if hasattr(time, 'time') else 0

        # 启动录制线程
        _thread.start_new_thread(self._record_loop, ())

        return True

    def stop(self):
        """停止录制。"""
        self._running = False
        # 等待线程结束
        _sleep_ms(200)

    def _record_loop(self):
        """录制主循环（后台线程）。"""
        interval = 1.0 / self._fps
        elapsed = 0.0

        while self._running:
            loop_start = time.time() if hasattr(time, 'time') else 0

            if not self._paused:
                try:
                    frame = self._cam.capture()
                    if frame:
                        filename = f"{self._output_dir}/frame_{self._frame_count:06d}.jpg"
                        self._save_frame(filename, frame)
                        self._frame_count += 1
                    else:
                        self._error_count += 1
                except Exception:
                    self._error_count += 1

            # 控制帧率
            elapsed_time = (time.time() if hasattr(time, 'time') else 0) - loop_start
            sleep_time = max(0, interval - elapsed_time)
            _sleep_ms(int(sleep_time * 1000))

            # 检查最大时长
            elapsed = (time.time() if hasattr(time, 'time') else 0) - self._start_time
            if self._max_duration > 0 and elapsed >= self._max_duration:
                self._running = False

    def _save_frame(self, filename, data):
        """保存一帧到文件。CPython 模式用普通文件操作。"""
        try:
            with open(filename, "wb") as f:
                f.write(data if isinstance(data, bytes) else bytes(data))
        except OSError:
            pass

    @staticmethod
    def _ensure_dir(path):
        try:
            os.mkdir(path)
        except OSError:
            pass  # 目录可能已存在

    # ====== 控制 ======

    def pause(self):
        """暂停录制。"""
        self._paused = True

    def resume(self):
        """恢复录制。"""
        self._paused = False

    def is_running(self):
        return self._running

    def is_paused(self):
        return self._paused

    def get_frame_count(self):
        return self._frame_count

    def get_error_count(self):
        return self._error_count

    # ====== 状态 ======

    def get_state(self):
        """返回录制器状态。"""
        return {
            "recording": self._running,
            "paused": self._paused,
            "frames": self._frame_count,
            "errors": self._error_count,
            "fps": self._fps,
            "output": self._output_dir,
            "duration_total": self._frame_count / max(1, self._fps),
        }


# ====== 桌面端 MP4 合成 ======

def compose_video(frame_dir: str, output: str, fps=10, codec="mp4v"):
    """将 JPEG 帧序列编码为 MP4 视频。

    Args:
        frame_dir: 帧序列目录
        output: 输出视频文件路径
        fps: 帧率
        codec: FourCC 编码 (mp4v / avc1 / h264)

    依赖: pip install opencv-python
    """
    import cv2

    # 收集排序帧文件
    files = sorted(f for f in os.listdir(frame_dir)
                   if f.endswith(".jpg") and f.startswith("frame_"))

    if not files:
        print(f"无帧文件: {frame_dir}")
        return False

    first = cv2.imread(os.path.join(frame_dir, files[0]))
    if first is None:
        print("无法读取第一帧")
        return False

    h, w = first.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output, fourcc, fps, (w, h))

    total = len(files)
    for i, fname in enumerate(files):
        img = cv2.imread(os.path.join(frame_dir, fname))
        if img is None:
            continue
        writer.write(img)
        if (i + 1) % 50 == 0:
            print(f"  编码: {i+1}/{total}")

    writer.release()
    size_mb = os.path.getsize(output) / (1024 * 1024)
    print(f"视频已生成: {output} ({total} 帧, {size_mb:.1f} MB)")
    return True


def compose_timelapse(frame_dir: str, output: str, speedup=30, fps=30):
    """从帧序列生成延时摄影视频。

    Args:
        speedup: 加速倍率（每隔 N 帧取 1 帧）
        fps: 输出帧率
    """
    import cv2

    files = sorted(f for f in os.listdir(frame_dir)
                   if f.endswith(".jpg") and f.startswith("frame_"))

    if not files:
        print(f"无帧文件: {frame_dir}")
        return False

    # 按加速倍率抽帧
    sampled = files[::speedup]
    if len(sampled) < 2:
        print(f"抽帧后帧数不足 (speedup={speedup})")
        return False

    first = cv2.imread(os.path.join(frame_dir, sampled[0]))
    if first is None:
        return False

    h, w = first.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output, fourcc, fps, (w, h))

    for i, fname in enumerate(sampled):
        img = cv2.imread(os.path.join(frame_dir, fname))
        if img is None:
            continue
        writer.write(img)

    writer.release()
    size_mb = os.path.getsize(output) / (1024 * 1024)
    print(f"延时视频: {output} ({len(sampled)} 帧, {size_mb:.1f} MB)")
    return True


# ====== CLI (仅 CPython) ======

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="显微镜视频录制工具")
    sub = parser.add_subparsers(dest="cmd")

    c = sub.add_parser("compose", help="合成视频")
    c.add_argument("frame_dir")
    c.add_argument("--output", "-o", default="microscope_video.mp4")
    c.add_argument("--fps", type=int, default=10)
    c.add_argument("--codec", default="mp4v")

    t = sub.add_parser("timelapse", help="延时摄影")
    t.add_argument("frame_dir")
    t.add_argument("--output", "-o", default="timelapse.mp4")
    t.add_argument("--speedup", type=int, default=30)
    t.add_argument("--fps", type=int, default=30)

    args = parser.parse_args()

    if args.cmd == "compose":
        compose_video(args.frame_dir, args.output, args.fps, args.codec)
    elif args.cmd == "timelapse":
        compose_timelapse(args.frame_dir, args.output, args.speedup, args.fps)
    else:
        parser.print_help()
