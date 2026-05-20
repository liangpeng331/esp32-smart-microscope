# 显微镜 Flutter APP

跨平台手机控制应用（iOS / Android），通过 WiFi 连接 ESP32-P4 智能显微镜。

## 功能

- **WiFi 连接管理** — 输入显微镜 IP 地址，自动保存
- **实时状态显示** — 系统状态、3 轴位置
- **XY 摇杆控制** — 四方向 d-pad，支持长按连续移动
- **Z 轴对焦控制** — 上下按钮 + 自动对焦触发
- **LED 调光** — 滑块无级调节 + 4 档预设
- **实时取景** — MJPEG 视频流播放
- **拍照** — 一键拍摄并保存到 SD 卡
- **预设点管理** — 保存/删除/浏览观察位置
- **SD 卡文件浏览** — 列出照片、下载到手机、远程删除

## 开发环境

```bash
# 安装 Flutter SDK (3.16+)
# https://docs.flutter.dev/get-started/install

# 进入项目目录
cd flutter_app

# 获取依赖
flutter pub get

# 运行（连接手机或模拟器）
flutter run

# 构建 APK
flutter build apk --release

# 构建 iOS IPA
flutter build ios --release
```

## 使用流程

1. 手机连接显微镜 WiFi 热点 `Microscope` (密码 12345678)
2. 打开 APP，确认 IP 地址为 `192.168.4.1`
3. 点击"连接显微镜"
4. 进入主界面后可进行以下操作：
   - **控制**标签 — 载物台移动、LED 调光
   - **摄像头**标签 — 实时取景、拍照
   - **预设**标签 — 管理观察位置
   - **文件**标签 — 浏览和下载 SD 卡照片

## 项目结构

```
flutter_app/
├── pubspec.yaml
└── lib/
    ├── main.dart              # 入口 + 导航结构
    ├── api/
    │   └── microscope_api.dart # HTTP API 封装
    ├── models/
    │   └── models.dart         # 数据模型
    ├── screens/
    │   ├── connection_screen.dart # 连接页面
    │   ├── control_screen.dart    # 主控制面板
    │   ├── camera_screen.dart     # 摄像头实时画面
    │   ├── presets_screen.dart    # 预设点管理
    │   └── files_screen.dart      # SD 卡文件浏览
    └── widgets/
        ├── joystick.dart       # XY 摇杆
        ├── z_buttons.dart      # Z 轴按钮
        ├── led_slider.dart     # LED 亮度滑块
        ├── status_card.dart    # 系统状态卡片
        └── mjpeg_viewer.dart   # MJPEG 视频流组件
```
