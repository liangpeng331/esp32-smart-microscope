"""
系统管理器：状态机、事件调度、预设点管理。

状态流转:
    IDLE → MOVING → IDLE
    IDLE → HOMING → IDLE
    任何状态 → ERROR → IDLE
"""

import json


class SystemState:
    IDLE = "IDLE"
    MOVING = "MOVING"
    HOMING = "HOMING"
    ERROR = "ERROR"


class SystemManager:
    """全局系统管理，协调各模块状态，管理预设点持久化。"""

    MAX_PRESETS = 6

    def __init__(self, stage_controller, led_controller, presets_file="/sd/presets.json"):
        """
        Args:
            stage_controller: StageController 实例
            led_controller: LedController 实例
            presets_file: 预设点 JSON 文件路径
        """
        self._stage = stage_controller
        self._led = led_controller
        self._presets_file = presets_file
        self._state = SystemState.IDLE
        self._presets = [None] * self.MAX_PRESETS
        self._error_message = ""

        self._load_presets()

    # ====== 状态机 ======

    @property
    def state(self):
        return self._state

    @property
    def error_message(self):
        return self._error_message

    def set_state(self, new_state, error_msg=""):
        if new_state not in (SystemState.IDLE, SystemState.MOVING,
                             SystemState.HOMING, SystemState.ERROR):
            raise ValueError(f"无效状态: {new_state}")
        self._state = new_state
        self._error_message = error_msg

    def is_ready(self):
        return self._state == SystemState.IDLE

    # ====== 预设点管理 ======

    def save_preset(self, position, slot=None):
        """保存当前位置到预设点。

        Args:
            position: 位置字典 {x, y, z}
            slot: 指定槽位 (0-5)，None 则自动选第一个空位

        Returns:
            int: 保存到的槽位编号，若满则返回 -1
        """
        pos = dict(position)
        if slot is not None:
            if 0 <= slot < self.MAX_PRESETS:
                self._presets[slot] = pos
                self._commit()
                return slot
            return -1

        for i in range(self.MAX_PRESETS):
            if self._presets[i] is None:
                self._presets[i] = pos
                self._commit()
                return i
        return -1

    def get_preset(self, index):
        """获取预设点位置。

        Args:
            index: 槽位编号 0-5

        Returns:
            dict 或 None
        """
        if 0 <= index < self.MAX_PRESETS:
            return self._presets[index]
        return None

    def list_presets(self):
        """返回所有预设点列表 [(index, position), ...]"""
        return [(i, p) for i, p in enumerate(self._presets) if p is not None]

    def delete_preset(self, index):
        """删除指定槽位的预设点。"""
        if 0 <= index < self.MAX_PRESETS:
            self._presets[index] = None
            self._commit()

    def clear_all_presets(self):
        """清除所有预设点。"""
        self._presets = [None] * self.MAX_PRESETS
        self._commit()

    def get_preset_count(self):
        return sum(1 for p in self._presets if p is not None)

    # ====== 系统状态查询 ======

    def get_system_status(self):
        """返回完整系统状态字典。"""
        return {
            "state": self._state,
            "error": self._error_message,
            "position": self._stage.get_position(),
            "homed": self._stage.is_homed(),
            "led": self._led.get_state(),
            "presets_count": self.get_preset_count(),
        }

    # ====== 运动操作（带状态管理） ======

    def home(self):
        """执行回零操作（带状态保护）。"""
        if not self.is_ready():
            return False
        try:
            self.set_state(SystemState.HOMING)
            self._stage.home()
            self.set_state(SystemState.IDLE)
            return True
        except Exception as e:
            self.set_state(SystemState.ERROR, str(e))
            return False

    def move_to(self, x=None, y=None, z=None):
        """绝对定位（带状态保护）。"""
        if not self.is_ready():
            return False
        try:
            self.set_state(SystemState.MOVING)
            self._stage.move_to(x=x, y=y, z=z)
            self.set_state(SystemState.IDLE)
            return True
        except Exception as e:
            self.set_state(SystemState.ERROR, str(e))
            return False

    def move_rel(self, dx=None, dy=None, dz=None):
        """相对定位（带状态保护）。"""
        if not self.is_ready():
            return False
        try:
            self.set_state(SystemState.MOVING)
            self._stage.move_rel(dx=dx, dy=dy, dz=dz)
            self.set_state(SystemState.IDLE)
            return True
        except Exception as e:
            self.set_state(SystemState.ERROR, str(e))
            return False

    # ====== 持久化 ======

    def _load_presets(self):
        """从 JSON 文件加载预设点。"""
        try:
            with open(self._presets_file, "r") as f:
                data = json.load(f)
                loaded = data.get("presets", [])
                for i, p in enumerate(loaded[:self.MAX_PRESETS]):
                    if p is not None and all(k in p for k in ("x", "y", "z")):
                        self._presets[i] = p
        except (OSError, ValueError):
            pass

    def _commit(self):
        """将预设点写入 JSON 文件。"""
        try:
            with open(self._presets_file, "w") as f:
                json.dump({"presets": self._presets}, f)
        except OSError:
            pass
