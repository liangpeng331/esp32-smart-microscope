"""
LVGL 9.x 触摸屏控制界面

Waveshare ESP32-P4-WIFI6-Touch-LCD-4B:
- 4" 720×720 IPS 显示
- GT911 电容触控 (I2C)
- 显示驱动通过 ESP-IDF 组件提供

界面布局适配 720×720 方屏，中文显示。

lvgl 通过延迟导入加载，模块可在 CPython 环境安全 import。
"""

# ====== 界面常量 ======

SCREEN_W = 720
SCREEN_H = 720

# 配色 (十六进制，运行时通过 _lv_color 转换为 lvgl 颜色)
_HEX_BG = 0x1A1A2E
_HEX_CARD = 0x16213E
_HEX_ACCENT = 0x0F3460
_HEX_PRIMARY = 0x4CAF50
_HEX_WARN = 0xFF9800
_HEX_TEXT = 0xE0E0E0
_HEX_WHITE = 0xFFFFFF
_HEX_SUBTLE = 0x888888


def _lv_color(hex_val):
    """十六进制转 lvgl 颜色，lvgl 不可用时返回 None。"""
    try:
        import lvgl as lv
        return lv.color_hex(hex_val)
    except ImportError:
        return None

def _lv_font(size):
    """获取 lvgl 字体，lvgl 不可用时返回 None。"""
    try:
        import lvgl as lv
        return getattr(lv, f'font_montserrat_{size}', None)
    except ImportError:
        return None


