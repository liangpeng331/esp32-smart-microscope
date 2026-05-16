"""
28BYJ-48 + ULN2003 半步驱动模块

半步序列 (8 拍): A → AB → B → BC → C → CD → D → DA
每拍前进 0.0879° (360°/4096)，4096 步/转。
"""

from machine import Pin


class MotorDriver:
    """28BYJ-48 步进电机驱动，ULN2003 四线控制，半步模式。"""

    # 8 拍半步序列（按相线圈激活）
    _HALFSTEP_SEQ = [
        [1, 0, 0, 0],  # A
        [1, 1, 0, 0],  # AB
        [0, 1, 0, 0],  # B
        [0, 1, 1, 0],  # BC
        [0, 0, 1, 0],  # C
        [0, 0, 1, 1],  # CD
        [0, 0, 0, 1],  # D
        [1, 0, 0, 1],  # DA
    ]

    def __init__(self, in1, in2, in3, in4, delay_ms=4):
        """
        Args:
            in1–in4: GPIO 引脚编号
            delay_ms: 步间延迟 (ms)，越小越快
        """
        self._pins = [
            Pin(in1, Pin.OUT),
            Pin(in2, Pin.OUT),
            Pin(in3, Pin.OUT),
            Pin(in4, Pin.OUT),
        ]
        self._delay_ms = delay_ms
        self._step_pos = 0      # 当前序列位置 (0–7)
        self._total_steps = 0   # 累计步数（位置跟踪）

        self.release()

    def step(self, steps, delay_ms=None):
        """移动指定步数。正数为一个方向，负数为反方向。

        Args:
            steps: 步数，>0 正向，<0 反向
            delay_ms: 临时覆盖速度，None 使用默认值
        """
        if delay_ms is None:
            delay_ms = self._delay_ms

        direction = 1 if steps >= 0 else -1
        remaining = abs(steps)

        for _ in range(remaining):
            if direction > 0:
                self._step_pos = (self._step_pos + 1) % 8
            else:
                self._step_pos = (self._step_pos - 1) % 8

            self._set_coils(self._step_pos)
            self._delay_us(int(delay_ms * 1000))

            if direction > 0:
                self._total_steps += 1
            else:
                self._total_steps -= 1

    def rotate_deg(self, degrees, delay_ms=None):
        """旋转指定角度。

        Args:
            degrees: 角度（正=顺时针，负=逆时针）
        """
        steps = int((abs(degrees) / 360.0) * 4096)
        if degrees < 0:
            steps = -steps
        self.step(steps, delay_ms)

    def set_speed(self, delay_ms):
        """设置步间延迟 (ms)。"""
        if delay_ms >= 1:
            self._delay_ms = delay_ms

    def release(self):
        """释放所有线圈，防止电机待机过热。"""
        for pin in self._pins:
            pin.off()
        self._coil_state = [0, 0, 0, 0]

    def get_position(self):
        """返回累计步数。"""
        return self._total_steps

    def reset_position(self):
        """清零位置计数器。"""
        self._total_steps = 0

    def _set_coils(self, pos):
        """设置四路线圈状态。"""
        state = self._HALFSTEP_SEQ[pos]
        for i, pin in enumerate(self._pins):
            if state[i]:
                pin.on()
            else:
                pin.off()
        self._coil_state = state

    def _delay_us(self, us):
        """微秒级延时。MicroPython 用 ticks_us，CPython 用 time.sleep。
        单元测试中设置 _testing = True 可跳过延时。
        """
        if getattr(self, '_testing', False):
            return
        import time
        if hasattr(time, 'ticks_us'):
            # MicroPython
            start = time.ticks_us()
            while time.ticks_diff(time.ticks_us(), start) < us:
                pass
        else:
            # CPython (测试环境)
            time.sleep(us / 1_000_000)
