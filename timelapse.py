"""
定时拍摄与延时摄影模块

支持：
  - 定时拍摄: 按固定间隔拍照
  - 延时摄影: 间隔拍摄 + 可选 Z 轴堆叠
  - 网格扫描: X/Y 平面自动扫描拍照 (用于大视野拼接)
"""

import time
import _thread

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class Timelapse:
    """定时拍摄 / 延时摄影控制器。"""

    def __init__(self, stage_controller, camera_controller, led_controller=None):
        """
        Args:
            stage_controller: StageController 实例
            camera_controller: CameraController 实例
            led_controller: LedController 实例 (可选，用于自动开关灯)
        """
        self._stage = stage_controller
        self._cam = camera_controller
        self._led = led_controller

        self._running = False
        self._paused = False
        self._task_thread = None
        self._status = {
            "running": False,
            "mode": None,
            "total": 0,
            "done": 0,
            "last_file": "",
        }

    # ====== 定时拍摄 ======

    def timed_capture(self, interval_sec, count, prefix="timelapse", folder="/sd/"):
        """定时拍摄：每 interval_sec 秒拍一张，共 count 张。

        在后台线程运行，通过 get_status() 查询进度。

        Args:
            interval_sec: 拍摄间隔 (秒)
            count: 总张数
            prefix: 文件名前缀
            folder: 保存目录

        Returns:
            bool: 任务是否成功启动
        """
        if self._running:
            return False

        self._running = True
        self._status = {"running": True, "mode": "timed",
                        "total": count, "done": 0, "last_file": ""}

        _thread.start_new_thread(
            self._timed_loop, (interval_sec, count, prefix, folder)
        )
        return True

    def _timed_loop(self, interval_sec, count, prefix, folder):
        """定时拍摄主循环。"""
        for i in range(count):
            if not self._running:
                break
            while self._paused and self._running:
                time.sleep(0.5)

            fn = f"{folder}{prefix}_{i+1:04d}.jpg"
            if self._cam.capture_to_file(fn):
                self._status["done"] = i + 1
                self._status["last_file"] = fn
                print(f"[Timelapse] {i+1}/{count} → {fn}")
            else:
                print(f"[Timelapse] 拍摄失败: {i+1}/{count}")

            if i < count - 1:
                time.sleep(interval_sec)

        self._running = False
        self._status["running"] = False
        print("[Timelapse] 定时拍摄完成")

    # ====== Z 轴堆叠拍摄 ======

    def z_stack(self, z_start, z_end, z_step, prefix="zstack", folder="/sd/"):
        """Z 轴堆叠：在不同 Z 位置各拍一张，用于景深合成。

        Args:
            z_start: 起始 Z 位置 (μm)
            z_end: 终止 Z 位置 (μm)
            z_step: Z 步长 (μm)
            prefix: 文件名前缀
            folder: 保存目录
        """
        if self._running:
            return False

        self._running = True
        self._status = {"running": True, "mode": "z_stack",
                        "total": 0, "done": 0, "last_file": ""}

        _thread.start_new_thread(
            self._zstack_loop, (z_start, z_end, z_step, prefix, folder)
        )
        return True

    def _zstack_loop(self, z_start, z_end, z_step, prefix, folder):
        """Z 轴堆叠主循环。"""
        # 移动到起点
        self._stage.move_to(z=z_start)

        z = z_start
        direction = 1 if z_end > z_start else -1
        i = 0
        total = abs(int((z_end - z_start) / z_step)) + 1
        self._status["total"] = total

        while self._running:
            if (direction > 0 and z > z_end) or (direction < 0 and z < z_end):
                break

            self._stage.move_to(z=z)
            _sleep_ms(200)  # 等待电机稳定

            fn = f"{folder}{prefix}_{i+1:04d}.jpg"
            if self._cam.capture_to_file(fn):
                self._status["done"] = i + 1
                self._status["last_file"] = fn
                print(f"[ZStack] Z={z:.0f}μm → {fn}")
            else:
                print(f"[ZStack] 拍摄失败 Z={z:.0f}μm")

            z += direction * z_step
            i += 1

        self._running = False
        self._status["running"] = False
        print("[ZStack] 堆叠拍摄完成")

    # ====== XY 网格扫描 ======

    def grid_scan(self, x_start, x_end, y_start, y_end,
                  step_um, prefix="grid", folder="/sd/"):
        """XY 网格扫描：逐行扫描拍照，用于大视野显微拼接。

        扫描路径：蛇形 (第一行左→右，第二行右→左...)

        Args:
            x_start, x_end: X 轴扫描范围 (μm)
            y_start, y_end: Y 轴扫描范围 (μm)
            step_um: 网格间距 (μm)，通常取视野大小的 80%
            prefix: 文件名前缀
            folder: 保存目录
        """
        if self._running:
            return False

        self._running = True
        x_cols = int(abs(x_end - x_start) / step_um) + 1
        y_rows = int(abs(y_end - y_start) / step_um) + 1
        total = x_cols * y_rows
        self._status = {"running": True, "mode": "grid",
                        "total": total, "done": 0, "last_file": ""}

        _thread.start_new_thread(
            self._grid_loop,
            (x_start, x_end, y_start, y_end, step_um, prefix, folder)
        )
        return True

    def _grid_loop(self, x_start, x_end, y_start, y_end, step, prefix, folder):
        """网格扫描主循环（蛇形路径）。"""
        y = y_start
        row = 0
        y_rows = int(abs(y_end - y_start) / step) + 1
        done = 0

        while self._running and row < y_rows:
            # 蛇形：偶数行左→右，奇数行右→左
            if row % 2 == 0:
                x_range = range(int(x_start), int(x_end) + 1, int(step))
            else:
                x_range = range(int(x_end), int(x_start) - 1, -int(step))

            for x in x_range:
                if not self._running:
                    break
                self._stage.move_to(x=x, y=y)
                _sleep_ms(200)

                fn = f"{folder}{prefix}_r{row:02d}_c{abs(int((x - x_start) / step)):02d}.jpg"
                if self._cam.capture_to_file(fn):
                    done += 1
                    self._status["done"] = done
                    self._status["last_file"] = fn
                else:
                    print(f"[Grid] 拍摄失败 X={x} Y={y}")

            y += step
            row += 1

        self._running = False
        self._status["running"] = False
        print(f"[Grid] 扫描完成: {done} 张")

    # ====== 控制 ======

    def stop(self):
        """停止当前任务。"""
        self._running = False
        self._paused = False

    def pause(self):
        """暂停当前任务。"""
        self._paused = True

    def resume(self):
        """恢复暂停的任务。"""
        self._paused = False

    def get_status(self):
        """返回当前任务状态。"""
        return dict(self._status)

    def is_running(self):
        return self._running
