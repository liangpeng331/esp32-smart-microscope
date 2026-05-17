"""
system_manager.py 单元测试 — Mock stage/led + 内存文件系统。

运行方式:
    python -m unittest tests.test_system_manager -v
"""

import io
import json
import sys
import unittest

# ====== Mock 体系 ======

class MockStage:
    def __init__(self):
        self._position = {"x": 0, "y": 0, "z": 0}
        self._homed = False

    def get_position(self):
        return dict(self._position)

    def is_homed(self):
        return self._homed

    def set_speed(self, name):
        pass

    def move_to(self, x=None, y=None, z=None):
        if x is not None:
            self._position["x"] = x
        if y is not None:
            self._position["y"] = y
        if z is not None:
            self._position["z"] = z

    def move_rel(self, dx=None, dy=None, dz=None):
        if dx is not None:
            self._position["x"] += dx
        if dy is not None:
            self._position["y"] += dy
        if dz is not None:
            self._position["z"] += dz

    def home(self):
        self._homed = True


class MockLED:
    def __init__(self):
        self._brightness = 50
        self._on = True

    def get_state(self):
        return {"on": self._on, "brightness": self._brightness}

    def set_brightness(self, v):
        self._brightness = v

    def on(self):
        self._on = True

    def off(self):
        self._on = False


class MockFS:
    """内存文件系统，替代 SD 卡。"""
    _files = {}

    @classmethod
    def reset(cls):
        cls._files = {}

    @classmethod
    def open(cls, path, mode="r"):
        if "r" in mode:
            if path not in cls._files:
                raise OSError("file not found")
            return io.StringIO(cls._files[path])
        else:
            return MockFileWriter(path, cls._files)


class MockFileWriter:
    def __init__(self, path, store):
        self._path = path
        self._store = store
        self._buf = io.StringIO()

    def __enter__(self):
        return self._buf

    def __exit__(self, *args):
        self._store[self._path] = self._buf.getvalue()


# 注入 mock
sys.modules['machine'] = type(sys)('machine')
import system_manager as sm

_PRESETS_FILE = "/mock/presets.json"

class TestSystemManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        MockFS.reset()
        sm.__dict__['open'] = MockFS.open

    @classmethod
    def tearDownClass(cls):
        sm.__dict__.pop('open', None)

    def setUp(self):
        MockFS.reset()
        self.stage = MockStage()
        self.led = MockLED()
        self.sys = sm.SystemManager(self.stage, self.led, _PRESETS_FILE)

    # ====== 状态机 ======

    def test_initial_state_is_idle(self):
        self.assertEqual(self.sys.state, sm.SystemState.IDLE)

    def test_is_ready_when_idle(self):
        self.assertTrue(self.sys.is_ready())

    def test_not_ready_when_moving(self):
        self.sys.set_state(sm.SystemState.MOVING)
        self.assertFalse(self.sys.is_ready())

    def test_set_state_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.sys.set_state("FLYING")

    def test_error_state_stores_message(self):
        self.sys.set_state(sm.SystemState.ERROR, "马达过载")
        self.assertEqual(self.sys.state, sm.SystemState.ERROR)
        self.assertEqual(self.sys.error_message, "马达过载")

    # ====== 预设点存取 ======

    def test_save_preset_auto_slot(self):
        pos = {"x": 100, "y": 200, "z": 300}
        slot = self.sys.save_preset(pos)
        self.assertGreaterEqual(slot, 0)
        self.assertEqual(self.sys.get_preset(slot), pos)

    def test_save_preset_specific_slot(self):
        self.sys.save_preset({"x": 1, "y": 2, "z": 3}, slot=3)
        self.assertEqual(self.sys.get_preset(3), {"x": 1, "y": 2, "z": 3})

    def test_save_preset_returns_minus_one_when_full(self):
        for i in range(6):
            self.sys.save_preset({"x": i, "y": 0, "z": 0})
        slot = self.sys.save_preset({"x": 99, "y": 99, "z": 99})
        self.assertEqual(slot, -1)

    def test_get_preset_out_of_range_returns_none(self):
        self.assertIsNone(self.sys.get_preset(6))
        self.assertIsNone(self.sys.get_preset(-1))

    def test_delete_preset(self):
        self.sys.save_preset({"x": 1, "y": 2, "z": 3}, slot=2)
        self.sys.delete_preset(2)
        self.assertIsNone(self.sys.get_preset(2))

    def test_list_presets(self):
        self.sys.save_preset({"x": 1, "y": 0, "z": 0}, slot=0)
        self.sys.save_preset({"x": 2, "y": 0, "z": 0}, slot=3)
        presets = self.sys.list_presets()
        self.assertEqual(len(presets), 2)
        self.assertIn((0, {"x": 1, "y": 0, "z": 0}), presets)

    def test_clear_all_presets(self):
        self.sys.save_preset({"x": 1, "y": 0, "z": 0})
        self.sys.save_preset({"x": 2, "y": 0, "z": 0})
        self.sys.clear_all_presets()
        self.assertEqual(self.sys.get_preset_count(), 0)

    def test_get_preset_count(self):
        self.assertEqual(self.sys.get_preset_count(), 0)
        self.sys.save_preset({"x": 1, "y": 0, "z": 0})
        self.sys.save_preset({"x": 2, "y": 0, "z": 0})
        self.assertEqual(self.sys.get_preset_count(), 2)

    # ====== 持久化 ======

    def test_presets_persist_to_json_file(self):
        self.sys.save_preset({"x": 10, "y": 20, "z": 30}, slot=0)
        self.assertIn(_PRESETS_FILE, MockFS._files)

        # 创建新的 manager 实例模拟重启
        sys2 = sm.SystemManager(MockStage(), MockLED(), _PRESETS_FILE)
        self.assertEqual(sys2.get_preset(0), {"x": 10, "y": 20, "z": 30})

    def test_load_skips_invalid_preset_format(self):
        MockFS._files[_PRESETS_FILE] = json.dumps({
            "presets": [{"x": 1, "y": 2, "z": 3}, {"bad": "format"}, {"x": 4, "y": 5, "z": 6}]
        })
        sys2 = sm.SystemManager(MockStage(), MockLED(), _PRESETS_FILE)
        self.assertEqual(sys2.get_preset(0), {"x": 1, "y": 2, "z": 3})
        self.assertIsNone(sys2.get_preset(1))
        self.assertEqual(sys2.get_preset(2), {"x": 4, "y": 5, "z": 6})

    # ====== 系统状态查询 ======

    def test_get_system_status(self):
        status = self.sys.get_system_status()
        self.assertEqual(status["state"], sm.SystemState.IDLE)
        self.assertIn("position", status)
        self.assertIn("led", status)
        self.assertIn("homed", status)
        self.assertEqual(status["presets_count"], 0)

    # ====== 运动操作（带状态保护） ======

    def test_home_sets_state_homing_then_idle(self):
        self.assertTrue(self.sys.home())
        self.assertEqual(self.sys.state, sm.SystemState.IDLE)
        self.assertTrue(self.stage.is_homed())

    def test_move_to_with_state_protection(self):
        self.assertTrue(self.sys.move_to(x=500))
        self.assertEqual(self.sys.state, sm.SystemState.IDLE)
        self.assertEqual(self.stage.get_position()["x"], 500)

    def test_move_refused_when_not_idle(self):
        self.sys.set_state(sm.SystemState.MOVING)
        self.assertFalse(self.sys.move_to(x=500))
        self.assertFalse(self.sys.home())

    def test_move_rel_with_state_protection(self):
        self.assertTrue(self.sys.move_rel(dx=100, dy=-50))
        pos = self.stage.get_position()
        self.assertEqual(pos["x"], 100)
        self.assertEqual(pos["y"], -50)


if __name__ == '__main__':
    unittest.main()
