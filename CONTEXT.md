# CONTEXT — ESP32-P4 智能显微镜

## 领域词汇表

| 术语 | 英文 | 含义 |
|------|------|------|
| 载物台 | Stage | 放置样本的 X/Y 移动平台 |
| 物镜 | Objective | 对焦用的 Z 轴镜头 |
| 云台 | 3-Axis Stage | X/Y 载物台 + Z 物镜的三轴系统 |
| 步进电机 | Stepper Motor | 28BYJ-48 5V 步进电机，半步模式 4096 步/转 |
| 半步 | Half-Step | 8 拍序列驱动，每拍 0.0879°，4096 步/转 |
| 回零 | Homing | 各轴向限位开关移动，触发后停止并校准原点 |
| 预设点 | Preset | 用户保存的可一键跳转的位置点，最多 6 个 |
| 点动 | Jog | 按一下移动一个固定步长的操作方式 |
| 丝杆导程 | Lead Screw Pitch | 丝杆每转一圈的线性位移，默认 0.8mm/转 |
| 限位开关 | Limit Switch | 机械触发开关，标记轴的物理原点 |

## 系统架构

```
main.py                      — 入口，4 阶段启动
├── config.py                — 全局常量（GPIO、电机参数、WiFi 配置）
├── motor_driver.py          — 28BYJ-48 + ULN2003 半步驱动（底层）
├── stage_controller.py      — 3 轴运动控制 + 限位保护 + 校准（中层）
├── led_controller.py        — LED PWM 调光
├── system_manager.py        — 状态机 + 预设点持久化（顶层协调）
├── touch_ui.py              — LVGL 9.x 触摸界面
└── wifi_server.py           — HTTP API 远程控制
```

### 分层关系

```
touch_ui / wifi_server        ← 用户界面层
        │
system_manager                ← 协调层（状态保护、预设点）
   │          │
stage_controller    led_controller  ← 业务逻辑层
   │
motor_driver                    ← 硬件抽象层
   │
machine.Pin / PWM               ← 固件层
```

## 核心概念

### 状态机

```
启动 → IDLE ←→ MOVING → IDLE
  │               ↓
  │    IDLE ←→ HOMING → IDLE
  │               ↓
  └────────→ ERROR ←→ IDLE
```

- 只有 IDLE 状态接受新指令
- ERROR 状态需手动清除（置回 IDLE）
- HOME/MOVING 操作异常时自动进入 ERROR

### 坐标系与运动学

- X/Y 轴：水平载物台，行程 ±10mm
- Z 轴：垂直对焦，行程 −5mm ~ +5mm
- 位置单位：微米 (μm)
- 校准系数：`丝杆导程 (mm/转) / 4096 步 × 1000 = μm/步`
- 默认：0.8mm / 4096 × 1000 ≈ 0.195 μm/步

### 预设点存储

- JSON 文件存储在 microSD 卡 (`/sd/presets.json`)
- 最多 6 个槽位，自动分配或指定槽位
- 位置数据校验：必须包含 x/y/z 三个键

### WiFi 远程控制

- ESP32-C6 协处理器提供 WiFi 6 AP
- HTTP API（非 WebSocket），请求-响应模式
- JSON 格式请求体和响应体
- 8 个 RESTful 端点覆盖全部操作

## 参考项目

- [OpenFlexure](https://openflexure.org) — 开源显微镜机械设计
- [stepping-razor](https://github.com/Arve2/stepping-razor) — 28BYJ-48 驱动参考
- [Waveshare ESP32-P4-WIFI6-Touch-LCD-4B](https://www.waveshare.com/wiki/ESP32-P4-WIFI6-Touch-LCD-4B) — 主控板资料
