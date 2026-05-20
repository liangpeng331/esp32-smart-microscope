# ESP32-P4 智能显微镜

基于 Waveshare ESP32-P4-WIFI6-Touch-LCD-4B 的 3 轴电动显微镜控制系统。

广东童园科技有限公司

## 功能

- **3 轴电动云台** — X/Y 载物台 + Z 对焦，28BYJ-48 半步驱动，行程 ±10mm
- **自动回零** — 限位开关校准原点
- **LED PWM 调光** — 4 档预设 + 无级调节
- **摄像头采集** — OV2640/OV5640，JPEG 输出，实时取景
- **自动对焦** — Laplacian 方差清晰度评价，Z 轴扫描合焦
- **定时拍摄** — 间隔拍摄 / Z 轴堆叠 / XY 网格扫描
- **WiFi 远程控制** — HTTP API (8+ 端点)，桌面端控制台
- **触摸屏界面** — LVGL 9.x，720×720 IPS，中文显示
- **离线语音识别** — ESP-SR 唤醒词 + 23 条中文指令
- **图像拼接** — 桌面端偏移/特征拼接工具

## 项目结构

```
esp32-smart-microscope/
├── main.py                 # 主入口 (4 阶段启动)
├── config.py               # 全局配置 (引脚/电机/WiFi/摄像头)
├── motor_driver.py         # 28BYJ-48 + ULN2003 半步驱动
├── stage_controller.py     # 3 轴云台 + 限位 + 回零
├── led_controller.py       # LED PWM 调光
├── system_manager.py       # 状态机 + 预设点管理
├── touch_ui.py             # LVGL 9.x 触摸界面
├── wifi_server.py          # HTTP API 服务器
├── camera_controller.py    # 摄像头采集
├── voice_controller.py     # 语音识别 (ESP-SR)
├── autofocus.py            # 自动对焦
├── timelapse.py            # 定时/堆叠/扫描拍摄
├── desktop/                # 桌面端工具
│   ├── microscope_control.html  # 浏览器控制台
│   ├── stitcher.py              # 图像拼接工具
│   └── README.md
├── tests/                  # 171 个单元测试
├── CONTEXT.md              # 领域文档
├── DEPLOY.md               # 部署指南
└── README.md               # 本文件
```

## 快速开始

1. 烧录 MicroPython 固件到 ESP32-P4
2. 上传所有 `.py` 文件到开发板
3. 上电启动，系统自动初始化
4. 连接 WiFi `Microscope` (密码 12345678)
5. 打开 `desktop/microscope_control.html` 远程控制

详见 [DEPLOY.md](DEPLOY.md)

## 测试

```bash
python3 -m unittest discover -s tests -v   # 171 个测试
```
