# ESP32-P4 智能显微镜 — 部署指南

## 硬件清单

| 部件 | 型号 | 数量 |
|------|------|------|
| 主控板 | Waveshare ESP32-P4-WIFI6-Touch-LCD-4B | 1 |
| 步进电机 | 28BYJ-48 5V + ULN2003 驱动板 | 3 |
| 摄像头 | OV2640 / OV5640 (DVP 接口) | 1 |
| 限位开关 | 微动开关 (常开型) | 2 |
| LED | 高亮白光 LED + MOSFET 驱动模块 | 1 |
| 电源 | 5V 3A DC | 1 |
| MicroSD | 8-32GB Class 10 | 1 |
| 麦克风 (可选) | I2S MEMS (INMP441) | 1 |

## 引脚接线

### 步进电机 (ULN2003)

| 电机 | IN1 | IN2 | IN3 | IN4 |
|------|-----|-----|-----|-----|
| X 轴 | GPIO4 | GPIO5 | GPIO6 | GPIO7 |
| Y 轴 | GPIO8 | GPIO9 | GPIO10 | GPIO11 |
| Z 轴 | GPIO12 | GPIO13 | GPIO14 | GPIO15 |

### 限位开关

| 轴 | GPIO | 类型 |
|----|------|------|
| X | GPIO2 | 常开，触发=低 |
| Y | GPIO3 | 常开，触发=低 |

### 摄像头 (DVP)

| 信号 | GPIO |
|------|------|
| XCLK | 43 |
| SIOD (SDA) | 44 |
| SIOC (SCL) | 45 |
| D0–D7 | 14, 13, 12, 11, 42, 41, 40, 39 |
| VSYNC | 47 |
| HREF | 38 |
| PCLK | 8 |

### LED

| 信号 | GPIO |
|------|------|
| PWM | GPIO21 |

### I2S 麦克风 (可选)

| 信号 | GPIO |
|------|------|
| SD (数据) | 41 |
| SCK (时钟) | 42 |
| WS (字选) | 2 |

## MicroPython 烧录

### 1. 下载固件

ESP32-P4 MicroPython 固件从以下渠道获取:
- Waveshare Wiki: https://www.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-4B
- MicroPython 官方: https://micropython.org/download/

### 2. 烧录工具

```bash
# macOS
pip install esptool
esptool.py --chip esp32p4 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32p4 --port /dev/cu.usbmodem* write_flash -z 0x0 firmware.bin

# 或使用 Waveshare 提供的烧录工具
```

### 3. 上传代码

使用 `mpremote` 或 `ampy`:

```bash
pip install mpremote

# 上传所有 Python 文件
mpremote connect /dev/cu.usbmodem* cp config.py :config.py
mpremote connect /dev/cu.usbmodem* cp motor_driver.py :motor_driver.py
mpremote connect /dev/cu.usbmodem* cp stage_controller.py :stage_controller.py
mpremote connect /dev/cu.usbmodem* cp led_controller.py :led_controller.py
mpremote connect /dev/cu.usbmodem* cp system_manager.py :system_manager.py
mpremote connect /dev/cu.usbmodem* cp touch_ui.py :touch_ui.py
mpremote connect /dev/cu.usbmodem* cp wifi_server.py :wifi_server.py
mpremote connect /dev/cu.usbmodem* cp camera_controller.py :camera_controller.py
mpremote connect /dev/cu.usbmodem* cp voice_controller.py :voice_controller.py
mpremote connect /dev/cu.usbmodem* cp autofocus.py :autofocus.py
mpremote connect /dev/cu.usbmodem* cp timelapse.py :timelapse.py
mpremote connect /dev/cu.usbmodem* cp main.py :main.py

# 软复位
mpremote connect /dev/cu.usbmodem* reset
```

## 首次启动

1. 接通 5V 电源
2. 等待显示屏亮起（约 3-5 秒）
3. 屏幕显示 "ESP32-P4 智能显微镜" 界面
4. 系统自动执行: 显示→电机→摄像头→WiFi→UI 初始化
5. 启动日志通过串口输出 (115200 baud)

### WiFi 连接

- SSID: `Microscope`
- 密码: `12345678`
- IP: `192.168.4.1`
- HTTP API: `http://192.168.4.1/api/status`

### 首次使用流程

1. **回零**: 点击"回零"按钮，3 轴自动寻找限位开关
2. **对焦**: 用 Z 轴方向键或语音"向上对焦"/"向下对焦"
3. **照明**: 滑动 LED 亮度条到合适亮度
4. **拍照**: 点击"拍照"按钮
5. **保存位置**: 点击"保存位置"记录常用观察点

## 调试

### 串口监控

```bash
# macOS
screen /dev/cu.usbmodem* 115200

# Linux
screen /dev/ttyUSB0 115200
```

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 屏幕不亮 | 电源不足 | 使用 5V 2A 以上电源 |
| 电机不转 | ULN2003 未供电 | 检查驱动板 5V 供电 |
| 电机只振动 | 速度太快 | 调为"慢"档 |
| WiFi 搜不到 | 天线未接 | 检查 IPEX 天线连接 |
| 摄像头黑屏 | 排线松动 | 重新插拔 FPC 排线 |
| 限位无效 | 接线反了 | 检查 NO/NC 类型 |
| SD 卡不可写 | 格式不支持 | 格式化为 FAT32 |

### 测试模式（无硬件）

```bash
cd esp32-smart-microscope
python3 -m unittest discover -s tests -v
```

所有 186 个测试在 CPython 上可以通过。

## 硬件验证

在 MicroPython REPL 中运行硬件测试脚本：

```python
import hardware_test
hardware_test.run_all()
```

测试项目：
1. GPIO 引脚可用性（6 个关键引脚）
2. 3 轴步进电机（双向转动验证）
3. LED PWM 调光（开关/亮度/预设）
4. 摄像头采集（初始化/拍照/取景）
5. WiFi AP 模式（SSID 广播）
6. SD 卡读写（列出/写入/读取/删除）
7. 触摸屏（lvgl 模块导入）
8. I2S 麦克风（ESP-SR 初始化，可选）
