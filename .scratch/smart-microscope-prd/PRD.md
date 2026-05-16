# ESP32-P4 智能显微镜 PRD

## Problem Statement

传统显微镜操作依赖手动旋钮调节载物台和焦距，效率低、重复性差、无法记录位置。用户需要一台电动化、可触控操作的智能显微镜，支持 3 轴电动控制、LED 调光，并具备直观的图形界面。

## Solution

基于 ESP32-P4 的智能显微镜控制系统：3 轴电动云台（X/Y 载物台 + Z 物镜对焦）、可调光 LED 照明、720×720 IPS 触摸屏图形界面。参考 OpenFlexure 的开源机械设计和运动学模型，成本控制在千元以内，全部代码和接线文档开源。

## User Stories

### 载物台 X/Y 轴控制
1. As a 用户, I want to 控制载物台沿 X 轴左右移动, so that 我可以水平定位样本。
2. As a 用户, I want to 控制载物台沿 Y 轴前后移动, so that 我可以垂直定位样本。
3. As a 用户, I want to 同时控制 X 和 Y 轴斜向移动, so that 我可以快速将目标区域移到视野中心。
4. As a 用户, I want to 看到 X 轴和 Y 轴的实时位置（微米）, so that 我知道当前视野在样本上的位置。
5. As a 用户, I want to 设置 X/Y 轴的移动速度（快/中/慢）, so that 我可以根据放大倍数选择合适的移动速度。
6. As a 用户, I want to 一键让 X/Y 轴回到原点, so that 我可以快速复位载物台。

### 物镜 Z 轴控制
7. As a 用户, I want to 控制 Z 轴上下移动进行对焦, so that 我可以获得清晰的图像。
8. As a 用户, I want to Z 轴以极小的步进（微米级）移动, so that 我可以精确对焦。
9. As a 用户, I want to 看到 Z 轴的实时位置（微米）, so that 我知道当前对焦位置。
10. As a 用户, I want to 设置 Z 轴的移动速度, so that 我可以快速粗调或慢速精调。

### LED 照明控制
11. As a 用户, I want to 调节 LED 亮度, so that 我可以在不同放大倍数下获得合适的照明。
12. As a 用户, I want to 一键开关 LED, so that 我可以快速开关照明。
13. As a 用户, I want to 设置 LED 亮度为预设档位（暗/中/亮/最亮）, so that 我可以快速切换常用亮度。

### 位置记忆与自动化
14. As a 用户, I want to 保存当前位置为预设点, so that 我可以快速回到感兴趣的区域。
15. As a 用户, I want to 一键移动到已保存的预设点, so that 我可以快速跳转到之前标记的位置。
16. As a 用户, I want to 看到所有已保存的预设点列表, so that 我可以管理和选择预设点。

### 系统功能
17. As a 用户, I want to 在 4 英寸触摸屏上进行所有操作, so that 我不需要外接电脑或物理按键。
18. As a 用户, I want to 屏幕显示清晰直观的中文界面, so that 我可以轻松上手使用。
19. As a 用户, I want to 通过 WiFi 连接用手机或电脑远程控制显微镜, so that 我可以远程观察样本。
20. As a 用户, I want to 系统启动时自动初始化所有电机到原点, so that 位置读数准确可靠。

## Implementation Decisions

### 硬件选型
- **主控板**: Waveshare ESP32-P4-WIFI6-Touch-LCD-4B（ESP32-P4 RISC-V 双核 @400MHz + 32MB PSRAM + 32MB Flash + 4 英寸 720×720 IPS 电容触摸屏 + GT911 触控 IC）
- **无线协处理**: 板载 ESP32-C6（WiFi 6 + BLE 5）
- **电机**: 3 × 28BYJ-48 5V 步进电机（X 轴、Y 轴、Z 轴各一）
- **电机驱动**: 3 × ULN2003 驱动板
- **LED**: 高亮白光 LED + 限流电阻 + MOSFET 驱动
- **电源**: 5V 3A 外接电源（同时供电主板和电机）

### GPIO 分配

