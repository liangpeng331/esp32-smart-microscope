"""自动对焦模块单元测试。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import autofocus


class FakeStage:
    def __init__(self):
        self._position = {"x": 0, "y": 0, "z": 5000}
        self._move_log = []

    def get_position(self):
        return dict(self._position)

    def move_to(self, x=None, y=None, z=None):
        if z is not None:
            self._position["z"] = z
            self._move_log.append(("to", z))

    def move_rel(self, dz=None):
        if dz is not None:
            self._position["z"] += dz
            self._move_log.append(("rel", dz))


class FakeCam:
    def __init__(self):
        self._captures = 0

    def capture(self):
        self._captures += 1
        # 返回模拟 JPEG 数据，中间位置最清晰
        return b'\xff\xd8' + b'\x00' * 500 + b'\xff\xd9'


class TestAutofocus(unittest.TestCase):

    def setUp(self):
        self.stage = FakeStage()
        self.cam = FakeCam()
        self.af = autofocus.Autofocus(self.stage, self.cam, z_range=(-200, 200), step=100)

    def test_sharpness_none_returns_zero(self):
        score = self.af._evaluate_sharpness(None)
        self.assertEqual(score, 0.0)

    def test_sharpness_small_data_returns_zero(self):
        score = self.af._evaluate_sharpness(b'\x00')
        self.assertEqual(score, 0.0)

    def test_sharpness_positive(self):
        score = self.af._evaluate_sharpness(b'\x00' * 200 + b'\xff' * 200)
        self.assertGreater(score, 0.0)

    def test_sharpness_blurry_lower_than_sharp(self):
        blurry = bytes(range(256)) * 4
        sharp = bytes([i % 2 * 255 for i in range(1024)])
        score_b = self.af._evaluate_sharpness(blurry)
        score_s = self.af._evaluate_sharpness(sharp)
        self.assertGreater(score_s, score_b)

    def test_focus_returns_dict(self):
        result = self.af.focus()
        self.assertIn("position", result)
        self.assertIn("sharpness", result)

    def test_focus_moves_stage(self):
        self.af.focus()
        self.assertGreater(len(self.stage._move_log), 0)

    def test_focus_captures_images(self):
        self.cam._captures = 0
        self.af.focus()
        self.assertGreater(self.cam._captures, 0)

    def test_focus_around(self):
        result = self.af.focus_around(5000, spread=100, step=50)
        self.assertIn("position", result)

    def test_get_state(self):
        state = self.af.get_state()
        self.assertEqual(state["z_range"], (-200, 200))
        self.assertEqual(state["step"], 100)

    def test_callback_called(self):
        calls = []
        self.af.focus(callback=lambda z, s: calls.append((z, s)))
        self.assertGreater(len(calls), 0)


if __name__ == "__main__":
    unittest.main()
