"""
stage_controller.py 单元测试 — Mock 电机和限位开关。

运行方式:
    python -m unittest tests.test_stage_controller -v
"""

import sys
import unittest

# ====== Mock 体系 ======

class MockMotorDriver:
    """替代 MotorDriver，记录步数和方向。"""

    def __init__(self, in1, in2, in3, in4, delay_ms=4):
        self._total_steps = 0
        self._delay_ms = delay_ms
        self._last_direction = None
        self._released = False
        self.step_history = []  # (steps, delay_ms)

    def step(self, steps, delay_ms=None):
        if delay_ms is None:
            delay_ms = self._delay_ms
        self.step_history.append((steps, delay_ms))
        if steps > 0:
            self._last_direction = 1
        elif steps < 0:
            self._last_direction = -1
        self._total_steps += steps

    def rotate_deg(self, degrees, delay_ms=None):
        raise NotImplementedError

    def set_speed(self, delay_ms):
        self._delay_ms = delay_ms

    def release(self):
        self._released = True

    def get_position(self):
        return self._total_steps

    def reset_position(self):
        self._total_steps = 0


class MockPin:
    """Mock GPIO Pin，支持动态设置 value。"""
    OUT = 1
    IN = 0
    PULL_UP = 1

    _values = {}  # pin_number → 0/1

    def __init__(self, number, mode=None, pull=None):
        self.number = number
        self.mode = mode
        if mode == MockPin.IN:
            MockPin._values.setdefault(number, 1)  # 默认高电平（未触发）

    def value(self, v=None):
        if v is not None:
            MockPin._values[self.number] = v
        return MockPin._values.get(self.number, 0)

    def on(self):
        MockPin._values[self.number] = 1

    def off(self):
        MockPin._values[self.number] = 0

    @classmethod
    def reset(cls):
        cls._values = {}


# ====== Mock config ======

class MockConfig:
    UM_PER_STEP = 0.1953125   # 0.8mm / 4096步
    SPEED_PRESETS = {"快": 2, "中": 4, "慢": 8}
    DEFAULT_SPEED = "中"
    TRAVEL_LIMIT_UM = {
        "x": (-10000, 10000),
        "y": (-10000, 10000),
        "z": (-5000, 5000),
    }
    HOME_DIRECTION = {"x": -1, "y": -1, "z": -1}
    HOME_POSITION_UM = {"x": 0, "y": 0, "z": 5000}


# 注入 Mock
sys.modules['machine'] = type(sys)('machine')
sys.modules['machine'].Pin = MockPin

import config as real_config
real_config.UM_PER_STEP = MockConfig.UM_PER_STEP
real_config.SPEED_PRESETS = MockConfig.SPEED_PRESETS
real_config.DEFAULT_SPEED = MockConfig.DEFAULT_SPEED
real_config.TRAVEL_LIMIT_UM = MockConfig.TRAVEL_LIMIT_UM
real_config.HOME_DIRECTION = MockConfig.HOME_DIRECTION
real_config.HOME_POSITION_UM = MockConfig.HOME_POSITION_UM

# 替换 MotorDriver
import motor_driver
motor_driver.MotorDriver = MockMotorDriver

from stage_controller import StageController


