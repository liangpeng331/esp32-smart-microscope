# ESP32-P4 MicroPython 固件编译指南

从源码编译运行"智能显微镜"所需的定制 MicroPython 固件。

## 为什么需要自己编译

预编译的 MicroPython 固件通常只包含核心 Python 运行时，不包含以下依赖：

| 组件 | 用途 | 来源 |
|------|------|------|
| LVGL 9.x | 触摸屏 UI 渲染 | lvgl.io |
| esp_lcd + ILI9881C | 4" IPS 显示驱动 | ESP-IDF |
| esp_lcd_touch_gt911 | 电容触摸驱动 | ESP-IDF |
| esp_camera | OV2640/OV5640 摄像头 | espressif/esp32-camera |
| ESP-SR | 离线中文语音识别 | espressif/esp-sr |
| esp_wifi_remote | ESP32-C6 WiFi 协处理 | ESP-IDF |
| SDMMC + FAT | microSD 卡读写 | ESP-IDF |

## 环境准备

### 硬件要求

- **编译机**: macOS 14+ / Ubuntu 22.04+ (x86_64 或 aarch64)
- **磁盘**: ≥ 20GB 空闲 (ESP-IDF 工具链约 8GB)
- **内存**: ≥ 8GB RAM
- **USB**: 一根 USB-C 数据线连接 ESP32-P4 开发板

### 安装系统依赖

**macOS**

```bash
# Xcode 命令行工具
xcode-select --install

# Homebrew 包
brew install cmake ninja dfu-util ccache
brew install python@3.12
pip3 install esptool pyserial
```

**Ubuntu**

```bash
sudo apt update
sudo apt install -y cmake ninja-build dfu-util ccache \
    python3 python3-pip python3-venv \
    git wget flex bison gperf \
    libusb-1.0-0 libusb-1.0-0-dev

pip3 install esptool pyserial
```

### 克隆 ESP-IDF

ESP32-P4 需要 ESP-IDF v5.2+ (推荐 v5.3 LTS)：

```bash
mkdir -p ~/esp
cd ~/esp
git clone --depth 1 --branch v5.3.2 \
    https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32p4
```

工具链安装需要下载交叉编译器 (riscv32-esp-elf) 和 SDK 组件，视网络状况约需 10-30 分钟。

验证安装：

```bash
source ~/esp/esp-idf/export.sh
idf.py --version
# 输出: ESP-IDF v5.3.2
```

### 克隆 MicroPython

```bash
cd ~
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init lib/berkeley-db-1xx

# 先构建 mpy-cross（交叉编译器，只需构建一次）
cd mpy-cross
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
```

## 板级定义

本项目提供了 Waveshare ESP32-P4-WIFI6-Touch-LCD-4B 的完整板级定义，位于 `firmware/boards/ESP32_P4_WAVESHARE_4B/`。

### 文件说明

```
firmware/boards/ESP32_P4_WAVESHARE_4B/
├── mpconfigboard.h       # 硬件配置宏（引脚/外设/频率）
├── mpconfigboard.cmake   # CMake 构建配置（组件/分区/优化）
├── sdkconfig.defaults    # ESP-IDF Kconfig 覆盖（PSRAM/摄像头/SD）
└── partitions.csv        # 自定义 16MB Flash 分区表
```

### 链接到 MicroPython 源码树

```bash
ln -sf \
    /path/to/esp32-smart-microscope/firmware/boards/ESP32_P4_WAVESHARE_4B \
    ~/micropython/ports/esp32/boards/ESP32_P4_WAVESHARE_4B
```

或者直接运行一键脚本：

```bash
cd esp32-smart-microscope/firmware
./build.sh setup    # 自动完成所有前置步骤
```

## 一键编译

```bash
cd esp32-smart-microscope/firmware

# 首次使用：初始化所有依赖
./build.sh setup

# 编译固件
./build.sh build

# 编译 + 烧录
./build.sh flash

# 烧录后打开串口监视器
./build.sh monitor
```

`build.sh` 是一个自包含脚本，会自动：
1. 检查系统依赖 (python3, cmake, ninja, git)
2. 如果缺失则克隆 ESP-IDF 和 MicroPython
3. 链接板级定义文件
4. 调用 `make BOARD=...` 编译固件
5. 调用 `esptool` 烧录到开发板

### 脚本环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MICROPY_PORT` | 自动检测 | 串口设备路径 |
| `IDF_TOOLS_PATH` | `~/.espressif` | ESP-IDF 工具链安装目录 |
| `MPY_DIR` | `~/micropython` | MicroPython 源码路径 |
| `IDF_DIR` | `~/esp/esp-idf` | ESP-IDF 路径 |

## 手动编译步骤

