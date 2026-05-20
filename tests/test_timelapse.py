"""定时拍摄模块单元测试。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import timelapse


class FakeStage:
    def __init__(self):
        self._position = {"x": 0, "y": 0, "z": 0}

    def move_to(self, x=None, y=None, z=None):
        if x is not None:
            self._position["x"] = x
        if y is not None:
            self._position["y"] = y
        if z is not None:
            self._position["z"] = z

    def get_position(self):
        return dict(self._position)


class FakeCam:
    def __init__(self):
        self._files = []

    def capture_to_file(self, path):
        self._files.append(path)
        return True


class TestTimelapse(unittest.TestCase):

    def setUp(self):
        self.stage = FakeStage()
        self.cam = FakeCam()
        self.tl = timelapse.Timelapse(self.stage, self.cam)

    def test_initial_state_not_running(self):
        self.assertFalse(self.tl.is_running())

    def test_get_status_initial(self):
        status = self.tl.get_status()
        self.assertFalse(status["running"])
        self.assertIsNone(status["mode"])

    def test_timed_capture_starts(self):
        result = self.tl.timed_capture(0.1, 2, prefix="test")
        self.assertTrue(result)
        self.assertTrue(self.tl.is_running())
        self.tl.stop()

    def test_timed_capture_rejects_when_running(self):
        self.tl.timed_capture(1, 5)
        result = self.tl.timed_capture(1, 5)
        self.assertFalse(result)
        self.tl.stop()

    def test_z_stack_starts(self):
        result = self.tl.z_stack(100, 300, 100)
        self.assertTrue(result)
        self.assertTrue(self.tl.is_running())
        self.tl.stop()

    def test_grid_scan_starts(self):
        result = self.tl.grid_scan(0, 200, 0, 200, 100)
        self.assertTrue(result)
        self.assertTrue(self.tl.is_running())
        self.tl.stop()

    def test_pause_resume(self):
        self.tl.timed_capture(1, 5)
        self.tl.pause()
        self.tl.resume()
        self.tl.stop()

    def test_stop_sets_not_running(self):
        self.tl.timed_capture(1, 5)
        self.tl.stop()
        self.assertFalse(self.tl.is_running())


if __name__ == "__main__":
    unittest.main()
