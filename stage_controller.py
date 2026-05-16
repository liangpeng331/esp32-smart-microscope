"""
3 轴电动云台控制器

参考 OpenFlexure 运动学模型，使用 28BYJ-48 步进电机驱动载物台 X/Y 轴
和物镜 Z 轴。位置以微米 (μm) 为单位。

核心公式：步数 = 目标位移(μm) / 校准系数(μm/步)
默认校准：0.8mm 丝杆导程 / 4096步/转 ≈ 0.195 μm/步
"""

from machine import Pin
from motor_driver import MotorDriver
import config


class StageController:
    """3 轴电动云台，支持绝对/相对定位、自动回零、限位保护。"""

    def __init__(self, x_pins, y_pins, z_pins,
                 limit_x_pin=None, limit_y_pin=None, limit_z_pin=None):
        """
        Args:
            x_pins: X 轴 4 个 GPIO (tuple)
            y_pins: Y 轴 4 个 GPIO
            z_pins: Z 轴 4 个 GPIO
            limit_x_pin: X 轴限位开关 GPIO (None = 无限位)
            limit_y_pin: Y 轴限位开关 GPIO
            limit_z_pin: Z 轴限位开关 GPIO
        """
        self._x = MotorDriver(*x_pins, delay_ms=config.SPEED_PRESETS[config.DEFAULT_SPEED])
        self._y = MotorDriver(*y_pins, delay_ms=config.SPEED_PRESETS[config.DEFAULT_SPEED])
        self._z = MotorDriver(*z_pins, delay_ms=config.SPEED_PRESETS[config.DEFAULT_SPEED])

        self._axes = {"x": self._x, "y": self._y, "z": self._z}

        # 限位开关（默认上拉，触发=低电平）
        self._limits = {}
        if limit_x_pin is not None:
            self._limits["x"] = Pin(limit_x_pin, Pin.IN, Pin.PULL_UP)
        if limit_y_pin is not None:
            self._limits["y"] = Pin(limit_y_pin, Pin.IN, Pin.PULL_UP)
        if limit_z_pin is not None:
            self._limits["z"] = Pin(limit_z_pin, Pin.IN, Pin.PULL_UP)

        # 校准系数 (μm/步)
        self._calibration = {
            "x": config.UM_PER_STEP,
            "y": config.UM_PER_STEP,
            "z": config.UM_PER_STEP,
        }

        # 当前位置 (μm)
        self._position = {"x": 0, "y": 0, "z": 0}

        # 行程范围 (μm)
        self._limits_um = dict(config.TRAVEL_LIMIT_UM)

        self._homed = False

    # ====== 运动控制 ======

    def move_to(self, x=None, y=None, z=None, blocking=True):
        """绝对定位，移动到指定微米坐标。

        Args:
            x, y, z: 目标位置 (μm)，None 表示不移动该轴
            blocking: True=阻塞直到完成，False=步进间可中断
        """
        targets = {"x": x, "y": y, "z": z}
        for axis, target in targets.items():
            if target is not None:
                self._check_limit(axis, target)
                current = self._position[axis]
                delta_um = target - current
                steps = self._um_to_steps(axis, abs(delta_um))
                direction = 1 if delta_um > 0 else -1
                motor = self._axes[axis]

                motor.step(steps * direction)
                self._position[axis] = target

    def move_rel(self, dx=None, dy=None, dz=None, blocking=True):
        """相对移动。

        Args:
            dx, dy, dz: 位移量 (μm)
        """
        if dx is not None:
            self.move_to(x=self._position["x"] + dx, blocking=blocking)
        if dy is not None:
            self.move_to(y=self._position["y"] + dy, blocking=blocking)
        if dz is not None:
            self.move_to(z=self._position["z"] + dz, blocking=blocking)

    # ====== 回零 ======

    def home(self):
        """3 轴自动回零。依次 X → Y → Z。

        每轴向限位开关方向移动，触发后停止并设置为原点偏移。
        Z 轴不回零（无上限位开关），仅设置初始位置。
        """
        home_order = ["x", "y", "z"]
        for axis in home_order:
            self._home_axis(axis)
        self._homed = True

    def _home_axis(self, axis):
        """单轴回零。"""
        if axis not in self._limits:
            # 无限位开关的轴（如 Z），仅设初始位置
            self._axes[axis].reset_position()
            self._position[axis] = config.HOME_POSITION_UM.get(axis, 0)
            return

        motor = self._axes[axis]
        limit_pin = self._limits[axis]
        direction = config.HOME_DIRECTION.get(axis, -1)

        # 向限位开关方向移动，触发即停
        max_steps = 20000  # 防止无限循环
        for i in range(max_steps):
            if self._limit_triggered(limit_pin):
                break
            motor.step(direction)

        # 反向退出限位开关
        backoff = 50  # 步
        motor.step(-direction * backoff)

        # 再次慢速逼近
        prev_delay = motor._delay_ms
        motor.set_speed(prev_delay * 2)  # 降速提高精度
        for i in range(200):
            if self._limit_triggered(limit_pin):
                break
            motor.step(direction)
        motor.set_speed(prev_delay)

        # 清零位置
        motor.reset_position()
        self._position[axis] = config.HOME_POSITION_UM.get(axis, 0)

    # ====== 查询 ======

    def get_position(self):
        """返回当前位置字典 {x, y, z} μm。"""
        return dict(self._position)

    def is_homed(self):
        """是否已完成回零。"""
        return self._homed

    # ====== 配置 ======

    def set_speed(self, preset_name):
        """设置速度档位。

        Args:
            preset_name: "快" | "中" | "慢"
        """
        if preset_name not in config.SPEED_PRESETS:
            raise ValueError(f"无效速度档位: {preset_name}")
        delay = config.SPEED_PRESETS[preset_name]
        for motor in self._axes.values():
            motor.set_speed(delay)

    def set_calibration(self, axis, um_per_step):
        """设置校准系数 (μm/步)。"""
        if axis not in self._calibration:
            raise ValueError(f"无效轴: {axis}")
        if um_per_step <= 0:
            raise ValueError("校准系数必须 > 0")
        self._calibration[axis] = um_per_step

    def release_all(self):
        """释放所有电机。"""
        for motor in self._axes.values():
            motor.release()

    # ====== 内部 ======

    def _check_limit(self, axis, target_um):
        """检查目标位置是否在行程范围内。"""
        lo, hi = self._limits_um.get(axis, (float('-inf'), float('inf')))
        if target_um < lo or target_um > hi:
            raise ValueError(
                f"{axis} 轴目标 {target_um}μm 超出行程范围 [{lo}, {hi}]μm"
            )

    def _um_to_steps(self, axis, um):
        """微米转步数。"""
        return max(1, round(um / self._calibration[axis]))

    def _limit_triggered(self, pin):
        """检查限位开关是否触发（低电平有效）。"""
        return pin.value() == 0
