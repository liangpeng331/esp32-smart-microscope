# 桌面端控制工具

## 浏览器控制台

打开 `microscope_control.html`，连接显微镜 WiFi 即可远程控制。

- 连接显微镜 WiFi 热点 (SSID: `Microscope`)
- 浏览器打开此文件
- 默认 IP: `192.168.4.1`

### 键盘快捷键

| 键 | 功能 |
|----|------|
| W/A/S/D | X/Y 轴方向移动 |
| Q/E | Z 轴对焦 |
| 箭头键 | 方向键按钮点击 |

## 图像拼接工具

```bash
# 偏移拼接 (快速，适合已知网格布局)
python stitcher.py -f /path/to/grid_images/ -r 3 -c 4 -o result.jpg

# 特征拼接 (精确，需 OpenCV)
python stitcher.py -f /path/to/grid_images/ -m feature -o result.jpg
```

### 依赖

```bash
# 偏移拼接
pip install Pillow

# 特征拼接
pip install opencv-python
```
