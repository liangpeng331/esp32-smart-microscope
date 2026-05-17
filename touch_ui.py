"""
LVGL 9.x 触摸屏控制界面

Waveshare ESP32-P4-WIFI6-Touch-LCD-4B:
- 4" 720×720 IPS 显示
- GT911 电容触控 (I2C)
- 显示驱动通过 ESP-IDF 组件提供

界面布局适配 720×720 方屏，中文显示。
"""

import lvgl as lv


# ====== 界面常量 ======

SCREEN_W = 720
SCREEN_H = 720

# 配色
COLOR_BG = lv.color_hex(0x1A1A2E)         # 深蓝黑背景
COLOR_CARD = lv.color_hex(0x16213E)        # 卡片背景
COLOR_ACCENT = lv.color_hex(0x0F3460)      # 强调色
COLOR_PRIMARY = lv.color_hex(0x4CAF50)     # 主色调 绿色
COLOR_WARN = lv.color_hex(0xFF9800)        # 警告 橙色
COLOR_TEXT = lv.color_hex(0xE0E0E0)        # 文字色
COLOR_WHITE = lv.color_hex(0xFFFFFF)


class TouchUI:
    """显微镜主控界面。"""

    def __init__(self, stage_controller, led_controller, system_manager=None):
        """
        Args:
            stage_controller: StageController 实例
            led_controller: LedController 实例
            system_manager: SystemManager 实例 (可选)
        """
        self._stage = stage_controller
        self._led = led_controller
        self._sys = system_manager

        self._speed = "中"
        self._step_size = 100  # 点动步长 (μm)

        self._build_ui()

    # ====== UI 构建 ======

    def _build_ui(self):
        """构建完整界面。"""
        self._scr = lv.screen_active()
        self._scr.set_style_bg_color(COLOR_BG, 0)

        # --- 标题栏 ---
        self._build_title()

        # --- 位置显示 + 方向键 ---
        self._build_position_panel()

        # --- 速度选择 ---
        self._build_speed_selector()

        # --- 功能按钮 ---
        self._build_action_buttons()

        # --- LED 控制 ---
        self._build_led_panel()

        # --- 预设点 ---
        self._build_presets_bar()

        # 定时刷新位置
        self._pos_timer = lv.timer_create(self._update_position, 250, None)

    def _build_title(self):
        """顶部标题栏。"""
        title = lv.label(self._scr)
        title.set_text("ESP32-P4 智能显微镜")
        title.set_style_text_color(COLOR_WHITE, 0)
        title.set_style_text_font(lv.font_montserrat_22, 0)
        title.align(lv.ALIGN_TOP_MID, 0, 12)

        # 广东童园科技
        subtitle = lv.label(self._scr)
        subtitle.set_text("广东童园科技有限公司")
        subtitle.set_style_text_color(lv.color_hex(0x888888), 0)
        subtitle.set_style_text_font(lv.font_montserrat_14, 0)
        subtitle.align(lv.ALIGN_TOP_MID, 0, 40)

    def _build_position_panel(self):
        """位置显示 + XY 方向键。"""
        # 左侧位置数值
        self._pos_labels = {}
        y_start = 80
        for i, axis in enumerate(["x", "y", "z"]):
            lbl = lv.label(self._scr)
            lbl.set_style_text_color(COLOR_TEXT, 0)
            lbl.set_style_text_font(lv.font_montserrat_20, 0)
            lbl.align(lv.ALIGN_TOP_LEFT, 30, y_start + i * 45)
            self._pos_labels[axis] = lbl

        self._update_position(None)

        # 右侧方向键 (XY 十字)
        self._build_dpad(430, 110)

        # Z 轴上下按钮
        self._build_z_buttons(580, 110)

        # 步长选择
        step_sizes = [10, 50, 100, 500]
        step_y = 280
        step_label = lv.label(self._scr)
        step_label.set_text("点动步长 (μm)")
        step_label.set_style_text_color(lv.color_hex(0x888888), 0)
        step_label.align(lv.ALIGN_TOP_LEFT, 30, step_y)

        self._step_dd = lv.dropdown(self._scr)
        self._step_dd.set_options("\n".join(str(s) for s in step_sizes))
        self._step_dd.set_selected(2)  # 默认 100
        self._step_dd.align(lv.ALIGN_TOP_LEFT, 30, step_y + 25)
        self._step_dd.set_size(100, 40)
        self._step_dd.add_event_cb(self._on_step_change, lv.EVENT.VALUE_CHANGED, None)

    def _build_dpad(self, cx, cy):
        """十字方向键 (X/Y 轴)。"""
        btn_size = 60
        gap = 10

        # 上 (Y+)
        btn = lv.button(self._scr)
        btn.set_size(btn_size, btn_size)
        btn.align(lv.ALIGN_TOP_LEFT, cx, cy - btn_size - gap)
        lbl = lv.label(btn)
        lbl.set_text("▲")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("y", 1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("y", 1),
                         lv.EVENT.LONG_PRESSED, None)

        # 下 (Y-)
        btn = lv.button(self._scr)
        btn.set_size(btn_size, btn_size)
        btn.align(lv.ALIGN_TOP_LEFT, cx, cy + btn_size + gap)
        lbl = lv.label(btn)
        lbl.set_text("▼")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("y", -1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("y", -1),
                         lv.EVENT.LONG_PRESSED, None)

        # 左 (X-)
        btn = lv.button(self._scr)
        btn.set_size(btn_size, btn_size)
        btn.align(lv.ALIGN_TOP_LEFT, cx - btn_size - gap, cy)
        lbl = lv.label(btn)
        lbl.set_text("◄")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("x", -1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("x", -1),
                         lv.EVENT.LONG_PRESSED, None)

        # 右 (X+)
        btn = lv.button(self._scr)
        btn.set_size(btn_size, btn_size)
        btn.align(lv.ALIGN_TOP_LEFT, cx + btn_size + gap, cy)
        lbl = lv.label(btn)
        lbl.set_text("►")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("x", 1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("x", 1),
                         lv.EVENT.LONG_PRESSED, None)

    def _build_z_buttons(self, x, y):
        """Z 轴上下按钮。"""
        btn_w, btn_h = 80, 50

        # Z+
        btn = lv.button(self._scr)
        btn.set_size(btn_w, btn_h)
        btn.align(lv.ALIGN_TOP_LEFT, x, y)
        lbl = lv.label(btn)
        lbl.set_text("Z ▲")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("z", 1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("z", 1),
                         lv.EVENT.LONG_PRESSED, None)

        # Z-
        btn = lv.button(self._scr)
        btn.set_size(btn_w, btn_h)
        btn.align(lv.ALIGN_TOP_LEFT, x, y + btn_h + 10)
        lbl = lv.label(btn)
        lbl.set_text("Z ▼")
        lbl.center()
        btn.add_event_cb(lambda e: self._move_axis("z", -1), lv.EVENT.CLICKED, None)
        btn.add_event_cb(lambda e: self._start_repeat("z", -1),
                         lv.EVENT.LONG_PRESSED, None)

    def _build_speed_selector(self):
        """速度选择器。"""
        y = 330
        label = lv.label(self._scr)
        label.set_text("速度")
        label.set_style_text_color(COLOR_TEXT, 0)
        label.align(lv.ALIGN_TOP_LEFT, 30, y)

        speeds = ["慢", "中", "快"]
        self._speed_btns = {}
        for i, s in enumerate(speeds):
            btn = lv.button(self._scr)
            btn.set_size(80, 36)
            btn.align(lv.ALIGN_TOP_LEFT, 80 + i * 95, y - 8)
            lbl = lv.label(btn)
            lbl.set_text(s)
            lbl.center()
            btn.add_event_cb(
                lambda e, sp=s: self._on_speed_change(sp),
                lv.EVENT.CLICKED, None
            )
            self._speed_btns[s] = btn

    def _build_action_buttons(self):
        """功能按钮行：回零、预设、设置。"""
        y = 390
        actions = [
            ("回零", COLOR_WARN, self._on_home_click),
            ("保存位置", COLOR_PRIMARY, self._on_save_preset),
            ("关于", COLOR_ACCENT, self._on_about),
        ]
        for i, (text, color, callback) in enumerate(actions):
            btn = lv.button(self._scr)
            btn.set_size(120, 40)
            btn.align(lv.ALIGN_TOP_LEFT, 30 + i * 140, y)
            btn.set_style_bg_color(color, 0)
            lbl = lv.label(btn)
            lbl.set_text(text)
            lbl.center()
            btn.add_event_cb(lambda e, cb=callback: cb(), lv.EVENT.CLICKED, None)

    def _build_led_panel(self):
        """LED 亮度控制区域。"""
        y = 450

        # 标题
        label = lv.label(self._scr)
        label.set_text("LED 照明")
        label.set_style_text_color(COLOR_TEXT, 0)
        label.align(lv.ALIGN_TOP_LEFT, 30, y)

        # 亮度滑块
        self._led_slider = lv.slider(self._scr)
        self._led_slider.set_range(0, 100)
        self._led_slider.set_value(50, lv.ANIM.OFF)
        self._led_slider.set_size(300, 10)
        self._led_slider.align(lv.ALIGN_TOP_LEFT, 30, y + 30)
        self._led_slider.add_event_cb(self._on_led_slider, lv.EVENT.VALUE_CHANGED, None)

        # 亮度百分比
        self._led_label = lv.label(self._scr)
        self._led_label.set_text("50%")
        self._led_label.set_style_text_color(COLOR_PRIMARY, 0)
        self._led_label.align(lv.ALIGN_TOP_LEFT, 340, y + 25)

        # 预设档位按钮
        presets = ["暗", "中", "亮", "最亮"]
        for i, p in enumerate(presets):
            btn = lv.button(self._scr)
            btn.set_size(70, 32)
            btn.align(lv.ALIGN_TOP_LEFT, 30 + i * 85, y + 55)
            lbl = lv.label(btn)
            lbl.set_text(p)
            lbl.center()
            btn.add_event_cb(
                lambda e, pr=p: self._on_led_preset(pr),
                lv.EVENT.CLICKED, None
            )

    def _build_presets_bar(self):
        """预设点快捷栏。"""
        y = 560
        label = lv.label(self._scr)
        label.set_text("预设位置")
        label.set_style_text_color(COLOR_TEXT, 0)
        label.align(lv.ALIGN_TOP_LEFT, 30, y)

        self._preset_btns = []
        for i in range(6):
            btn = lv.button(self._scr)
            btn.set_size(100, 36)
            btn.align(lv.ALIGN_TOP_LEFT, 30 + i * 110, y + 30)
            lbl = lv.label(btn)
            lbl.set_text(f"P{i+1}")
            lbl.center()
            idx = i
            btn.add_event_cb(
                lambda e, n=idx: self._on_recall_preset(n),
                lv.EVENT.CLICKED, None
            )
            self._preset_btns.append(btn)

    # ====== 事件处理 ======

    def _move_axis(self, axis, direction):
        """点动移动一个步长单位。"""
        step = self._step_size * direction
        try:
            self._stage.move_rel(**{axis: step})
        except ValueError:
            pass  # 超出限位，忽略

    def _start_repeat(self, axis, direction):
        """长按开始连续移动（通过定时器实现）。"""
        # LVGL long press 后创建重复定时器
        timer = lv.timer_create(
            lambda t: self._move_axis(axis, direction),
            50,  # 20Hz
            None
        )
        # 用 2 秒超时自动停止
        lv.timer_create(lambda t: timer.delete(), 2000, None)

    def _on_step_change(self, e):
        selected = self._step_dd.get_selected()
        options = [10, 50, 100, 500]
        self._step_size = options[selected]

    def _on_speed_change(self, speed):
        self._speed = speed
        self._stage.set_speed(speed)

    def _on_home_click(self):
        """回零确认弹窗。"""
        self._show_confirm(
            "确认回零",
            "3 轴将自动回到原点，继续？",
            lambda: self._stage.home()
        )

    def _on_save_preset(self):
        """保存当前位置为预设点。"""
        if self._sys:
            pos = self._stage.get_position()
            self._sys.save_preset(pos)
            self._show_toast("位置已保存")

    def _on_recall_preset(self, index):
        """调用预设点位置。"""
        if self._sys:
            preset = self._sys.get_preset(index)
            if preset:
                self._stage.move_to(**preset)
                self._show_toast(f"已移动到 P{index+1}")

    def _on_led_slider(self, e):
        val = self._led_slider.get_value()
        self._led_label.set_text(f"{val}%")
        self._led.set_brightness(val)
        if val > 0 and not self._led.get_state()["on"]:
            self._led.on()

    def _on_led_preset(self, name):
        self._led.preset(name)
        brightness = self._led.get_state()["brightness"]
        self._led_slider.set_value(brightness, lv.ANIM.OFF)
        self._led_label.set_text(f"{brightness}%")

    def _on_about(self):
        self._show_alert("关于",
            "ESP32-P4 智能显微镜\n"
            "版本 1.0.0\n\n"
            "广东童园科技有限公司\n"
            "www.tongyuankj.com\n\n"
            "3 轴电动云台 | LED 调光\n"
            "720×720 IPS 触摸屏\n"
            "参考 OpenFlexure 设计"
        )

    # ====== 定时刷新 ======

    def _update_position(self, timer):
        """每秒刷新 4 次位置显示。"""
        try:
            pos = self._stage.get_position()
            for axis, lbl in self._pos_labels.items():
                val = pos.get(axis, 0)
                lbl.set_text(f"{axis.upper()}: {val:+.0f} μm")
        except Exception:
            pass

    # ====== 弹窗辅助 ======

    def _show_confirm(self, title, msg, on_ok):
        """确认对话框。"""
        dialog = lv.msgbox(self._scr, title, msg, ["取消", "确认"], True)
        dialog.add_event_cb(
            lambda e: on_ok() if dialog.get_active_btn() == 1 else None,
            lv.EVENT.VALUE_CHANGED, None
        )

    def _show_alert(self, title, msg):
        """提示框。"""
        lv.msgbox(self._scr, title, msg, ["确定"], True)

    def _show_toast(self, msg):
        """短暂提示。"""
        toast = lv.label(self._scr)
        toast.set_text(msg)
        toast.set_style_bg_color(COLOR_PRIMARY, 0)
        toast.set_style_text_color(COLOR_WHITE, 0)
        toast.align(lv.ALIGN.BOTTOM_MID, 0, -30)
        lv.timer_create(lambda t: toast.delete(), 1500, None)