class TouchUI:
    """显微镜主控界面。"""

    def __init__(self, stage_controller, led_controller, system_manager=None, camera_controller=None, voice_controller=None):
        """
        Args:
            stage_controller: StageController 实例
            led_controller: LedController 实例
            system_manager: SystemManager 实例 (可选)
            camera_controller: CameraController 实例 (可选)
            voice_controller: VoiceController 实例 (可选)
        """
        self._stage = stage_controller
        self._led = led_controller
        self._sys = system_manager
        self._cam = camera_controller
        self._voice = voice_controller

        self._speed = "中"
        self._step_size = 100  # 点动步长 (μm)

        # 延迟加载 lvgl
        try:
            import lvgl as lv
            self._lv = lv
        except ImportError:
            self._lv = None

        if self._lv is not None:
            self._build_ui()
        else:
            print("[TouchUI] lvgl 不可用，UI 未初始化")

    # ====== UI 构建 ======

    def _build_ui(self):
        """构建完整界面。"""
        lv = self._lv
        self._scr = lv.screen_active()
        self._scr.set_style_bg_color(_lv_color(_HEX_BG), 0)

        self._build_title()
        self._build_camera_bar()
        self._build_position_panel()
        self._build_speed_selector()
        self._build_action_buttons()
        self._build_led_panel()
        self._build_presets_bar()

        # 定时刷新位置
        self._pos_timer = lv.timer_create(self._update_position, 250, None)

    def _build_title(self):
        """顶部标题栏。"""
        lv = self._lv
        title = lv.label(self._scr)
        title.set_text("ESP32-P4 智能显微镜")
        title.set_style_text_color(_lv_color(_HEX_WHITE), 0)
        title.set_style_text_font(_lv_font(22), 0)
        title.align(lv.ALIGN_TOP_MID, 0, 12)

        subtitle = lv.label(self._scr)
        subtitle.set_text("广东童园科技有限公司")
        subtitle.set_style_text_color(_lv_color(_HEX_SUBTLE), 0)
        subtitle.set_style_text_font(_lv_font(14), 0)
        subtitle.align(lv.ALIGN_TOP_MID, 0, 40)

    def _build_camera_bar(self):
        """摄像头 + 语音快捷控制栏（标题下方）。"""
        lv = self._lv
        y = 62

        # 预览开关（有摄像头时显示）
        if self._cam is not None:
            self._cam_preview_btn = lv.button(self._scr)
            self._cam_preview_btn.set_size(80, 32)
            self._cam_preview_btn.align(lv.ALIGN_TOP_LEFT, 30, y)
            self._cam_preview_lbl = lv.label(self._cam_preview_btn)
            self._cam_preview_lbl.set_text("取景")
            self._cam_preview_lbl.center()
            self._cam_preview_btn.add_event_cb(
                lambda e: self._toggle_camera_preview(),
                lv.EVENT.CLICKED, None
            )

            # 拍照按钮
            btn = lv.button(self._scr)
            btn.set_size(70, 32)
            btn.align(lv.ALIGN_TOP_LEFT, 120, y)
            btn.set_style_bg_color(_lv_color(_HEX_PRIMARY), 0)
            lbl = lv.label(btn)
            lbl.set_text("拍照")
            lbl.center()
            btn.add_event_cb(lambda e: self._on_capture_photo(), lv.EVENT.CLICKED, None)

            # 摄像头状态
            self._cam_status_lbl = lv.label(self._scr)
            self._cam_status_lbl.set_text("摄像头就绪")
            self._cam_status_lbl.set_style_text_color(_lv_color(_HEX_SUBTLE), 0)
            self._cam_status_lbl.align(lv.ALIGN_TOP_LEFT, 200, y + 5)

        # 语音开关（有语音模块时显示）
        voice_x = 310
        if self._voice is not None:
            self._voice_btn = lv.button(self._scr)
            self._voice_btn.set_size(70, 32)
            self._voice_btn.align(lv.ALIGN_TOP_LEFT, voice_x, y)
            self._voice_btn_lbl = lv.label(self._voice_btn)
            self._voice_btn_lbl.set_text("语音")
            self._voice_btn_lbl.center()
            self._voice_btn.add_event_cb(
                lambda e: self._toggle_voice(),
                lv.EVENT.CLICKED, None
            )

            self._voice_status_lbl = lv.label(self._scr)
            self._voice_status_lbl.set_text("语音就绪")
            self._voice_status_lbl.set_style_text_color(_lv_color(_HEX_SUBTLE), 0)
            self._voice_status_lbl.align(lv.ALIGN_TOP_LEFT, voice_x + 80, y + 5)

    def _build_position_panel(self):
        """位置显示 + XY 方向键。"""
        lv = self._lv
        # 左侧位置数值
        self._pos_labels = {}
        y_start = 105
        for i, axis in enumerate(["x", "y", "z"]):
            lbl = lv.label(self._scr)
            lbl.set_style_text_color(_lv_color(_HEX_TEXT), 0)
            lbl.set_style_text_font(_lv_font(20), 0)
            lbl.align(lv.ALIGN_TOP_LEFT, 30, y_start + i * 45)
            self._pos_labels[axis] = lbl

        self._update_position(None)

        self._build_dpad(430, 110)
        self._build_z_buttons(580, 110)

        step_sizes = [10, 50, 100, 500]
        step_y = 280
        step_label = lv.label(self._scr)
        step_label.set_text("点动步长 (μm)")
        step_label.set_style_text_color(_lv_color(_HEX_SUBTLE), 0)
        step_label.align(lv.ALIGN_TOP_LEFT, 30, step_y)

        self._step_dd = lv.dropdown(self._scr)
        self._step_dd.set_options("\n".join(str(s) for s in step_sizes))
        self._step_dd.set_selected(2)
        self._step_dd.align(lv.ALIGN_TOP_LEFT, 30, step_y + 25)
        self._step_dd.set_size(100, 40)
        self._step_dd.add_event_cb(self._on_step_change, lv.EVENT.VALUE_CHANGED, None)

    def _build_dpad(self, cx, cy):
        """十字方向键 (X/Y 轴)。"""
        lv = self._lv
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
        lv = self._lv
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
        lv = self._lv
        y = 330
        label = lv.label(self._scr)
        label.set_text("速度")
        label.set_style_text_color(_lv_color(_HEX_TEXT), 0)
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
        lv = self._lv
        y = 390
        actions = [
            ("回零", _lv_color(_HEX_WARN), self._on_home_click),
            ("保存位置", _lv_color(_HEX_PRIMARY), self._on_save_preset),
            ("关于", _lv_color(_HEX_ACCENT), self._on_about),
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
        lv = self._lv
        y = 450

        label = lv.label(self._scr)
        label.set_text("LED 照明")
        label.set_style_text_color(_lv_color(_HEX_TEXT), 0)
        label.align(lv.ALIGN_TOP_LEFT, 30, y)

        self._led_slider = lv.slider(self._scr)
        self._led_slider.set_range(0, 100)
        self._led_slider.set_value(50, lv.ANIM.OFF)
        self._led_slider.set_size(300, 10)
        self._led_slider.align(lv.ALIGN_TOP_LEFT, 30, y + 30)
        self._led_slider.add_event_cb(self._on_led_slider, lv.EVENT.VALUE_CHANGED, None)

        self._led_label = lv.label(self._scr)
        self._led_label.set_text("50%")
        self._led_label.set_style_text_color(_lv_color(_HEX_PRIMARY), 0)
        self._led_label.align(lv.ALIGN_TOP_LEFT, 340, y + 25)

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
        lv = self._lv
        y = 560
        label = lv.label(self._scr)
        label.set_text("预设位置")
        label.set_style_text_color(_lv_color(_HEX_TEXT), 0)
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
        lv = self._lv
        timer = lv.timer_create(
            lambda t: self._move_axis(axis, direction),
            50,
            None
        )
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
        self._led_slider.set_value(brightness, self._lv.ANIM.OFF)
        self._led_label.set_text(f"{brightness}%")

    def _toggle_camera_preview(self):
        """开关摄像头实时取景。"""
        if self._cam is None:
            self._show_toast("摄像头未连接")
            return
        if self._cam._previewing:
            self._cam.stop_preview()
            self._cam_preview_lbl.set_text("取景")
            self._cam_status_lbl.set_text("预览已关闭")
        else:
            if self._cam.start_preview():
                self._cam_preview_lbl.set_text("停止")
                self._cam_status_lbl.set_text("预览中...")
            else:
                self._show_toast("预览启动失败")

    def _on_capture_photo(self):
        """拍照并保存到 SD 卡。"""
        if self._cam is None:
            return
        import time
        timestamp = time.time()
        filename = f"/sd/photo_{int(timestamp)}.jpg"
        if self._cam.capture_to_file(filename):
            self._show_toast(f"已保存: {filename}")
        else:
            self._show_toast("拍照失败")

    def _toggle_voice(self):
        """开关语音识别。"""
        if self._voice is None:
            return
        if self._voice.is_listening():
            self._voice.stop_listening()
            self._voice_btn_lbl.set_text("语音")
            self._voice_status_lbl.set_text("语音已关闭")
        else:
            if self._voice.start_listening():
                self._voice_btn_lbl.set_text("关闭")
                self._voice_status_lbl.set_text("唤醒词: 小天小天")
            else:
                self._show_toast("语音启动失败")

    def _on_about(self):
        self._show_alert("关于",
            "ESP32-P4 智能显微镜\n"
            "版本 1.0.0\n\n"
            "广东童园科技有限公司\n"
            "www.tongyuankj.com\n\n"
            "3 轴电动云台 | LED 调光\n"
            "800×600 显微摄影\n"
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
        lv = self._lv
        dialog = lv.msgbox(self._scr, title, msg, ["取消", "确认"], True)
        dialog.add_event_cb(
            lambda e: on_ok() if dialog.get_active_btn() == 1 else None,
            lv.EVENT.VALUE_CHANGED, None
        )

    def _show_alert(self, title, msg):
        """提示框。"""
        lv = self._lv
        lv.msgbox(self._scr, title, msg, ["确定"], True)

    def _show_toast(self, msg):
        """短暂提示。"""
        lv = self._lv
        toast = lv.label(self._scr)
        toast.set_text(msg)
        toast.set_style_bg_color(_lv_color(_HEX_PRIMARY), 0)
        toast.set_style_text_color(_lv_color(_HEX_WHITE), 0)
        toast.align(lv.ALIGN.BOTTOM_MID, 0, -30)
        lv.timer_create(lambda t: toast.delete(), 1500, None)