| 功能 | GPIO | 说明 |
|------|------|------|
| X 轴 IN1 | GPIO4 | ULN2003 输入 1 |
| X 轴 IN2 | GPIO5 | ULN2003 输入 2 |
| X 轴 IN3 | GPIO6 | ULN2003 输入 3 |
| X 轴 IN4 | GPIO7 | ULN2003 输入 4 |
| Y 轴 IN1 | GPIO8 | ULN2003 输入 1 |
| Y 轴 IN2 | GPIO9 | ULN2003 输入 2 |
| Y 轴 IN3 | GPIO10 | ULN2003 输入 3 |
| Y 轴 IN4 | GPIO11 | ULN2003 输入 4 |
| Z 轴 IN1 | GPIO12 | ULN2003 输入 1 |
| Z 轴 IN2 | GPIO13 | ULN2003 输入 2 |
| Z 轴 IN3 | GPIO14 | ULN2003 输入 3 |
| Z 轴 IN4 | GPIO15 | ULN2003 输入 4 |
| LED PWM | GPIO21 | LED 亮度控制 |
| X 限位开关 | GPIO2 | 载物台 X 轴原点 |
| Y 限位开关 | GPIO3 | 载物台 Y 轴原点 |

### 软件架构

```
main.py                  — 入口，初始化各模块，启动 UI
config.py                — 全局配置（电机参数、LED 默认值、UI 设置）
motor_driver.py          — 28BYJ-48 + ULN2003 底层步进驱动
stage_controller.py      — 3 轴运动控制 + OpenFlexure 运动学
led_controller.py        — LED PWM 调光控制
touch_ui.py              — LVGL 图形界面（主控面板、位置显示、设置）
wifi_server.py           — WiFi Web 远程控制服务
system_manager.py        — 状态机、事件调度、预设点管理
```

### 软件关键决策
- **固件语言**: MicroPython（开发速度快，社区生态丰富，电机驱动库成熟）
- **UI 框架**: LVGL 9.x（ESP32-P4 官方支持，Waveshare 提供驱动）
- **步进模式**: 半步（Half-Step），4096 步/转，兼顾精度和扭矩
- **位置单位**: 微米（μm），通过校准系数将步数转换为实际位移
- **运动学模型**: 参考 OpenFlexure 的线性运动学（28BYJ-48 通过丝杆/柔性铰链驱动载物台）
- **Web 远程控制**: 轻量 HTTP API，不依赖 WebSocket，降低复杂度
- **预设点存储**: JSON 文件存储在 microSD 卡上

### OpenFlexure 运动学参考
- 28BYJ-48 步进角 = 5.625°/64，减速比 1/64
- 半步模式：4096 步/转
- 丝杆导程：约 0.8mm/转（取决于具体机械结构）
- 理论分辨率：0.8mm / 4096 ≈ 0.2μm/步
- 实际有效分辨率受限于柔性铰链间隙和摩擦，约 1-5μm

## Testing Decisions

### 测试原则
- 只测试外部行为，不测试实现细节
- 每个模块可独立运行测试，不依赖完整硬件
- 使用 Mock 模拟 GPIO 和硬件外设

### 测试模块覆盖
| 模块 | 测试方式 | 测试要点 |
|------|----------|----------|
| motor_driver | 单元测试 + Mock GPIO | 步进序列正确性、步数计算、方向控制 |
| stage_controller | 单元测试 + Mock motor | 位置计算、限位逻辑、运动范围约束 |
| led_controller | 单元测试 + Mock PWM | 占空比计算、亮度档位映射、开关逻辑 |
| touch_ui | 手动测试 | UI 交互、触摸响应（LVGL 难以自动化测试） |
| wifi_server | 单元测试 + HTTP 请求 | API 响应正确性、参数验证 |
| system_manager | 单元测试 | 状态转换正确性、预设点存取、配置读写 |

### 测试文件结构
```
tests/
  test_motor_driver.py
  test_stage_controller.py
  test_led_controller.py
  test_wifi_server.py
  test_system_manager.py
```

## Out of Scope

- 图像采集和相机控制（ESP32-P4 可接 MIPI CSI 摄像头，但本期不包含）
- 自动对焦算法
- AI 图像识别
- 3D 打印机械结构设计文件（参考 OpenFlexure 现有设计，不做新的）
- 电池供电
- OTA 固件升级

## Further Notes

- 机械结构建议直接参考 OpenFlexure 的开源 STL 文件 3D 打印
- Waveshare 开发板资料：https://www.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-4B
- OpenFlexure 项目：https://openflexure.org
- 28BYJ-48 驱动库参考：https://github.com/Arve2/stepping-razor
