#!/usr/bin/env python3
"""
景深合成工具 (Focus Stacking)

将 Z 轴堆叠拍摄的多张照片合成为一张全景深图像。

算法：
  1. 拉普拉斯金字塔分解
  2. 每层取局部方差最大的像素
  3. 金字塔重建

用法：
  python focus_stack.py -f /path/to/zstack/ -o result.jpg

依赖：
  pip install opencv-python numpy
"""

import argparse
import glob
import os
import sys
import time


def focus_stack_laplacian(image_paths, output="focus_stacked.jpg",
                          levels=5, blend_width=16):
    """基于拉普拉斯金字塔的景深合成。

    Args:
        image_paths: 图片路径列表
        output: 输出文件
        levels: 金字塔层数
        blend_width: 混合过渡宽度 (px)
    """
    import cv2
    import numpy as np

    images = []
    for p in image_paths:
        img = cv2.imread(p)
        if img is not None:
            images.append(img)

    if len(images) < 2:
        print("错误: 需要至少 2 张图片")
        return False

    print(f"加载 {len(images)} 张图片，开始景深合成...")

    # 统一尺寸
    h = min(img.shape[0] for img in images)
    w = min(img.shape[1] for img in images)
    images = [img[:h, :w] for img in images]

    start = time.time()

    # 为每张图构建拉普拉斯金字塔和高斯金字塔
    laps = []
    gauss_maps = []
    for img in images:
        img_f = img.astype(np.float32)
        lap_pyr = _build_laplacian_pyramid(img_f, levels)
        laps.append(lap_pyr)

        # 对每层计算局部方差作为聚焦度量
        gauss_pyr = _build_gaussian_pyramid(
            _compute_focus_map(img), levels
        )
        gauss_maps.append(gauss_pyr)

    # 在每层金字塔取最佳聚焦像素
    merged_pyr = []
    for level in range(levels):
        # 所有图像的该层拉普拉斯图
        layer_stack = np.stack([lap[level] for lap in laps], axis=0)
        # 所有图像的该层聚焦权重
        weight_stack = np.stack([gm[level] for gm in gauss_maps], axis=0)

        # Softmax 归一化权重
        weight_stack -= weight_stack.max(axis=0, keepdims=True)
        weight_stack = np.exp(weight_stack * 2)  # 温度系数 2
        weight_sum = weight_stack.sum(axis=0, keepdims=True) + 1e-8
        weight_stack /= weight_sum

        # 加权融合
        merged = (layer_stack * weight_stack).sum(axis=0)
        merged_pyr.append(merged)

    # 重建图像
    result = _reconstruct_from_pyramid(merged_pyr)
    result = np.clip(result, 0, 255).astype(np.uint8)

    elapsed = time.time() - start
    cv2.imwrite(output, result)
    print(f"景深合成完成 → {output} ({w}x{h}) 耗时 {elapsed:.1f}s")
    return True


def _compute_focus_map(img):
    """计算每个像素的局部聚焦度量 (Laplacian 方差)。"""
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # 拉普拉斯算子
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)

    # 局部窗口内的方差
    kernel = np.ones((9, 9), np.float32) / 81
    lap_sq = lap * lap
    local_var = cv2.filter2D(lap_sq, -1, kernel)

    # 归一化
    local_var = (local_var - local_var.min()) / (local_var.max() - local_var.min() + 1e-8)

    # 扩展到 3 通道
    return np.stack([local_var] * 3, axis=-1)


def _build_gaussian_pyramid(img, levels):
    """构建高斯金字塔。"""
    import cv2
    pyr = [img]
    for _ in range(levels - 1):
        img = cv2.pyrDown(img)
        pyr.append(img)
    return pyr


def _build_laplacian_pyramid(img, levels):
    """构建拉普拉斯金字塔。"""
    import cv2
    gauss = _build_gaussian_pyramid(img, levels)
    lap = []
    for i in range(levels - 1):
        expanded = cv2.pyrUp(gauss[i + 1], dstsize=(gauss[i].shape[1], gauss[i].shape[0]))
        lap.append(gauss[i] - expanded)
    lap.append(gauss[-1])
    return lap


def _reconstruct_from_pyramid(pyramid):
    """从拉普拉斯金字塔重建图像。"""
    import cv2
    img = pyramid[-1]
    for i in range(len(pyramid) - 2, -1, -1):
        img = cv2.pyrUp(img, dstsize=(pyramid[i].shape[1], pyramid[i].shape[0]))
        img += pyramid[i]
    return img


# ====== 主入口 ======

def main():
    parser = argparse.ArgumentParser(description="景深合成工具")
    parser.add_argument("--folder", "-f", required=True, help="Z 轴堆叠图片目录")
    parser.add_argument("--output", "-o", default="focus_stacked.jpg", help="输出文件")
    parser.add_argument("--levels", "-l", type=int, default=5, help="金字塔层数 (默认 5)")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"错误: 目录不存在: {args.folder}")
        sys.exit(1)

    images = sorted(glob.glob(os.path.join(args.folder, "*.jpg"))) + \
             sorted(glob.glob(os.path.join(args.folder, "*.png")))
    if len(images) < 2:
        print(f"错误: {args.folder} 中需要至少 2 张图片")
        sys.exit(1)

    ok = focus_stack_laplacian(images, args.output, args.levels)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
