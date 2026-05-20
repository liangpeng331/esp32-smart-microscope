#!/usr/bin/env python3
"""
显微图像拼接工具

将网格扫描产生的图像拼接为大视野显微图。

两种模式：
  1. 偏移拼接 (--mode offset): 基于载物台位移量计算像素偏移，快速拼接
  2. 特征拼接 (--mode feature): 基于 ORB/SIFT 特征匹配，精确拼接（需 OpenCV）

用法：
  python stitcher.py --folder /path/to/grid_images/ --rows 3 --cols 4
"""

import argparse
import glob
import os
import sys
import time


# ====== 偏移拼接模式 ======

def stitch_by_offset(image_dir, rows, cols, overlap_pct=20, output="stitched.jpg"):
    """基于已知网格偏移的快速拼接。

    Args:
        image_dir: 图片目录
        rows: 网格行数
        cols: 网格列数
        overlap_pct: 重叠百分比 (0-50)
        output: 输出文件路径
    """
    try:
        from PIL import Image
    except ImportError:
        print("错误: 需要 Pillow 库: pip install Pillow")
        return False

    # 查找图片
    images = sorted(glob.glob(os.path.join(image_dir, "*.jpg"))) + \
             sorted(glob.glob(os.path.join(image_dir, "*.png")))
    if not images:
        print(f"错误: {image_dir} 中未找到图片")
        return False

    print(f"找到 {len(images)} 张图片，预期 {rows}x{cols}={rows*cols} 张")

    # 加载并获取单张尺寸
    tiles = []
    for i, path in enumerate(images):
        try:
            img = Image.open(path)
            tiles.append(img.copy())
            img.close()
        except Exception as e:
            print(f"警告: 无法加载 {path}: {e}")
            tiles.append(None)

    if len(tiles) < rows * cols:
        print(f"警告: 图片数量 ({len(tiles)}) 不足 {rows}x{cols}={rows*cols}")

    # 计算拼接尺寸
    tile_w = max(t.size[0] for t in tiles if t is not None)
    tile_h = max(t.size[1] for t in tiles if t is not None)
    step_x = int(tile_w * (1 - overlap_pct / 100))
    step_y = int(tile_h * (1 - overlap_pct / 100))

    canvas_w = step_x * (cols - 1) + tile_w
    canvas_h = step_y * (rows - 1) + tile_h

    print(f"单张: {tile_w}x{tile_h}, 画布: {canvas_w}x{canvas_h}")
    print(f"步长: X={step_x}px, Y={step_y}px (重叠 {overlap_pct}%)")

    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            if idx >= len(tiles) or tiles[idx] is None:
                print(f"  跳过 [{row},{col}] (索引 {idx})")
                continue
            img = tiles[idx]
            if img.size != (tile_w, tile_h):
                img = img.resize((tile_w, tile_h), Image.LANCZOS)

            x = col * step_x
            y = row * step_y
            # 蛇形路径：奇数行图片水平翻转（与扫描路径一致）
            if row % 2 == 1:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)

            canvas.paste(img, (x, y))
            print(f"  [{row},{col}] → ({x}, {y})")

    canvas.save(output, quality=95)
    print(f"拼接完成 → {output} ({canvas_w}x{canvas_h})")
    return True


# ====== 特征拼接模式 ======

def stitch_by_features(image_dir, output="stitched_feature.jpg"):
    """基于 ORB 特征的自动拼接（需 OpenCV）。"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("错误: 需要 OpenCV: pip install opencv-python")
        return False

    images = sorted(glob.glob(os.path.join(image_dir, "*.jpg"))) + \
             sorted(glob.glob(os.path.join(image_dir, "*.png")))
    if len(images) < 2:
        print("错误: 需要至少 2 张图片")
        return False

    print(f"特征拼接 {len(images)} 张图片...")

    # OpenCV 内置拼接器
    stitcher = cv2.Stitcher.create(cv2.Stitcher_SCANS)
    imgs = [cv2.imread(p) for p in images]

    start = time.time()
    status, result = stitcher.stitch(imgs)
    elapsed = time.time() - start

    if status != cv2.Stitcher_OK:
        print(f"拼接失败: 状态码 {status}")
        return False

    cv2.imwrite(output, result)
    h, w = result.shape[:2]
    print(f"拼接完成 → {output} ({w}x{h}) 耗时 {elapsed:.1f}s")
    return True


# ====== 主入口 ======

def main():
    parser = argparse.ArgumentParser(description="显微图像拼接工具")
    parser.add_argument("--folder", "-f", required=True, help="图片目录")
    parser.add_argument("--mode", "-m", default="offset",
                        choices=["offset", "feature"],
                        help="拼接模式: offset=偏移拼接, feature=特征拼接")
    parser.add_argument("--rows", "-r", type=int, default=3, help="网格行数")
    parser.add_argument("--cols", "-c", type=int, default=3, help="网格列数")
    parser.add_argument("--overlap", "-p", type=int, default=20,
                        help="重叠百分比 (0-50, 默认 20)")
    parser.add_argument("--output", "-o", default="stitched.jpg", help="输出文件")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"错误: 目录不存在: {args.folder}")
        sys.exit(1)

    if args.mode == "offset":
        ok = stitch_by_offset(args.folder, args.rows, args.cols,
                              args.overlap, args.output)
    else:
        ok = stitch_by_features(args.folder, args.output)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
