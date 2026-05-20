"""
语音控制模块

基于 ESP-SR (Espressif Speech Recognition) 的离线中文语音控制。
唤醒词"小天小天"，支持载物台控制、拍照、对焦等指令。

在 CPython 环境自动降级为模拟模式。
"""

import time

# 尝试导入 ESP-SR 相关模块
try:
    import esp_sr
    _HAS_ESP_SR = True
except ImportError:
    _HAS_ESP_SR = False

try:
    from machine import Pin, I2S
    _HAS_I2S = True
except ImportError:
    _HAS_I2S = False


# ====== 指令映射 ======

# 中文指令 → (意图, 参数)
_COMMAND_MAP = {
    # 移动指令
    "向上移动": ("move_rel", {"dy": 500}),
    "向下移动": ("move_rel", {"dy": -500}),
    "向左移动": ("move_rel", {"dx": -500}),
    "向右移动": ("move_rel", {"dx": 500}),
    "向上微调": ("move_rel", {"dy": 100}),
    "向下微调": ("move_rel", {"dy": -100}),
    "向左微调": ("move_rel", {"dx": -100}),
    "向右微调": ("move_rel", {"dx": 100}),
    "向上对焦": ("move_rel", {"dz": 200}),
    "向下对焦": ("move_rel", {"dz": -200}),

    # 回零
    "回零": ("home", {}),
    "回到原点": ("home", {}),

    # 拍照
    "拍照": ("capture", {}),
    "拍摄照片": ("capture", {}),

    # 自动对焦
    "自动对焦": ("autofocus", {}),
    "对焦": ("autofocus", {}),

    # LED 控制
    "开灯": ("led_on", {}),
    "关灯": ("led_off", {}),
    "灯亮一点": ("led_brighter", {}),
    "灯暗一点": ("led_dimmer", {}),
    "灯光最亮": ("led_max", {}),
    "灯光最暗": ("led_min", {}),

    # 预设点
    "保存位置": ("save_preset", {}),
    "位置一": ("recall_preset", {"slot": 0}),
    "位置二": ("recall_preset", {"slot": 1}),
    "位置三": ("recall_preset", {"slot": 2}),
    "位置四": ("recall_preset", {"slot": 3}),
    "位置五": ("recall_preset", {"slot": 4}),
    "位置六": ("recall_preset", {"slot": 5}),

    # 状态查询
    "当前位置": ("get_position", {}),

    # 停止
    "停止": ("stop", {}),
    "紧急停止": ("stop", {}),

    # 退出语音
    "退出语音": ("exit_voice", {}),
    "停止监听": ("exit_voice", {}),
}


