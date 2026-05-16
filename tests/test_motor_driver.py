"""
motor_driver.py 单元测试 — 使用 Mock Pin 验证步进序列。

运行方式（CPython）:
    cd esp32-smart-microscope && python -m pytest tests/test_motor_driver.py -v
"""

import sys
import unittest

# ---- Mock machine.Pin ----

class MockPin:
    """替代 machine.Pin，记录引脚状态用于断言。"""
    OUT = 1
    IN = 0

    _instances = {}  # pin_number → MockPin

    def __init__(self, number, mode=None):
        self.number = number
        self.mode = mode
        self._state = 0
        MockPin._instances[number] = self

    def on(self):
        self._state = 1

    def off(self):
        self._state = 0

    def value(self):
        return self._state

    @classmethod
    def reset(cls):
        cls._instances = {}

    @classmethod
    def state_of(cls, pin_number):
        """返回指定引脚的当前状态 (0/1)"""
        return cls._instances[pin_number]._state

    @classmethod
    def states_of(cls, *pin_numbers):
        """返回多个引脚的状态列表"""
        return [cls.state_of(p) for p in pin_numbers]


# 注入 Mock
sys.modules['machine'] = type(sys)('machine')
sys.modules['machine'].Pin = MockPin

# 现在可以安全导入
from motor_driver import MotorDriver


class TestMotorDriver(unittest.TestCase):

    def setUp(self):
        MockPin.reset()
        self.motor = MotorDriver(in1=4, in2=5, in3=6, in4=7, delay_ms=4)
        self.motor._testing = True  # 跳过延时加速测试

    def tearDown(self):
        self.motor.release()

    # ====== 基本步进测试 ======

    def test_step_forward_one_advances_sequence(self):
        initial = self.motor._step_pos
        self.motor.step(1)
        self.assertEqual(self.motor._step_pos, (initial + 1) % 8)

    def test_step_backward_one_retreats_sequence(self):
        initial = self.motor._step_pos
        self.motor.step(-1)
        self.assertEqual(self.motor._step_pos, (initial - 1) % 8)

    def test_step_forward_8_returns_to_same_phase(self):
        """8 步（一个完整周期）后序列位置相同"""
        initial = self.motor._step_pos
        self.motor.step(8)
        self.assertEqual(self.motor._step_pos, initial)

    def test_step_4096_full_rotation(self):
        """4096 步为一整圈"""
        initial = self.motor._step_pos
        self.motor.step(4096)
        self.assertEqual(self.motor._step_pos, initial)
        self.assertEqual(self.motor.get_position(), 4096)

    # ====== 位置跟踪 ======

    def test_position_tracks_forward_steps(self):
        self.motor.step(100)
        self.assertEqual(self.motor.get_position(), 100)

    def test_position_tracks_backward_steps(self):
        self.motor.step(100)
        self.motor.step(-30)
        self.assertEqual(self.motor.get_position(), 70)

    def test_position_tracks_negative(self):
        self.motor.step(-50)
        self.assertEqual(self.motor.get_position(), -50)

    def test_reset_position(self):
        self.motor.step(200)
        self.motor.reset_position()
        self.assertEqual(self.motor.get_position(), 0)

    # ====== 角度旋转 ======

    def test_rotate_360_equals_4096_steps(self):
        initial_pos = self.motor.get_position()
        self.motor.rotate_deg(360)
        self.assertEqual(self.motor.get_position() - initial_pos, 4096)

    def test_rotate_negative_90_equals_negative_1024(self):
        initial_pos = self.motor.get_position()
        self.motor.rotate_deg(-90)
        self.assertEqual(self.motor.get_position() - initial_pos, -1024)

    # ====== 速度控制 ======

    def test_set_speed_updates_delay(self):
        self.motor.set_speed(2)
        self.assertEqual(self.motor._delay_ms, 2)

    def test_set_speed_rejects_too_small(self):
        self.motor.set_speed(0)
        self.assertEqual(self.motor._delay_ms, 4)  # 未改变

    def test_step_respects_custom_delay(self):
        # 测试自定义 delay 参数被临时使用（不改变默认值）
        default = self.motor._delay_ms
        self.motor.step(1, delay_ms=1)
        self.assertEqual(self.motor._delay_ms, default)

    # ====== 线圈状态 ======

    def test_release_sets_all_pins_off(self):
        self.motor.release()
        for i in range(4):
            self.assertEqual(self.motor._coil_state[i], 0)

    def test_step_sets_valid_coil_states(self):
        """每一步的线圈状态都在有效序列中"""
        for _ in range(50):
            self.motor.step(1)
            self.assertIn(self.motor._coil_state, MotorDriver._HALFSTEP_SEQ)

    def test_sequence_is_eight_beat(self):
        """验证半步序列有 8 拍"""
        self.assertEqual(len(MotorDriver._HALFSTEP_SEQ), 8)

    def test_sequence_each_beat_2_active_coils(self):
        """每拍恰好有 1-2 个线圈激活"""
        for seq in MotorDriver._HALFSTEP_SEQ:
            active = sum(seq)
            self.assertIn(active, [1, 2])

    # ====== 引脚输出验证 ======

    def test_step_forward_to_first_position_sets_pins(self):
        """单步后验证引脚状态匹配序列"""
        self.motor.step(1)
        pos = self.motor._step_pos
        expected = MotorDriver._HALFSTEP_SEQ[pos]
        actual = [self.motor._coil_state[i] for i in range(4)]
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