class TestStageController(unittest.TestCase):

    def setUp(self):
        MockPin.reset()
        # 预触发限位开关（模拟已在限位处），避免回零测试超长循环
        MockPin._values[2] = 0  # X限位已触发
        MockPin._values[3] = 0  # Y限位已触发
        self.stage = StageController(
            x_pins=(4, 5, 6, 7),
            y_pins=(8, 9, 10, 11),
            z_pins=(12, 13, 14, 15),
            limit_x_pin=2,
            limit_y_pin=3,
            limit_z_pin=None,  # Z 无限位
        )
        # 加速测试
        for m in self.stage._axes.values():
            m._testing = True

    # ====== move_to ======

    def test_move_to_single_axis_x(self):
        target = 1000  # μm
        self.stage.move_to(x=target)
        pos = self.stage.get_position()
        self.assertAlmostEqual(pos["x"], target, delta=1)
        self.assertEqual(pos["y"], 0)
        self.assertEqual(pos["z"], 0)

    def test_move_to_multiple_axes(self):
        self.stage.move_to(x=500, y=300, z=-200)
        pos = self.stage.get_position()
        self.assertAlmostEqual(pos["x"], 500, delta=1)
        self.assertAlmostEqual(pos["y"], 300, delta=1)
        self.assertAlmostEqual(pos["z"], -200, delta=1)

    def test_move_to_negative_position(self):
        self.stage.move_to(x=-3000)
        pos = self.stage.get_position()
        self.assertAlmostEqual(pos["x"], -3000, delta=1)

    def test_move_to_beyond_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            self.stage.move_to(x=15000)

    def test_move_to_beyond_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            self.stage.move_to(x=-15000)

    def test_move_to_z_beyond_limit_raises(self):
        with self.assertRaises(ValueError):
            self.stage.move_to(z=6000)

    # ====== move_rel ======

    def test_move_rel_forward(self):
        self.stage.move_rel(dx=500)
        self.assertAlmostEqual(self.stage.get_position()["x"], 500, delta=1)

    def test_move_rel_backward(self):
        self.stage.move_rel(dx=-300)
        self.assertAlmostEqual(self.stage.get_position()["x"], -300, delta=1)

    def test_move_rel_accumulates(self):
        self.stage.move_rel(dx=100)
        self.stage.move_rel(dy=200)
        self.stage.move_rel(dx=50)
        pos = self.stage.get_position()
        self.assertAlmostEqual(pos["x"], 150, delta=1)
        self.assertAlmostEqual(pos["y"], 200, delta=1)

    def test_move_rel_beyond_limit_raises(self):
        self.stage.move_to(x=10000)  # 到边界
        with self.assertRaises(ValueError):
            self.stage.move_rel(dx=1)  # 超出

    # ====== 回零 ======

    def test_home_position_after_home(self):
        """回零后位置设置为 HOME_POSITION_UM"""
        self.stage.home()
        pos = self.stage.get_position()
        self.assertEqual(pos["x"], MockConfig.HOME_POSITION_UM["x"])
        self.assertEqual(pos["y"], MockConfig.HOME_POSITION_UM["y"])
        self.assertEqual(pos["z"], MockConfig.HOME_POSITION_UM["z"])

    def test_home_sets_homed_flag(self):
        self.assertFalse(self.stage.is_homed())
        self.stage.home()
        self.assertTrue(self.stage.is_homed())

    def test_home_z_without_limit_switch(self):
        """Z 轴无限位开关，直接设初始位置"""
        self.stage._axes["z"].step(500)  # 模拟之前有移动
        self.stage.home()
        # Z 轴应该被重置
        self.assertEqual(self.stage.get_position()["z"],
                         MockConfig.HOME_POSITION_UM["z"])

    def test_home_triggers_limit_switch(self):
        """设置限位开关为触发状态，回零应立即完成"""
        # 模拟 X 限位已触发
        MockPin._values[2] = 0
        self.stage.home()
        self.assertEqual(self.stage.get_position()["x"],
                         MockConfig.HOME_POSITION_UM["x"])

    # ====== 速度 ======

    def test_set_speed_fast(self):
        self.stage.set_speed("快")
        for m in self.stage._axes.values():
            self.assertEqual(m._delay_ms, 2)

    def test_set_speed_slow(self):
        self.stage.set_speed("慢")
        for m in self.stage._axes.values():
            self.assertEqual(m._delay_ms, 8)

    def test_set_speed_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.stage.set_speed("极快")

    # ====== 校准 ======

    def test_calibration_affects_step_count(self):
        """校准系数影响步数：系数越小，步数越多"""
        # 默认约 0.195 μm/步
        # 1000μm / 0.195 ≈ 5120 步
        initial_pos = self.stage._x.get_position()

        self.stage.move_to(x=1000)

        steps_used = self.stage._x.get_position() - initial_pos
        expected_approx = round(1000 / MockConfig.UM_PER_STEP)
        self.assertAlmostEqual(steps_used, expected_approx, delta=5)

    def test_set_calibration_changes_behavior(self):
        self.stage.set_calibration("x", um_per_step=1.0)  # 粗糙校准
        initial_pos = self.stage._x.get_position()

        self.stage.move_to(x=100)

        steps = self.stage._x.get_position() - initial_pos
        self.assertAlmostEqual(steps, 100, delta=2)  # 1μm/步 → 100步

    def test_set_calibration_rejects_zero(self):
        with self.assertRaises(ValueError):
            self.stage.set_calibration("x", 0)

    def test_set_calibration_rejects_invalid_axis(self):
        with self.assertRaises(ValueError):
            self.stage.set_calibration("w", 1.0)

    # ====== get_position ======

    def test_get_position_is_copy_not_reference(self):
        pos1 = self.stage.get_position()
        pos1["x"] = 9999
        pos2 = self.stage.get_position()
        self.assertNotEqual(pos2["x"], 9999)

    # ====== release_all ======

    def test_release_all_releases_all_motors(self):
        self.stage.release_all()
        for motor in self.stage._axes.values():
            self.assertTrue(motor._released)


if __name__ == '__main__':
    unittest.main()
