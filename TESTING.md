# ESP32-P4 智能显微镜 — 实机烧录与测试流程

从裸板到全功能验证的完整操作手册。

## 目录

1. [烧录前检查](#1-烧录前检查)
2. [固件烧录](#2-固件烧录)
3. [应用代码上传](#3-应用代码上传)
4. [首次启动验证](#4-首次启动验证)
5. [硬件逐项验证](#5-硬件逐项验证)
6. [功能子系统测试](#6-功能子系统测试)
7. [校准程序](#7-校准程序)
8. [老化测试](#8-老化测试)
9. [故障排查流程图](#9-故障排查流程图)

---

## 1. 烧录前检查

### 1.1 目视检查

在通电之前完成以下目视检查：

- [ ] **主控板**：ESP32-P4 开发板无物理损坏，元件无脱落
- [ ] **电机接线**：3 个 ULN2003 驱动板的 IN1-IN4 按 DEPLOY.md 引脚表正确连接
- [ ] **电机供电**：ULN2003 驱动板的 5V/GND 已连接（不要只靠 GPIO 供电）
- [ ] **摄像头排线**：FPC 排线完全插入 DVP 接口，金手指朝上，锁扣扣紧
- [ ] **限位开关**：X/Y 限位微动开关焊接牢固，信号线/地线无短路
- [ ] **LED 模块**：MOSFET 驱动模块正确连接，LED 正负极正确
- [ ] **天线**：IPEX 天线已接到 ESP32-C6 的 WiFi 天线座
- [ ] **SD 卡**：microSD 卡已插入卡槽，格式为 FAT32
- [ ] **电源**：使用 5V ≥3A 的 USB 电源适配器（不要用电脑 USB 口，电流不足）
- [ ] **USB 线**：数据线（非仅充电线），能传输数据

### 1.2 工具准备

| 工具 | 用途 | 获取方式 |
|------|------|----------|
| `esptool.py` | 固件烧录 | `pip install esptool` |
| `mpremote` | 文件上传 | `pip install mpremote` |
| 串口终端 | 日志查看 | `screen` / `picocom` / `miniterm` |
| 万用表 | 电压测量 | 硬件工具 |
| 手机/电脑 | WiFi 扫描 | 系统自带 |

### 1.3 万用表验证（可选）

在通电前用万用表蜂鸣档验证：

```
验证项目                          期望
GPIO4 ↔ ULN2003-IN1 (X轴)        导通
GPIO8 ↔ ULN2003-IN1 (Y轴)        导通
GPIO12 ↔ ULN2003-IN1 (Z轴)       导通
ULN2003 VCC ↔ 5V 电源正极         导通
ULN2003 GND ↔ 5V 电源负极         导通
GPIO2 ↔ 限位开关 X 信号线         导通
GPIO3 ↔ 限位开关 Y 信号线         导通
GPIO21 ↔ LED MOSFET 信号输入      导通
摄像头 FPC 各引脚无相邻短路        不导通
```

---

## 2. 固件烧录

### 2.1 进入下载模式

1. **断开** USB 数据线
2. **按住** 开发板上的 BOOT 键不放
3. **插入** USB 数据线（连接电脑）
4. **松开** BOOT 键
5. 开发板进入下载模式（屏幕不亮是正常的）

### 2.2 确认串口识别

```bash
# macOS
ls /dev/cu.usb*     # 应显示 /dev/cu.usbmodemXXXX

# Linux
ls /dev/ttyUSB*     # 应显示 /dev/ttyUSB0
```

如果未识别到串口：
- 检查 USB 线是否支持数据传输
- 检查是否安装了 CP210x 驱动（Linux 通常内置）
- 尝试重新进入下载模式

### 2.3 擦除 Flash

```bash
esptool.py --chip esp32p4 --port /dev/cu.usbmodem101 erase_flash
```

预期输出：
```
Chip is ESP32-P4
Erasing flash (this may take a while)...
Chip erase completed successfully
```

如果擦除失败：
- 确认已进入下载模式（BOOT 键 + 上电）
- 尝试降低波特率：添加 `--baud 115200`

### 2.4 写入固件

如果你已按 BUILD.md 编译了固件：

```bash
cd ~/micropython/ports/esp32

# 激活 ESP-IDF 环境
source ~/esp/esp-idf/export.sh

# 烧录
make BOARD=ESP32_P4_WAVESHARE_4B PORT=/dev/cu.usbmodem101 deploy
```

如果使用预编译固件：

```bash
esptool.py --chip esp32p4 --port /dev/cu.usbmodem101 \
    write_flash -z 0x0 firmware.bin
```

### 2.5 烧录后复位

烧录完成后：
1. **断开** USB 数据线
2. **重新插入** USB 数据线（正常上电，不按 BOOT）
3. 等待 3-5 秒让系统启动

### 2.6 验证 MicroPython REPL

打开串口终端：

```bash
# macOS
screen /dev/cu.usbmodem101 115200

# 或使用 mpremote
mpremote connect /dev/cu.usbmodem101
```

在 REPL 中按 Enter，应看到 `>>>` 提示符。输入：

```python
import sys
print(sys.version)
# MicroPython v1.24.0 on ...
print(sys.implementation)
# (name='micropython', version=(1, 24, 0), mpy=...)
```

---

## 3. 应用代码上传

### 3.1 批量上传

```bash
cd /path/to/esp32-smart-microscope

# 上传核心模块（按依赖顺序）
mpremote connect /dev/cu.usbmodem101 cp config.py :config.py
mpremote connect /dev/cu.usbmodem101 cp motor_driver.py :motor_driver.py
mpremote connect /dev/cu.usbmodem101 cp stage_controller.py :stage_controller.py
mpremote connect /dev/cu.usbmodem101 cp led_controller.py :led_controller.py
mpremote connect /dev/cu.usbmodem101 cp system_manager.py :system_manager.py
mpremote connect /dev/cu.usbmodem101 cp camera_controller.py :camera_controller.py
mpremote connect /dev/cu.usbmodem101 cp voice_controller.py :voice_controller.py
mpremote connect /dev/cu.usbmodem101 cp autofocus.py :autofocus.py
mpremote connect /dev/cu.usbmodem101 cp timelapse.py :timelapse.py
mpremote connect /dev/cu.usbmodem101 cp auto_exposure.py :auto_exposure.py
mpremote connect /dev/cu.usbmodem101 cp settings.py :settings.py
mpremote connect /dev/cu.usbmodem101 cp hardware_test.py :hardware_test.py
mpremote connect /dev/cu.usbmodem101 cp touch_ui.py :touch_ui.py
mpremote connect /dev/cu.usbmodem101 cp wifi_server.py :wifi_server.py
mpremote connect /dev/cu.usbmodem101 cp main.py :main.py
```

### 3.2 上传后验证

```bash
# 列出已上传文件
mpremote connect /dev/cu.usbmodem101 exec "import os; print(os.listdir('/'))"

# 预期输出应包含:
# ['main.py', 'config.py', 'motor_driver.py', 'stage_controller.py',
#  'led_controller.py', 'system_manager.py', 'touch_ui.py',
#  'wifi_server.py', 'camera_controller.py', 'voice_controller.py',
#  'autofocus.py', 'timelapse.py', 'auto_exposure.py', 'settings.py',
#  'hardware_test.py']
```

### 3.3 软复位启动

```bash
mpremote connect /dev/cu.usbmodem101 reset
```

此时 `main.py` 自动执行，串口终端应看到：

```
[显微镜] ESP32-P4 智能显微镜 启动中...
[显微镜] 版本 1.2.0 — 广东童园科技有限公司
[显微镜] 显示已预初始化          (或 警告: lvgl/display 模块未找到)
[显微镜] GT911 触摸初始化完成    (或 警告: touch 模块未找到)
[显微镜] 3 轴云台初始化完成
[显微镜] LED 照明初始化完成
[显微镜] 摄像头初始化完成
[显微镜] 系统管理器初始化完成
[显微镜] 用户设置已加载 (速度=中, LED=50%)
[显微镜] WiFi AP 就绪: Microscope @ 192.168.4.1
[显微镜] HTTP API 服务器已启动 (端口 80)
[显微镜] 自动曝光就绪
[显微镜] 触摸界面就绪
[显微镜] 系统就绪
```

---

## 4. 首次启动验证

### 4.1 显示屏验证

| 检查项 | 预期结果 |
|--------|----------|
| 背光点亮 | 屏幕亮起，无闪烁 |
| 启动画面 | 显示"ESP32-P4 智能显微镜"界面 |
| 触摸响应 | 手指点击各按钮有反馈 |
| 颜色正常 | 无严重色偏、画面撕裂 |

### 4.2 WiFi 验证

1. 用手机扫描 WiFi 网络
2. 应看到 SSID `Microscope`
3. 连接密码 `12345678`
4. 获取 IP 后，浏览器打开 `http://192.168.4.1/api/status`
5. 应返回 JSON 系统状态

```bash
# 或在电脑上测试
curl http://192.168.4.1/api/status
# {"state":"IDLE","position":{"x":0,"y":0,"z":5000},"presets":0}
```

### 4.3 REPL 快速检查

通过串口终端发送命令：

```python
# 检查电机
import config
from motor_driver import MotorDriver
m = MotorDriver(*config.X_AXIS_PINS, delay_ms=4)
m.step(10)
m.step(-10)
m.release()

# 检查 LED
from led_controller import LedController
led = LedController(config.LED_PIN, config.PWM_FREQ, config.PWM_MAX_DUTY)
led.on(); led.set_brightness(50); led.off()
```

---

## 5. 硬件逐项验证

运行完整硬件测试套件：

```python
import hardware_test
hardware_test.run_all()
```

### 5.1 预期输出

```
==================================================
ESP32-P4 智能显微镜 — 硬件验证
==================================================

--- GPIO 引脚测试 ---
  [PASS] X_AXIS (GPIO4) — 可用
  [PASS] Y_AXIS (GPIO8) — 可用
  [PASS] Z_AXIS (GPIO12) — 可用
  [PASS] LED (GPIO21) — 可用
  [PASS] LIMIT_X (GPIO2) — 可用
  [PASS] LIMIT_Y (GPIO3) — 可用

--- 步进电机测试 ---
  [PASS] X 轴 — 双向转动正常
  [PASS] Y 轴 — 双向转动正常
  [PASS] Z 轴 — 双向转动正常

--- LED 调光测试 ---
  [PASS] LED 开关 — 正常
  [PASS] LED 亮度 0% — 正常
  [PASS] LED 亮度 25% — 正常
  [PASS] LED 亮度 50% — 正常
  [PASS] LED 亮度 75% — 正常
  [PASS] LED 亮度 100% — 正常
  [PASS] LED 预设 '暗' — 正常
  [PASS] LED 预设 '中' — 正常
  [PASS] LED 预设 '亮' — 正常
  [PASS] LED 预设 '最亮' — 正常

--- 摄像头测试 ---
  [PASS] 摄像头初始化 — 成功
  [PASS] 拍照 — 成功 (XXXXX 字节)
  [PASS] 实时取景 — 启动成功
  [PASS] 实时取景 — 停止成功

--- WiFi 测试 ---
  [PASS] WiFi AP — 就绪 (Microscope @ 192.168.4.1)

--- SD 卡测试 ---
  [PASS] SD 卡 — 可读取 (X 个文件/目录)
  [PASS] SD 卡 — 写入成功
  [PASS] SD 卡 — 读取验证通过
  [PASS] SD 卡 — 删除测试文件成功

--- 触摸屏测试 ---
  [PASS] lvgl 模块 — 可导入

--- 麦克风测试 ---
  [PASS] 语音模块 — 初始化成功

==================================================
测试完成: X 项
  通过: X
  失败: 0
  跳过: 0
==================================================
  全部硬件测试通过！
```

### 5.2 单项验证（仅测某一模块）

```python
import hardware_test

# 单独测试某个模块
hardware_test.test_motors()
hardware_test.test_camera()
hardware_test.test_sd_card()
```

### 5.3 测试失败的处理

| 测试 | 常见失败原因 | 处理 |
|------|------------|------|
| GPIO | 引脚被占用、焊接短路 | 检查接线、重新上电 |
| 电机 | ULN2003 无 5V 供电、接线顺序错误 | 检查驱动板 5V，核对 IN1-IN4 顺序 |
| LED | MOSFET 接反、LED 烧毁 | 用万用表测 LED 两端电压 |
| 摄像头 | FPC 松动、I2C 地址冲突 | 重新插拔排线、检查座子 |
| WiFi | 天线未接、C6 固件问题 | 检查 IPEX 连接 |
| SD 卡 | 格式非 FAT32、卡槽接触不良 | 重新格式化为 FAT32 |

---

## 6. 功能子系统测试

### 6.1 运动控制系统

```python
from stage_controller import StageController
import config

stage = StageController(
    x_pins=config.X_AXIS_PINS,
    y_pins=config.Y_AXIS_PINS,
    z_pins=config.Z_AXIS_PINS,
    limit_x_pin=config.LIMIT_X_PIN,
    limit_y_pin=config.LIMIT_Y_PIN,
)

# 测试回零
stage.home()                            # 3 轴依次回零
pos = stage.get_position()              # 应返回 {'x': 0, 'y': 0, 'z': 5000}

# 测试相对移动
stage.move_rel(dx=500, dy=500, dz=100)  # 各轴移动指定微米
pos2 = stage.get_position()

# 测试绝对定位
stage.move_to(x=0, y=0, z=5000)         # 回到原点

# 测试速度切换
stage.set_speed("快")
stage.move_rel(dx=200)
stage.set_speed("慢")
stage.move_rel(dx=-200)

# 释放所有电机
stage.release_all()
```

### 6.2 摄像头采集

```python
from camera_controller import CameraController
import config

cam = CameraController(
    width=config.CAM_DEFAULT_WIDTH,
    height=config.CAM_DEFAULT_HEIGHT,
    fmt=config.CAM_DEFAULT_FORMAT,
    fps=config.CAM_FPS,
)
cam.init(
    xclk_pin=config.CAM_PIN_XCLK,
    siod_pin=config.CAM_PIN_SIOD,
    sioc_pin=config.CAM_PIN_SIOC,
    d7_pin=config.CAM_PIN_D7, d6_pin=config.CAM_PIN_D6,
    d5_pin=config.CAM_PIN_D5, d4_pin=config.CAM_PIN_D4,
    d3_pin=config.CAM_PIN_D3, d2_pin=config.CAM_PIN_D2,
    d1_pin=config.CAM_PIN_D1, d0_pin=config.CAM_PIN_D0,
    vsync_pin=config.CAM_PIN_VSYNC,
    href_pin=config.CAM_PIN_HREF,
    pclk_pin=config.CAM_PIN_PCLK,
    pwdn_pin=config.CAM_PIN_PWDN,
)

# 拍照到 SD 卡
img = cam.capture()
if img:
    with open("/sd/test_photo.jpg", "wb") as f:
        f.write(img)
    print(f"照片已保存: {len(img)} 字节")

# 调整分辨率测试
cam.set_resolution(320, 240)
img_small = cam.capture()
cam.set_resolution(800, 600)

# 调整图像参数
cam.set_brightness(1)
cam.set_contrast(-1)
cam.set_saturation(1)

cam.deinit()
```

### 6.3 语音识别

```python
from voice_controller import VoiceController

# 创建控制器（需要 system_manager, stage, led, cam 实例）
vc = VoiceController(sys_mgr, stage, led, cam)
vc.init()

# 查看支持的命令
print(vc.get_commands())

# 开始在循环中处理语音
# 实际使用时由 main.py 主循环调用 vc.process()
# 这里可以手动测试:
vc.process()  # 单次处理，如果有语音输入则执行命令

vc.deinit()
```

### 6.4 自动对焦

```python
from autofocus import Autofocus
from stage_controller import StageController
from camera_controller import CameraController
import config

stage = StageController(...)  # 已初始化
cam = CameraController(...)
cam.init(...)

af = Autofocus(stage, cam)

# 执行一次对焦
best_z, score = af.focus(z_range=500, step=50)
print(f"最佳焦距: Z={best_z}μm, 清晰度={score}")

# 精细对焦
best_z2, score2 = af.focus_around(z_range=200, step=20)
print(f"精细对焦: Z={best_z2}μm, 清晰度={score2}")
```

### 6.5 WiFi API 集成测试

通过桌面端控制面板 `desktop/microscope_control.html` 进行集成测试：

1. 在浏览器中打开 `desktop/microscope_control.html`
2. 输入开发板 IP `192.168.4.1`，点击连接
3. 测试各功能：
   - 方向键移动载物台
   - LED 亮度滑块
   - 拍照按钮
   - 预设点保存/加载
   - 自动对焦
   - MJPEG 实时取景

也可以通过 curl 命令行测试：

```bash
# 状态查询
curl -s http://192.168.4.1/api/status | python3 -m json.tool

# 移动
curl -s -X POST http://192.168.4.1/api/move \
    -H "Content-Type: application/json" \
    -d '{"rel": true, "dx": 100, "dy": 200}' | python3 -m json.tool

# LED 控制
curl -s -X POST http://192.168.4.1/api/led \
    -H "Content-Type: application/json" \
    -d '{"brightness": 70}' | python3 -m json.tool

# 拍照
curl -s -X POST http://192.168.4.1/api/camera/capture

# 列出 SD 卡文件
curl -s http://192.168.4.1/api/files | python3 -m json.tool

# 下载照片（把 test_photo.jpg 替换为实际文件名）
curl -o photo.jpg http://192.168.4.1/api/files/download/test_photo.jpg
```

---

## 7. 校准程序

### 7.1 运动学校准

调整 `config.py` 中的 `LEAD_SCREW_PITCH_MM` 以匹配实际丝杆：

```python
# 在 REPL 中执行
from stage_controller import StageController
import config

stage = StageController(...)
stage.home()

# 移动 1000μm (1mm)，用游标卡尺测量实际位移
stage.move_rel(dx=1000)
actual_mm = float(input("实测 X 轴位移 (mm): "))

# 校正系数 = 当前值 × (目标位移 / 实测位移)
new_pitch = config.LEAD_SCREW_PITCH_MM * (1000 / (actual_mm * 1000))
print(f"校正后导程: {new_pitch:.4f} mm/转")

# 更新 config.py 中的 LEAD_SCREW_PITCH_MM
```

### 7.2 限位开关验证

```python
from machine import Pin
import config

# 手动触发限位开关，观察电平变化
limit_x = Pin(config.LIMIT_X_PIN, Pin.IN, Pin.PULL_UP)
print(f"X 限位 (未触发): {limit_x.value()}")  # 应=1
# 手动按下限位开关
print(f"X 限位 (触发中): {limit_x.value()}")  # 应=0
```

### 7.3 摄像头对焦校准

1. 放置一个高对比度目标（如打印的棋盘格）在载物台上
2. 手动调节 Z 轴找到最清晰的物距
3. 记录 Z 轴位置作为该物镜的工作距离
4. 将此值写入 `config.py` 的 `HOME_POSITION_UM["z"]`

---

## 8. 老化测试

### 8.1 电机循环测试（2 小时）

```python
import time
from stage_controller import StageController
import config

stage = StageController(...)
stage.home()

cycles = 0
try:
    while cycles < 100:
        # X/Y 往复
        stage.move_rel(dx=500, dy=500)
        stage.move_rel(dx=-500, dy=-500)
        # Z 小幅往复
        stage.move_rel(dz=100)
        stage.move_rel(dz=-100)
        cycles += 1
        if cycles % 10 == 0:
            print(f"完成 {cycles}/100 循环")
except Exception as e:
    print(f"老化测试异常 ({cycles} 循环): {e}")
finally:
    stage.release_all()

print(f"电机老化测试: {cycles} 循环完成")
```

### 8.2 连续拍照测试（1 小时）

```python
import time
from camera_controller import CameraController
import config

cam = CameraController(...)
cam.init(...)

count = 0
errors = 0
try:
    while count < 200:
        img = cam.capture()
        if img:
            with open(f"/sd/burnin_{count:04d}.jpg", "wb") as f:
                f.write(img)
            count += 1
        else:
            errors += 1
        if count % 20 == 0:
            print(f"拍照: {count}/200 (错误: {errors})")
        time.sleep(3)
except Exception as e:
    print(f"拍照老化异常: {e}")

print(f"拍照老化测试: {count} 张成功, {errors} 张失败")
cam.deinit()

# 清理测试文件
import os
for f in os.listdir("/sd"):
    if f.startswith("burnin_") and f.endswith(".jpg"):
        os.remove(f"/sd/{f}")
```

### 8.3 系统长时间运行 (8 小时)

```bash
# 启动正常系统，运行 8 小时后检查状态
curl http://192.168.4.1/api/status

# 检查项:
#   - 系统状态应为 IDLE (非 ERROR)
#   - 位置坐标应无异常漂移
#   - LED 状态正常
#   - 内存占用 (通过 sys 模块检查)
```

```python
import gc
gc.collect()
print(f"空闲内存: {gc.mem_free()} 字节")
```

---

## 9. 故障排查流程图

### 9.1 启动失败

```
上电不启动
    │
    ├─ 屏幕完全不亮
    │   ├─ USB 电源 ≥ 5V 2A？ → 否 → 更换电源适配器
    │   └─ 用万用表测 5V/GND → 无电压 → 检查 USB 线和接口
    │
    ├─ 屏幕亮但无画面
    │   ├─ 固件烧录成功？ → 否 → 重新烧录
    │   ├─ lvgl/display 模块导入成功？ → 否 → 固件缺组件，重新编译
    │   └─ 串口有日志输出？ → 否 → 检查波特率 115200
    │
    └─ 屏幕显示但界面卡死
        ├─ 串口日志有异常？ → 是 → 根据错误信息排查对应模块
        └─ 触摸无响应？ → 检查 GT911 I2C 连接
```

### 9.2 电机不转

```
电机指令发出但无转动
    │
    ├─ 电机有振动声？
    │   ├─ 是 → 频率过高/负载过大 → 调为"慢"档重试
    │   └─ 否 → 继续排查
    │
    ├─ ULN2003 指示灯亮？
    │   ├─ 不亮 → 驱动板无 5V → 检查驱动板供电
    │   └─ 亮但不转 → 接线顺序错误 → 核对 IN1-IN4 引脚
    │
    └─ 用万用表测 GPIO 输出 → 无电压跳变 → GPIO 被占用或损坏
```

### 9.3 摄像头黑屏

```
capture() 返回空或黑图
    │
    ├─ 初始化报错？
    │   ├─ I2C 错误 → 检查 SIOD/SIOC 接线
    │   ├─ "sensor not detected" → 检查 FPC 排线接触
    │   └─ "no PSRAM" → 固件未启用 PSRAM，重编译
    │
    ├─ capture() 返回 None
    │   ├─ XCLK 有 10MHz+ 输出？ → 用示波器或逻辑分析仪测 GPIO43
    │   └─ PCLK 有信号？ → 检查 GPIO8 和摄像头排线
    │
    └─ 返回数据但全黑
        └─ 镜头盖未取下？ → 去掉镜头保护盖
```

### 9.4 WiFi 搜不到

```
扫描不到 SSID "Microscope"
    │
    ├─ ESP32-C6 是否已配置？
    │   └─ 检查固件中 esp_wifi_remote 组件是否编译进去
    │
    ├─ IPEX 天线是否已接？
    │   ├─ 未接 → 接好天线
    │   └─ 已接 → 检查天线是否匹配（2.4GHz）
    │
    └─ 串口日志有无 "WiFi AP 就绪"？
        ├─ 无 → network 模块报错 → 查看具体错误
        └─ 有 → 设备距离太远 → 靠近再搜
```

---

## 附录 A：测试检查清单

按此清单逐项打勾，确保完整验证：

### 硬件层
- [ ] GPIO 引脚：6 个关键引脚全部可用
- [ ] X 轴电机：正反向转动正常，无失步
- [ ] Y 轴电机：正反向转动正常，无失步
- [ ] Z 轴电机：正反向转动正常，无失步
- [ ] LED：开关、0-100% 调光、4 档预设正常
- [ ] 摄像头：初始化、拍照、取景正常
- [ ] WiFi：AP 模式、192.168.4.1 可达
- [ ] SD 卡：读写、删除正常
- [ ] 触摸屏：lvgl 导入成功
- [ ] 麦克风：ESP-SR 初始化成功

### 软件层
- [ ] main.py 启动流程完整无异常
- [ ] 触摸 UI 所有按钮响应正常
- [ ] HTTP API 所有端点返回正确 JSON
- [ ] MJPEG 流可在浏览器中播放
- [ ] 语音唤醒词"小天小天"可识别
- [ ] 语音命令执行正确（至少测试 5 条）
- [ ] 自动对焦在 Z 轴找到最清晰位置
- [ ] 自动曝光维持亮度在目标范围
- [ ] 定时拍摄生成正确间隔的照片
- [ ] 设置保存后复位不丢失

### 稳定性
- [ ] 电机 100 次循环无异常
- [ ] 连续拍照 200 张无遗漏
- [ ] 8 小时运行后系统仍在 IDLE 状态
- [ ] 内存无泄漏（gc.mem_free() 不持续下降）

---

## 附录 B：快速诊断命令

```python
# 一键复制到 REPL 执行
import gc, sys, os, machine

# 系统信息
print(f"MicroPython: {sys.version}")
print(f"频率: {machine.freq() / 1e6:.0f} MHz")
print(f"空闲内存: {gc.mem_free():,} 字节")
print(f"根目录: {os.listdir('/')}")

# Flash 信息
try:
    flash = os.statvfs("/")
    total = flash[2] * flash[1]
    free = flash[3] * flash[1]
    print(f"Flash: {free:,} / {total:,} 字节可用")
except:
    print("Flash: 无法获取")

# SD 卡信息
try:
    sd = os.statvfs("/sd")
    total = sd[2] * sd[1]
    free = sd[3] * sd[1]
    print(f"SD 卡: {free:,} / {total:,} 字节可用")
except:
    print("SD 卡: 未挂载")

# WiFi 状态
try:
    import network
    ap = network.WLAN(network.AP_IF)
    print(f"WiFi: {'激活' if ap.active() else '未激活'}")
    if ap.active():
        print(f"  SSID: {ap.config('essid')}")
        print(f"  IP: {ap.ifconfig()[0]}")
except:
    print("WiFi: 不可用")
```