如果 `build.sh` 无法满足需求，可以手动执行每一步：

### 1. 激活 ESP-IDF 环境

```bash
source ~/esp/esp-idf/export.sh
```

### 2. 进入 MicroPython ESP32 端口目录

```bash
cd ~/micropython/ports/esp32
```

### 3. 编译

```bash
make BOARD=ESP32_P4_WAVESHARE_4B -j$(nproc)
```

产物路径：`build-ESP32_P4_WAVESHARE_4B/micropython.bin`

### 4. 烧录

```bash
# 擦除
esptool.py --chip esp32p4 --port /dev/cu.usbmodem101 erase_flash

# 写入
make BOARD=ESP32_P4_WAVESHARE_4B PORT=/dev/cu.usbmodem101 deploy
```

## 分区表说明

16MB Flash 按如下布局分配：

```
偏移量      大小       分区          内容
0x000000    (boot)     bootloader    二级引导
0x009000    24KB       nvs           WiFi/系统非易失存储
0x00F000    4KB        phy_init      PHY 初始化
0x010000    6MB        factory       固件本体 (含 LVGL, ESP-SR)
0x610000    2MB        lvgl_assets   LVGL 图片/字体
0x810000    7.9MB      micropython   MicroPython 文件系统 (FAT)
```

## 常见编译问题

### Q: `idf.py` 报 "Unrecognized target: esp32p4"

ESP-IDF 版本过旧。需要 **v5.2 或更高**。检查版本：

```bash
idf.py --version
```

### Q: 编译时 PSRAM 报错

检查 `sdkconfig.defaults` 中 PSRAM 配置是否与实际硬件匹配。Waveshare 4B 使用 Octal PSRAM (8 线)，确认：

```
CONFIG_SPIRAM_MODE_OCT=y
```

### Q: `esp_camera` 组件缺失

DVP 摄像头驱动来自 espressif/esp32-camera 仓库，需要手动添加到 ESP-IDF 组件路径：

```bash
cd ~/esp/esp-idf/components
git clone https://github.com/espressif/esp32-camera.git esp_camera
```

### Q: `esp_sr` 组件缺失

```bash
cd ~/esp/esp-idf/components
git clone https://github.com/espressif/esp-sr.git esp_sr
cd esp_sr
# ESP-SR 模型数据较大，建议浅克隆
git checkout master
```

### Q: LVGL 编译报 "undefined reference to lv_*"

MicroPython 主分支可能未内置 LVGL 绑定。需要确认 `ports/esp32` 是否包含了 LVGL 组件。如果未包含：

1. 检查 `~/micropython/ports/esp32/esp32_common.cmake` 中 `MICROPY_LVGL` 是否为 1
2. 或者在板级 `mpconfigboard.cmake` 中显式添加 LVGL 依赖路径

### Q: 编译完成后 LCD 黑屏

1. 确认 `mpconfigboard.h` 中 `MICROPY_HW_LCD_WIDTH/HEIGHT` 与硬件一致 (720×720)
2. 确认 LCD 接口类型 (MIPI DSI vs RGB) 与板级驱动匹配
3. 用 `esptool.py read_flash_status` 检查 Flash 是否正常

### Q: `esptool` 无法连接开发板

```bash
# macOS — 检查是否被其他程序占用
ls -l /dev/cu.usbmodem*

# 按住 BOOT 键，点按 RESET，进入下载模式后再试
# 或检查 USB 线是否支持数据传输（部分充电线不支持）
```

## 编译产物

成功编译后得到：

| 文件 | 用途 |
|------|------|
| `build-*/micropython.bin` | 完整固件，烧录到 0x0 |
| `build-*/bootloader/bootloader.bin` | 二级引导 |
| `build-*/partition_table/partition-table.bin` | 分区表 |

`make deploy` 会自动按正确偏移量烧录以上三个文件。

## 上传应用代码

固件烧录完成后，还需要上传 Python 代码到 MicroPython 文件系统：

```bash
cd esp32-smart-microscope

# 用 mpremote 批量上传
for f in config.py motor_driver.py stage_controller.py \
    led_controller.py system_manager.py touch_ui.py \
    wifi_server.py camera_controller.py voice_controller.py \
    autofocus.py timelapse.py auto_exposure.py settings.py \
    hardware_test.py main.py; do
    mpremote connect /dev/cu.usbmodem* cp "$f" ":$f"
done

# 软复位
mpremote connect /dev/cu.usbmodem* reset
```

## 下一步

固件就绪后：
1. 按 [DEPLOY.md](DEPLOY.md) 进行硬件接线和部署
2. 运行 `hardware_test.run_all()` 验证全部外设
3. 阅读 [固件开发笔记](docs/adr/) 了解架构决策