class VoiceController:
    """离线中文语音识别控制器。

    使用 ESP-SR 唤醒词引擎 + 多命令词识别。
    唤醒词："小天小天"。
    """

    WAKE_WORD = "小天小天"

    # ESP-SR 中文命令词 ID 映射
    COMMAND_IDS = [
        "向上移动", "向下移动", "向左移动", "向右移动",
        "向上微调", "向下微调", "向左微调", "向右微调",
        "向上对焦", "向下对焦",
        "回零", "回到原点",
        "拍照", "拍摄照片",
        "自动对焦", "对焦",
        "开灯", "关灯",
        "灯亮一点", "灯暗一点",
        "灯光最亮", "灯光最暗",
        "保存位置",
        "位置一", "位置二", "位置三",
        "位置四", "位置五", "位置六",
        "当前位置",
        "停止", "紧急停止",
        "退出语音", "停止监听",
    ]

    def __init__(self, system_manager, stage, led, cam=None):
        """
        Args:
            system_manager: SystemManager 实例
            stage: StageController 实例
            led: LedController 实例
            cam: CameraController 实例 (可选)
        """
        self._sys = system_manager
        self._stage = stage
        self._led = led
        self._cam = cam

        self._active = False
        self._listening = False
        self._wake_detected = False
        self._last_command = ""
        self._command_handler = None

    # ====== 生命周期 ======

    def init(self, mic_data_pin=None, mic_clk_pin=None, mic_ws_pin=None):
        """初始化麦克风和 ESP-SR 引擎。

        Args:
            mic_data_pin: I2S 数据引脚
            mic_clk_pin: I2S 时钟引脚
            mic_ws_pin: I2S 字选引脚
        """
        if _HAS_ESP_SR and _HAS_I2S:
            try:
                # 初始化 I2S 麦克风
                self._i2s = I2S(
                    0,
                    sck=Pin(mic_clk_pin or 42),
                    ws=Pin(mic_ws_pin or 2),
                    sd=Pin(mic_data_pin or 41),
                    mode=I2S.RX,
                    bits=16,
                    format=I2S.MONO,
                    rate=16000,
                    ibuf=2880,
                )

                # 初始化 ESP-SR 唤醒引擎
                self._wake_engine = esp_sr.WakeWordEngine(
                    model="hilexin",           # 中文唤醒词模型
                    wake_words=[self.WAKE_WORD],
                )

                # 初始化命令词识别引擎
                self._cmd_engine = esp_sr.CommandEngine(
                    commands=self.COMMAND_IDS,
                    lang="cn",
                )

                self._active = True
                print(f"[Voice] ESP-SR 初始化完成，唤醒词: {self.WAKE_WORD}")
                return True

            except Exception as e:
                print(f"[Voice] ESP-SR 初始化失败: {e}")
                return False
        else:
            # CPython 模拟模式
            self._active = True
            print(f"[Voice] 模拟模式 (未检测到 ESP-SR)")
            return True

    def deinit(self):
        """释放语音识别资源。"""
        self._listening = False
        self._active = False
        if _HAS_ESP_SR:
            try:
                self._wake_engine.deinit()
                self._cmd_engine.deinit()
                self._i2s.deinit()
            except Exception:
                pass

    # ====== 监听循环 ======

    def start_listening(self, callback=None):
        """开始监听（非阻塞，需循环调用 process）。"""
        if not self._active:
            return False
        self._listening = True
        self._command_handler = callback
        print(f"[Voice] 开始监听...")
        return True

    def stop_listening(self):
        """停止监听。"""
        self._listening = False
        print(f"[Voice] 停止监听")

    def process(self):
        """处理一帧音频数据（需在主循环中高频调用）。

        Returns:
            str | None: 识别到的指令文本，或 None
        """
        if not self._listening or not self._active:
            return None

        if not _HAS_ESP_SR:
            return None  # 模拟模式无输入

        try:
            # 从 I2S 读取音频帧
            audio_data = self._i2s.read(2880)

            if not self._wake_detected:
                # 等待唤醒词
                detected = self._wake_engine.detect(audio_data)
                if detected:
                    self._wake_detected = True
                    print("[Voice] 唤醒词检测到!")
                    return "__WAKE__"
            else:
                # 识别命令词
                cmd_id = self._cmd_engine.recognize(audio_data)
                if cmd_id >= 0 and cmd_id < len(self.COMMAND_IDS):
                    command = self.COMMAND_IDS[cmd_id]
                    self._wake_detected = False
                    self._last_command = command
                    self._dispatch(command)
                    return command

        except Exception as e:
            print(f"[Voice] 处理错误: {e}")

        return None

    # ====== 指令分发 ======

    def _dispatch(self, command):
        """执行语音指令。"""
        intent = _COMMAND_MAP.get(command)
        if intent is None:
            print(f"[Voice] 未知指令: {command}")
            return

        action, params = intent
        self._execute(action, params)

        if self._command_handler:
            self._command_handler(command, action, params)

    def _execute(self, action, params):
        """执行系统操作。"""
        try:
            if action == "move_rel":
                self._sys.move_rel(**params)
            elif action == "home":
                self._sys.home()
            elif action == "capture":
                if self._cam:
                    import time
                    fn = f"/sd/photo_{int(time.time())}.jpg"
                    self._cam.capture_to_file(fn)
            elif action == "autofocus":
                pass  # 由 autofocus 模块实现
            elif action == "led_on":
                self._led.on()
            elif action == "led_off":
                self._led.off()
            elif action == "led_brighter":
                state = self._led.get_state()
                self._led.set_brightness(min(100, state["brightness"] + 20))
            elif action == "led_dimmer":
                state = self._led.get_state()
                self._led.set_brightness(max(0, state["brightness"] - 20))
            elif action == "led_max":
                self._led.set_brightness(100)
            elif action == "led_min":
                self._led.set_brightness(5)
            elif action == "save_preset":
                pos = self._stage.get_position()
                self._sys.save_preset(pos)
            elif action == "recall_preset":
                preset = self._sys.get_preset(params["slot"])
                if preset:
                    self._sys.move_to(**preset)
            elif action == "get_position":
                pos = self._stage.get_position()
                print(f"[Voice] 当前位置: X={pos['x']:.0f} Y={pos['y']:.0f} Z={pos['z']:.0f} μm")
            elif action == "stop":
                self._stage.release_all()
            elif action == "exit_voice":
                self.stop_listening()
        except Exception as e:
            print(f"[Voice] 指令执行失败: {action} — {e}")

    # ====== 文本转语音 ======

    def speak(self, text):
        """文字转语音反馈（需要扬声器 + I2S DAC）。"""
        if _HAS_ESP_SR:
            try:
                esp_sr.speak(text, lang="cn")
            except Exception:
                pass
        print(f"[Voice] TTS: {text}")

    # ====== 状态 ======

    def get_state(self):
        return {
            "active": self._active,
            "listening": self._listening,
            "wake_detected": self._wake_detected,
            "last_command": self._last_command,
            "has_esp_sr": _HAS_ESP_SR,
        }

    def is_active(self):
        return self._active

    def is_listening(self):
        return self._listening
