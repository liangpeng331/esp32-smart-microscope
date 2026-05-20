# ESP32-P4 智能显微镜

基于 Waveshare ESP32-P4-WIFI6-Touch-LCD-4B 的 3 轴电动显微镜控制系统。集成本地触摸屏、离线语音识别、WiFi 远程控制、自动对焦、细胞检测等功能。

---

## 目录

- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [硬件清单](#硬件清单)
- [端口接线](#端口接线)
- [机械组装](#机械组装)
- [软件开发环境搭建](#软件开发环境搭建)
- [固件编译](#固件编译)
- [固件烧录](#固件烧录)
- [应用代码上传](#应用代码上传)
- [首次启动与验证](#首次启动与验证)
- [使用指南](#使用指南)
- [调试与故障排除](#调试与故障排除)
- [WiFi 远程控制](#wifi-远程控制)
- [测试](#测试)
- [常见问题 FAQ](#常见问题-faq)

---

## 功能特性

* **3 轴电动云台** — X/Y 载物台 + Z 对焦，28BYJ-48 步进电机半步驱动，行程 ±10mm，精度 0.2μm/步
* **自动回零** — 限位开关校准机械原点，一键复位
* **LED PWM 调光** — 4 档预设（暗/中/亮/最亮）+ 无级滑动调节，1kHz 无闪烁
* **摄像头采集** — OV2640/OV5640 摄像头，JPEG 输出，实时取景，15fps
* **自动对焦** — Laplacian 方差清晰度评价算法，Z 轴扫描自动合焦
* **自动曝光** — 直方图分析 + 目标亮度控制，亮度/对比度/饱和度可调
* **定时拍摄** — 间隔拍摄 / Z 轴景深堆叠 / XY 网格扫描拼接
* **视频录制** — 设备端 MJPEG 帧采集 + 桌面端 MP4 合成
* **WiFi 远程控制** — HTTP REST API（8+ 端点），浏览器控制台，桌面端工具集
* **触摸屏界面** — LVGL 9.x 图形库，720×720 IPS 全彩显示，中文菜单
* **离线语音识别** — ESP-SR 引擎，唤醒词 + 23 条中文语音指令
* **文件管理** — microSD 卡存储，FAT 文件系统，拍照自动编号
* **安全加固** — WiFi 密码可配置、API 令牌认证、输入参数校验
* **图像拼接** — 桌面端偏移/特征点拼接工具
* **景深合成** — 多焦点堆叠合成全清晰图像
* **深度学习细胞检测** — YOLOv8 目标检测 + UNet 语义分割
* **云端同步** — MQTT 遥测 + OSS 文件上传 + Webhook 通知
* **跨平台 APP** — Flutter 手机端控制应用（Android/iOS）
* **CI/CD** — GitHub Actions 自动运行 237 个测试

---

## 项目结构

```
esp32-smart-microscope/
├── main.py                  # 主入口（4 阶段启动流程）
├── config.py                # 全局配置（引脚/电机参数/WiFi/摄像头）
├── motor_driver.py          # 28BYJ-48 + ULN2003 半步驱动
├── stage_controller.py      # 3 轴云台控制 + 限位检测 + 自动回零
├── led_controller.py        # LED PWM 调光控制
├── system_manager.py        # 状态机管理 + 预设点保存/加载
├── touch_ui.py              # LVGL 9.x 触摸屏图形界面
├── wifi_server.py           # HTTP API 服务器（RESTful）
├── camera_controller.py     # 摄像头采集与图像处理
├── voice_controller.py      # 离线中文语音识别（ESP-SR）
├── autofocus.py             # 自动对焦算法（Laplacian 清晰度评价）
├── auto_exposure.py         # 自动曝光控制（直方图分析）
├── timelapse.py             # 定时拍摄 / 景深堆叠 / 网格扫描
├── video_recorder.py        # 视频录制模块（MJPEG → MP4）
├── cell_analyzer.py         # 细胞分析桥接模块
├── cloud_sync.py            # 云端同步（MQTT/OSS/Webhook）
├── security.py              # 安全模块（密码/令牌/输入校验）
├── settings.py              # 设置持久化（SD 卡 JSON 存储）
├── hardware_test.py         # 硬件自检（8 项全外设测试）
├── desktop/                 # 桌面端工具集
│   ├── microscope_control.html  # 浏览器控制台（远程操作界面）
│   ├── stitcher.py              # 图像拼接工具
│   ├── focus_stack.py           # 景深堆叠工具
│   ├── cell_counter.py          # 细胞识别计数引擎
│   ├── cell_detector.py         # YOLOv8/UNet 深度学习检测
│   └── cell_analysis_client.py  # 细胞分析桌面客户端
├── flutter_app/             # Flutter 跨平台手机 APP
│   └── lib/                     # Dart 源码
├── tests/                   # 单元测试（237 个用例）
│   ├── test_motor_driver.py
│   ├── test_stage_controller.py
│   ├── test_autofocus.py
│   ├── test_camera_controller.py
│   ├── test_wifi_server.py
│   ├── test_timelapse.py
│   ├── test_settings.py
│   ├── test_auto_exposure.py
│   ├── test_cell_analyzer.py
│   ├── test_cell_counter.py
│   └── test_system_manager.py
├── firmware/                # 固件编译
│   ├── build.sh                 # 一键编译/烧录脚本
│   └── boards/ESP32_P4_WAVESHARE_4B/
│       ├── mpconfigboard.h      # 硬件配置宏
│       ├── mpconfigboard.cmake  # CMake 构建配置
│       ├── sdkconfig.defaults   # ESP-IDF Kconfig 覆盖
│       └── partitions.csv       # 16MB Flash 分区表
├── docs/                    # 文档
│   └── adr/                     # 架构决策记录
├── .github/workflows/       # CI/CD 自动化
│   └── test.yml
├── BUILD.md                 # 固件编译详细指南
├── DEPLOY.md                # 硬件部署详细指南
├── TESTING.md               # 实机烧录与测试流程
├── CONTEXT.md               # 领域知识文档
└── README.md                # 本文件
```

---

## 硬件清单

### 必需部件

| 序号 | 部件 | 型号/规格 | 数量 | 约参考价 | 购买渠道 |
|------|------|-----------|------|----------|----------|
| 1 | 主控板 | Waveshare ESP32-P4-WIFI6-Touch-LCD-4B | 1 | ¥299 | 微雪电子官方商城 / 淘宝 |
| 2 | 步进电机 | 28BYJ-48 5V DC + ULN2003 驱动板 | 3 | ¥15/套 | 淘宝搜索 "28BYJ-48 ULN2003" |
| 3 | 摄像头模块 | OV2640 DVP 接口（兼容 OV5640） | 1 | ¥25 | 淘宝搜索 "OV2640 DVP 摄像头模块" |
| 4 | 限位开关 | 微动开关（常开型 NO），带滚轮杠杆 | 2 | ¥1/个 | 淘宝搜索 "微动开关 滚轮 常开" |
| 5 | LED 照明 | 高亮白光 LED 环形灯板 + IRF520 MOS 管驱动模块 | 1 | ¥8 | 淘宝搜索 "IRF520 MOSFET 驱动模块" |
| 6 | MicroSD 卡 | 8-32GB Class 10, FAT32 格式 | 1 | ¥25 | 京东/淘宝 |
| 7 | 电源适配器 | 5V 3A DC, 5.5×2.1mm 插头 | 1 | ¥15 | 淘宝搜索 "5V 3A 电源适配器" |
| 8 | USB-C 数据线 | 支持数据传输（非仅充电线） | 1 | ¥10 | 手机配件店 |
| 9 | 杜邦线 | 公对母 20cm，40 根装 | 2 | ¥5/包 | 淘宝搜索 "杜邦线 公对母 20cm" |
| 10 | 排针排母 | 2.54mm 间距，直插式 | 若干 | ¥2 | 淘宝搜索 "排针 2.54mm" |

### 可选部件

| 部件 | 型号 | 用途 |
|------|------|------|
| I2S MEMS 麦克风 | INMP441 | 离线语音识别输入 |
| WiFi 天线 | IPEX 接口 | 增强 WiFi 信号（主板附赠） |
| 物镜 | 4× / 10× / 40× 显微镜物镜 | 光学放大 |

### 工具需求

* 螺丝刀套装（十字 + 一字）
* 万用表（用于接线验证）
* 热熔胶枪或双面胶（固定部件）
* 电脑（macOS 14+ / Windows 10+ / Ubuntu 22.04+）

---

## 端口接线

> **⚠️ 接线前请断开电源！用万用表确认所有连线正确后再通电。**

### 接线总览图

```
                         ┌──────────────────────────────────────┐
                         │        ESP32-P4-WIFI6-Touch-LCD-4B    │
                         │                                      │
  ┌──────┐  FPC排线       │  ┌──DVP-Camera────┐                 │
  │OV2640├───────────────┤  └───────────────┘                 │
  │摄像头 │               │                                      │
  └──────┘               │  GPIO4─5─6─7   ──→ ULN2003 #1 X轴   │
                         │  GPIO8─9─10─11 ──→ ULN2003 #2 Y轴   │
  ┌──────────────────┐   │  GPIO12─13─14─15 ─→ ULN2003 #3 Z轴  │
  │ ULN2003 ×3       │   │                                      │
  │ + 28BYJ-48 ×3    ├───┤  GPIO2  ──→ 限位开关 X (NO→GND)      │
  │ X/Y/Z 轴电机     │   │  GPIO3  ──→ 限位开关 Y (NO→GND)      │
  └──────────────────┘   │  GPIO21 ──→ LED MOS管 SIG            │
                         │                                      │
  ┌──────────────────┐   │  ┌──MicroSD Slot──┐                 │
  │ LED环形灯 +      │   │  │  (背面插入)     │                 │
  │ MOS管驱动模块    ├───┤  └───────────────┘                 │
  └──────────────────┘   │                                      │
                         │  USB-C ──→ 电脑 (烧录/串口/供电)      │
  ┌──────────────────┐   │  5V GND ──→ 外接 5V 3A 电源          │
  │ 外接 5V 3A 电源  ├───┤                                      │
  └──────────────────┘   └──────────────────────────────────────┘
```

### 1. 步进电机接线（ULN2003 驱动板）

每个 28BYJ-48 电机配套一个 ULN2003 驱动板，驱动板有 4 个输入脚 (IN1-IN4)。

**X 轴电机（载物台左右移动）**

| ULN2003 引脚 | ESP32-P4 GPIO | 杜邦线颜色（建议） |
|-------------|---------------|-------------------|
| IN1 | GPIO4 | 橙色 |
| IN2 | GPIO5 | 黄色 |
| IN3 | GPIO6 | 绿色 |
| IN4 | GPIO7 | 蓝色 |
| VCC (+) | 5V | 红色 |
| GND (-) | GND | 黑色 |

**Y 轴电机（载物台前后移动）**

| ULN2003 引脚 | ESP32-P4 GPIO | 杜邦线颜色（建议） |
|-------------|---------------|-------------------|
| IN1 | GPIO8 | 橙色 |
| IN2 | GPIO9 | 黄色 |
| IN3 | GPIO10 | 绿色 |
| IN4 | GPIO11 | 蓝色 |
| VCC (+) | 5V | 红色 |
| GND (-) | GND | 黑色 |

**Z 轴电机（物镜上下对焦）**

| ULN2003 引脚 | ESP32-P4 GPIO | 杜邦线颜色（建议） |
|-------------|---------------|-------------------|
| IN1 | GPIO12 | 橙色 |
| IN2 | GPIO13 | 黄色 |
| IN3 | GPIO14 | 绿色 |
| IN4 | GPIO15 | 蓝色 |
| VCC (+) | 5V | 红色 |
| GND (-) | GND | 黑色 |

> **注意**：3 个 ULN2003 驱动板的 VCC 和 GND 都并联到 5V 电源。GPIO4-15 只需接信号线（ESP32-P4 的 GPIO 是 3.3V 电平，ULN2003 兼容 3.3V-5V 输入）。

### 2. 限位开关接线

使用常开型（NO）微动开关，触发时 GPIO 读低电平。

| 限位开关 | ESP32-P4 引脚 | 开关触点 | 说明 |
|----------|---------------|---------|------|
| X 轴限位 | GPIO2 | COM ↔ GPIO2, NO ↔ GND | 载物台左端极限位置 |
| Y 轴限位 | GPIO3 | COM ↔ GPIO3, NO ↔ GND | 载物台后端极限位置 |

> 开关内部：COM（公共端）接 GPIO，NO（常开端）接 GND。未触发时 GPIO 悬空（内部上拉为高），触发时 COM 与 NO 导通，GPIO 读低。

### 3. LED 照明接线

| IRF520 MOS 模块引脚 | 连接目标 |
|--------------------|----------|
| SIG（信号） | ESP32-P4 GPIO21 |
| VCC（电源+） | 5V |
| GND（电源-） | GND |
| V+（输出+） | LED 灯板正极 |
| V-（输出-） | LED 灯板负极 |

> MOS 管模块通过 PWM 控制 LED 亮度。GPIO21 输出 PWM 信号到 SIG 脚，占空比 0-100% 对应亮度 0-100%。

### 4. 摄像头接线

OV2640/OV5640 通过 24P FPC 软排线直接插入主板上的 DVP 摄像头插座。**无需单独飞线**。

DVP 接口的 GPIO 映射（系统预设，已在 config.py 中配置）：

| DVP 信号 | ESP32-P4 GPIO |
|----------|---------------|
| XCLK（主时钟） | GPIO43 |
| PCLK（像素时钟） | GPIO8 |
| VSYNC（帧同步） | GPIO47 |
| HREF（行同步） | GPIO38 |
| D0 | GPIO14 |
| D1 | GPIO13 |
| D2 | GPIO12 |
| D3 | GPIO11 |
| D4 | GPIO42 |
| D5 | GPIO41 |
| D6 | GPIO40 |
| D7 | GPIO39 |
| SIOD（I2C SDA） | GPIO44 |
| SIOC（I2C SCL） | GPIO45 |

> **注意**：摄像头 I2C（SIOD/SIOC）和触摸屏 I2C 共用 I2C0 总线，地址不冲突（摄像头 0x30，触摸 0x5D）。

### 5. 电源接线

```
5V 3A 适配器 ──→ 主板 5V/GND 引脚（或通过 USB-C 供电）
                └──→ 3 个 ULN2003 驱动板 VCC/GND（并联）
                └──→ IRF520 MOS 模块 VCC/GND
```

建议使用面包板或接线端子分配 5V 和 GND 给多个模块。

---

## 机械组装

### 组装步骤

#### 第 1 步：固定主板

将 ESP32-P4 主板用尼龙柱固定在底座上（4 角 M3 安装孔）。显示屏面朝上，DVP 摄像头接口朝前。

#### 第 2 步：安装 X/Y 轴

```
底座
├── Y 轴滑台（前后移动）
│   └── Y 轴电机 — 28BYJ-48 + 丝杆/同步带
└── X 轴滑台（左右移动，装在 Y 轴滑台上方）
    └── X 轴电机 — 28BYJ-48 + 丝杆/同步带
        └── 载物台（放玻片）
```

1. 将 Y 轴滑台固定在底座上
2. 将 X 轴滑台固定在 Y 轴滑台的移动平台上
3. 载物台固定在 X 轴滑台顶部

#### 第 3 步：安装 Z 轴（对焦）

```
立柱
└── Z 轴滑台（上下移动）
    └── 摄像头 + 物镜支架
        └── Z 轴电机 — 28BYJ-48
```

1. 将立柱固定在底座后侧
2. 将 Z 轴滑台装在立柱上
3. 将摄像头/物镜支架装在 Z 轴滑台上

#### 第 4 步：安装摄像头

1. 将 OV2640 摄像头模块装入支架，镜头朝下对准载物台
2. 用 FPC 排线将摄像头 DVP 接口连接到主板 DVP 插座
3. 确保排线完全插入，两端锁扣锁紧

#### 第 5 步：安装限位开关

1. **X 轴限位**：装在载物台左端极限位置，当载物台运行到最左端时触碰开关
2. **Y 轴限位**：装在载物台后端极限位置，当载物台运行到最后端时触碰开关

#### 第 6 步：安装 LED 环形灯

1. 将 LED 环形灯板固定在物镜周围（环形向下照射）
2. 将 MOS 管模块固定在底座侧面

#### 第 7 步：接线

按照[端口接线](#端口接线)章节完成所有电气连接。

---

## 软件开发环境搭建

### 支持的操作系统

* **macOS 14+**（Apple Silicon / Intel）
* **Ubuntu 22.04+**（x86_64 或 aarch64）
* **Windows 10/11** (WSL2 Ubuntu 推荐)

### 安装系统依赖

**macOS**

```bash
# 1. 安装 Xcode 命令行工具
xcode-select --install

# 2. 安装 Homebrew 包
brew install cmake ninja dfu-util ccache python@3.12
pip3 install esptool pyserial mpremote

# 3. 验证
cmake --version    # ≥ 3.16
python3 --version  # ≥ 3.10
```

**Ubuntu**

```bash
# 1. 系统包
sudo apt update
sudo apt install -y cmake ninja-build dfu-util ccache \
    python3 python3-pip python3-venv \
    git wget flex bison gperf \
    libusb-1.0-0 libusb-1.0-0-dev

# 2. Python 包
pip3 install esptool pyserial mpremote

# 3. 串口权限
sudo usermod -a -G dialout $USER
# 重新登录生效
```

### 安装 ESP-IDF

ESP32-P4 需要 ESP-IDF v5.2+，推荐 v5.3.2 LTS：

```bash
mkdir -p ~/esp
cd ~/esp
git clone --depth 1 --branch v5.3.2 https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32p4
```

> 这一步需下载 RISC-V 交叉编译器（约 1.5GB），视网络状况约需 10-30 分钟。

验证安装：

```bash
source ~/esp/esp-idf/export.sh
idf.py --version
# 输出: ESP-IDF v5.3.2
```

### 克隆 MicroPython 并编译 mpy-cross

```bash
cd ~
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init lib/berkeley-db-1xx

# 编译 mpy-cross（MicroPython 交叉编译器，只需编译一次）
cd mpy-cross
make -j$(sysctl -n hw.ncpu 2>/dev/null || nproc)
```

### 克隆本项目和链接板级定义

```bash
cd ~
git clone https://github.com/liangpeng331/esp32-smart-microscope.git
cd esp32-smart-microscope

# 将板级定义链接到 MicroPython 源码树
ln -sf \
    ~/esp32-smart-microscope/firmware/boards/ESP32_P4_WAVESHARE_4B \
    ~/micropython/ports/esp32/boards/ESP32_P4_WAVESHARE_4B
```

### 一键环境搭建（可选）

或者直接使用项目提供的自动化脚本：

```bash
cd ~/esp32-smart-microscope/firmware
./build.sh setup
```

此脚本会自动检查依赖、克隆 ESP-IDF、克隆 MicroPython、编译 mpy-cross 并链接板级定义。

---

## 固件编译

### 一键编译

```bash
cd ~/esp32-smart-microscope/firmware

# 编译固件
./build.sh build
```

### 手动编译（逐步操作）

适合需要了解每一步细节的开发者。

```bash
# 1. 激活 ESP-IDF 工具链
source ~/esp/esp-idf/export.sh

# 2. 进入 MicroPython ESP32 端口
cd ~/micropython/ports/esp32

# 3. 确保板级定义已链接
ls boards/ESP32_P4_WAVESHARE_4B/
# 应该看到: mpconfigboard.h  mpconfigboard.cmake  sdkconfig.defaults  partitions.csv

# 4. 创建分区表链接（ESP-IDF 要求在项目根目录）
ln -sf boards/ESP32_P4_WAVESHARE_4B/partitions.csv partitions.csv

# 5. 编译
make BOARD=ESP32_P4_WAVESHARE_4B -j$(sysctl -n hw.ncpu 2>/dev/null || nproc)
```

### 编译产物

成功后生成以下文件：

| 文件 | 路径 | 用途 |
|------|------|------|
| **micropython.bin** | `build-ESP32_P4_WAVESHARE_4B/micropython.bin` | 主固件（烧录地址 0x10000） |
| bootloader.bin | `build-ESP32_P4_WAVESHARE_4B/bootloader/bootloader.bin` | 二级引导（烧录地址 0x2000） |
| partition-table.bin | `build-ESP32_P4_WAVESHARE_4B/partition_table/partition-table.bin` | 分区表（烧录地址 0x8000） |

### 分区表说明

```
Flash 地址    大小      分区名称       内容
──────────────────────────────────────────────
0x000000      (boot)    bootloader    二级引导程序
0x009000      24KB      nvs           系统配置存储
0x00F000      4KB       phy_init      PHY 初始化
0x010000      6MB       factory       固件本体（含 LVGL、ESP-SR等）
0x610000      2MB       lvgl_assets   LVGL 图片/字体资源（SPIFFS）
0x810000      7.9MB     micropython   MicroPython 文件系统（FAT）
```

> 可在 `firmware/boards/ESP32_P4_WAVESHARE_4B/partitions.csv` 中调整分区大小。

### 编译常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `Unrecognized target: esp32p4` | ESP-IDF 版本过旧 | 需要 v5.2+，检查 `idf.py --version` |
| `CONFIG_PARTITION_TABLE_CUSTOM` 不生效 | sdkconfig 缓存 | 删除 `sdkconfig` 后重新 `reconfigure` |
| `partition too small for binary` | 固件超过 1MB | 使用自定义分区表（已在 sdkconfig.defaults 中配置） |
| `esp_camera` 组件缺失 | 未配置组件 | 确认 `sdkconfig.defaults` 中有 `CONFIG_ESP_CAMERA_ENABLE=y` |
| `MP_REGISTER_MODULE` 未定义 | QSTR 缓存过期 | 执行 `idf.py fullclean` 后重新编译 |
| GitHub 连接失败 | 网络问题 | 重试几次，或配置代理/镜像 |

---

## 固件烧录

### 连接开发板

1. 用 USB-C 数据线连接 ESP32-P4 主板到电脑
2. **进入下载模式**：按住 **BOOT** 键不放 → 点按 **RESET** 键 → 松开 **BOOT** 键
3. 确认串口识别：

```bash
# macOS
ls -l /dev/cu.usbmodem*

# Ubuntu
ls -l /dev/ttyUSB*
```

### 一键烧录

```bash
cd ~/esp32-smart-microscope/firmware

# 编译 + 烧录（自动检测串口）
./build.sh flash

# 如需手动指定串口：
MICROPY_PORT=/dev/cu.usbmodem101 ./build.sh flash
```

### 手动烧录（esptool 逐步操作）

```bash
# 1. 激活 ESP-IDF 环境
source ~/esp/esp-idf/export.sh

cd ~/micropython/ports/esp32

# 2. 擦除整个 Flash
esptool.py --chip esp32p4 --port /dev/cu.usbmodem* erase_flash

# 3. 使用 make deploy（推荐，自动烧录 bootloader + 分区表 + 固件）
make BOARD=ESP32_P4_WAVESHARE_4B PORT=/dev/cu.usbmodem* deploy

# 4. 或手动分别烧录
esptool.py --chip esp32p4 --port /dev/cu.usbmodem* \
    write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m \
    0x2000 build-ESP32_P4_WAVESHARE_4B/bootloader/bootloader.bin \
    0x8000 build-ESP32_P4_WAVESHARE_4B/partition_table/partition-table.bin \
    0x10000 build-ESP32_P4_WAVESHARE_4B/micropython.bin
```

> 烧录完成后按 RESET 键或重新上电。

---

## 应用代码上传

固件烧录完成后，还需要上传 Python 应用代码到 MicroPython 文件系统。

### 使用 mpremote

```bash
# 安装 mpremote（如果尚未安装）
pip3 install mpremote

cd ~/esp32-smart-microscope

# 批量上传所有 Python 文件
for f in config.py motor_driver.py stage_controller.py \
    led_controller.py system_manager.py touch_ui.py \
    wifi_server.py camera_controller.py voice_controller.py \
    autofocus.py timelapse.py auto_exposure.py settings.py \
    cell_analyzer.py video_recorder.py cloud_sync.py security.py \
    hardware_test.py main.py; do
    echo "上传 $f ..."
    mpremote connect /dev/cu.usbmodem* cp "$f" ":$f"
done

# 软复位启动
mpremote connect /dev/cu.usbmodem* reset
```

### 验证文件上传

```bash
mpremote connect /dev/cu.usbmodem* ls
# 应列出所有 Python 文件
```

---

## 首次启动与验证

### 启动流程

1. 确认 microSD 卡已插入（FAT32 格式）
2. 接通 5V 电源（或通过 USB-C 供电）
3. 等待约 3-5 秒，屏幕亮起
4. 屏幕显示 "ESP32-P4 智能显微镜" 主界面
5. 系统按顺序自动初始化：

```
显示初始化 → 电机复位 → 摄像头检测 → WiFi AP 启动 → 界面渲染
```

### 串口监视器（查看启动日志）

```bash
# 方式 1：screen
screen /dev/cu.usbmodem* 115200

# 方式 2：mpremote
mpremote connect /dev/cu.usbmodem*

# 方式 3：项目脚本
cd ~/esp32-smart-microscope/firmware
./build.sh monitor
```

### 运行硬件自检

在 MicroPython REPL 中执行：

```python
import hardware_test
hardware_test.run_all()
```

自检项目：
1. ✅ GPIO 引脚可用性（6 个关键引脚）
2. ✅ 3 轴步进电机（双向转动验证）
3. ✅ LED PWM 调光（开关/亮度/预设）
4. ✅ 摄像头采集（初始化/拍照/取景）
5. ✅ WiFi AP 模式（SSID 广播）
6. ✅ SD 卡读写（列出/写入/读取/删除）
7. ✅ 触摸屏（lvgl 模块导入）
8. ✅ I2S 麦克风（ESP-SR 初始化，可选）

---

## 使用指南

### 触摸屏操作

| 界面区域 | 操作 | 功能 |
|----------|------|------|
| 实时预览 | 中央区域 | 摄像头实时画面 |
| X/Y/Z 方向键 | 点击 | 控制载物台移动 |
| 速度切换 | 点击切换 | 快/中/慢三档 |
| LED 滑块 | 滑动 | 调节照明亮度（0-100%） |
| 拍照 | 点击 📷 | 拍摄当前画面并存 SD 卡 |
| 自动对焦 | 点击 AF | Z 轴扫描自动对焦 |
| 回零 | 点击 🏠 | 3 轴自动寻找限位开关复位 |
| 预设位 | 长按 1-6 | 保存当前位置；短按则移动到已保存位置 |
| 定时拍摄 | 菜单进入 | 间隔/堆叠/扫描模式 |

### 语音控制

支持唤醒词 + 23 条中文指令：

**唤醒词**：`"你好显微镜"`

| 类别 | 语音指令 |
|------|----------|
| 移动 | "向左移"、"向右移"、"向前移"、"向后移"、"向上对焦"、"向下对焦" |
| 速度 | "快速"、"中速"、"慢速" |
| 拍照 | "拍照"、"开始录像"、"停止录像" |
| 对焦 | "自动对焦" |
| 照明 | "开灯"、"关灯"、"亮一点"、"暗一点" |
| 复位 | "回到原点" |
| 预设 | "保存位置"、"位置一"~"位置六" |

---

## 调试与故障排除

### 串口调试

启动日志通过串口 115200 bps 输出，包含每个模块的初始化状态和错误信息。

```bash
screen /dev/cu.usbmodem* 115200
# 按 Ctrl+A 然后 K 退出
```

### MicroPython REPL

通过 REPL 可交互式调试：

```python
# 查看系统信息
import machine
machine.freq()         # CPU 频率
machine.reset_cause()  # 复位原因

# 查看 Flash 空间
import os
os.statvfs('/')

# 测试单个模块
import motor_driver
m = motor_driver.MotorDriver(4,5,6,7)  # X 轴
m.step(100)  # 正转 100 步

# 查看错误日志
import system_manager
system_manager.get_log()
```

### 常见故障排除

| 现象 | 可能原因 | 解决步骤 |
|------|----------|----------|
| 屏幕不亮 | ① 电源不足 ② 排线松动 | ① 换 5V 2A 以上电源 ② 检查 LCD 排线 |
| 电机不转 | ① ULN2003 未供电 ② 信号线接错 | ① 万用表量驱动板 5V ② 对照接线表检查 |
| 电机振动但不转 | ① 速度太快 ② 缺相 | ① 切换为"慢"速 ② 检查 4 根信号线 |
| 电机方向反了 | 接线顺序颠倒 | 交换 IN1-IN4 连接顺序 |
| WiFi 搜不到 | ① 天线未接 ② 信道冲突 | ① 接上 IPEX 天线 ② 靠近开发板搜索 |
| 摄像头黑屏 | ① FPC 排线松 ② 供电不足 | ① 重新插拔锁紧 ② 检查 5V 供电 |
| 摄像头画面花屏 | 数据线接触不良 | 检查 D0-D7 引脚焊接 |
| 拍照不保存 | SD 卡未插入 / 格式不对 | 格式化为 FAT32 |
| 自动对焦失败 | ① Z 轴行程不够 ② 画面太暗 | ① 增大 Z 轴行程 ② 增加 LED 亮度 |
| 限位开关不触发 | ① 接线反了 ② 开关坏了 | ① 检查 NO/NC 类型 ② 万用表通断档测试 |
| 烧录失败 | ① 未进入下载模式 ② 串口占用 | ① 按住 BOOT + 点按 RESET ② 关闭其他终端 |
| 上传代码报错 | 串口权限不足 | `sudo chmod 666 /dev/cu.usbmodem*` |
| REPL 无响应 | 程序死循环 | 按 Ctrl+C 中断 |

### LED 调试指示灯

上电后观察主板的 LED：

* **电源灯（红色）**：常亮表示供电正常
* **状态灯**：快速闪烁 = 启动中，慢闪 = 正常运行
* **WiFi 灯**：常亮 = AP 已启动

### 无硬件测试模式

可以在电脑上运行单元测试验证逻辑正确性（无需开发板）：

```bash
cd ~/esp32-smart-microscope
python3 -m unittest discover -s tests -v
```

全部 237 个测试在 CPython 上可以通过。

---

## WiFi 远程控制

### 连接 WiFi

* **SSID**：`Microscope`
* **密码**：`12345678`
* **IP**：`192.168.4.1`

> 首次启动后约 5 秒 WiFi 就绪。可以在 `config.py` 中修改 SSID 和密码，或在 SD 卡创建 `/sd/security.json` 自定义。

### 浏览器控制台

1. 连接 `Microscope` WiFi
2. 打开浏览器访问 `http://192.168.4.1`
3. 或打开本地文件 `desktop/microscope_control.html`

### HTTP API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/status` | 获取系统状态（位置/速度/LED/摄像头） |
| POST | `/api/move` | 移动指定轴 `{"axis":"x","direction":1,"steps":100}` |
| POST | `/api/stop` | 急停全部电机 |
| POST | `/api/home` | 执行回零流程 |
| POST | `/api/led` | 设置亮度 `{"brightness":80}` |
| POST | `/api/capture` | 拍照并返回 JPEG 数据 |
| GET | `/api/live` | MJPEG 实时视频流 |
| POST | `/api/preset/save` | 保存预设位 `{"slot":1}` |
| POST | `/api/preset/go` | 移动到预设位 `{"slot":1}` |
| GET | `/api/files` | 列出 SD 卡照片文件 |
| POST | `/api/autofocus` | 触发自动对焦 |
| POST | `/api/timelapse` | 启动定时拍摄 `{"interval":5,"count":10}` |

### 桌面端工具

```bash
cd ~/esp32-smart-microscope/desktop

# 图像拼接
python3 stitcher.py --input /path/to/images/ --output stitched.jpg

# 景深堆叠
python3 focus_stack.py --input /path/to/stack/ --output focus.jpg

# 细胞计数
python3 cell_counter.py --input sample.jpg --output result.jpg
```

---

## 测试

### 单元测试（电脑端）

```bash
cd ~/esp32-smart-microscope
python3 -m unittest discover -s tests -v
# 237 个测试用例
```

### 硬件测试（开发板端）

```python
import hardware_test
hardware_test.run_all()
```

### CI/CD

推送代码到 GitHub 后，GitHub Actions 自动运行全部测试：
`.github/workflows/test.yml`

---

## 常见问题 FAQ

**Q: 可以用别的 ESP32 芯片吗？**
A: 不行。ESP32-P4 是唯一支持 DVP 摄像头 + MIPI DSI 显示屏的型号，本项目专为 ESP32-P4 设计。

**Q: 可以用 SPI 摄像头代替 DVP 吗？**
A: 理论上可以，但需要修改 `camera_controller.py` 中摄像头初始化代码和 DVP 引脚配置。

**Q: 编译时提示 `micropython.bin binary size ... bytes. Smallest app partition is ...`？**
A: 这是正常的编译输出，表示分区检查通过。只要没有 "too small" 错误就是成功的。

**Q: 电机精度能到多少？**
A: 28BYJ-48 半步模式每转 4096 步，配 0.8mm 导程丝杆，理论精度约 0.195μm/步。实际精度受机械回差影响约 5-10μm。

**Q: 摄像头最大分辨率多少？**
A: OV2640 最大 1600×1200 (UXGA)，推荐使用 800×600 兼顾帧率和清晰度。

**Q: 能同时接多个摄像头吗？**
A: 不能。ESP32-P4 只有一个 DVP 接口。

**Q: 语音识别需要联网吗？**
A: 不需要。ESP-SR 是离线引擎，全部在本地运行。

**Q: SD 卡最大支持多大？**
A: FAT32 理论上限 2TB，实测 32GB 稳定使用。推荐 8-16GB Class 10。

**Q: 电脑用 Windows 可以吗？**
A: 烧录和串口工具在 Windows 下也支持。但编译固件建议使用 WSL2 Ubuntu。

---

## 许可证

本项目采用 MIT 许可证。依赖的第三方组件（ESP-IDF、MicroPython、LVGL、ESP-SR 等）各自保留其原始许可证。

---

## 相关链接

* 项目仓库：https://github.com/liangpeng331/esp32-smart-microscope
* Waveshare 产品页：https://www.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-4B
* MicroPython 官方：https://micropython.org/
* ESP-IDF 文档：https://docs.espressif.com/projects/esp-idf/
* LVGL 文档：https://docs.lvgl.io/
