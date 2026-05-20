"""
显微镜细胞识别与计数引擎。

基于经典计算机视觉方法（Otsu 阈值 + Watershed 分割 + 连通域标记），
不需要 GPU 或深度学习框架，在普通笔记本上即可运行。

算法流程:
    1. 灰度化 → 高斯模糊去噪
    2. Otsu 二值化 → 形态学开运算去噪
    3. 距离变换 → Watershed 分离粘连细胞
    4. 连通域标记 → 统计计数 + 尺寸分布
    5. 可视化输出（标注图 + 分布报告）

用法:
    python3 cell_counter.py <image.jpg> [--output result.jpg]
"""

import argparse
import sys
import json

try:
    import cv2
    import numpy as np
except ImportError:
    print("需要安装 opencv-python: pip install opencv-python numpy")
    sys.exit(1)


class CellCounter:
    """细胞识别与计数引擎。

    Attributes:
        min_area: 最小细胞面积 (像素)，过滤噪点
        max_area: 最大细胞面积 (像素)，过滤大块杂质
        blur_kernel: 高斯模糊核大小
        morph_kernel: 形态学核大小
        dist_thresh: 距离变换阈值系数 (0~1，越小分离越多)
    """

    def __init__(
        self,
        min_area: int = 50,
        max_area: int = 50000,
        blur_kernel: int = 5,
        morph_kernel: int = 3,
        dist_thresh: float = 0.3,
    ):
        self.min_area = max(10, min_area)
        self.max_area = max_area
        self.blur_kernel = blur_kernel if blur_kernel % 2 == 1 else blur_kernel + 1
        self.morph_kernel = morph_kernel
        self.dist_thresh = max(0.05, min(0.95, dist_thresh))

        # 结果
        self.cell_count: int = 0
        self.contours: list = []
        self.sizes: list[float] = []
        self.mask: np.ndarray | None = None
        self.annotated: np.ndarray | None = None

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理：灰度 → 高斯模糊 → Otsu 二值化 → 形态学开运算。"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)

        # Otsu 自动阈值
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 开运算去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                           (self.morph_kernel, self.morph_kernel))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)

        return opened

    def _separate_cells(self, binary: np.ndarray) -> np.ndarray:
        """基于距离变换 + Watershed 分离粘连细胞。

        对二值图做距离变换，用阈值标记前景核心区域，
        未知区域用 Watershed 分水岭分割。
        """
        # 距离变换
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        dist_norm = cv2.normalize(dist, None, 0, 1.0, cv2.NORM_MINMAX)

        # 前景标记：距离变换值大于阈值的区域
        _, fg = cv2.threshold(dist_norm, self.dist_thresh, 1.0, cv2.THRESH_BINARY)
        fg = fg.astype(np.uint8)

        # 背景标记：膨胀二值图取反
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        bg_dilated = cv2.dilate(binary, kernel, iterations=3)
        bg = cv2.bitwise_not(bg_dilated) // 255
        bg = bg.astype(np.uint8)

        # 未知区域
        unknown = cv2.subtract(bg, fg)

        # 连通域标记前景
        _, markers = cv2.connectedComponents(fg)
        markers += 1  # 背景=1 (watershed 要求 >0)

        # 未知区域标记为 0
        markers[unknown == 1] = 0

        return markers

    def _extract_contours(self, markers: np.ndarray) -> list:
        """从 Watershed 标记图中提取每个细胞的轮廓。"""
        # 排除背景 (marker == 1) 和边界 (marker == -1)
        valid = (markers > 1).astype(np.uint8) * 255

        contours, _ = cv2.findContours(valid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 按面积过滤
        filtered = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if self.min_area <= area <= self.max_area:
                filtered.append(cnt)

        return filtered

    def _compute_sizes(self, contours: list) -> list[float]:
        """计算每个细胞的直径（基于面积等效圆）。"""
        sizes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            diameter = 2.0 * np.sqrt(area / np.pi)
            sizes.append(round(diameter, 2))
        return sizes

    def _draw_annotations(self, image: np.ndarray, contours: list) -> np.ndarray:
        """在图像上绘制细胞标注（编号 + 轮廓）。"""
        result = image.copy()

        for i, cnt in enumerate(contours):
            # 随机颜色
            color = (
                (i * 47 + 80) % 256,
                (i * 113 + 150) % 256,
                (i * 73 + 50) % 256,
            )
            cv2.drawContours(result, [cnt], -1, color, 2)

            # 中心点标注编号
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(result, str(i + 1), (cx - 10, cy + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # 总计数
        h, w = image.shape[:2]
        cv2.putText(result, f"Count: {len(contours)}", (10, h - 16),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        return result

    def _build_mask(self, image_shape: tuple, contours: list) -> np.ndarray:
        """构建分割 mask（白色细胞区域，黑色背景）。"""
        mask = np.zeros(image_shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, contours, -1, 255, -1)
        return mask

    def count(self, image: np.ndarray) -> dict:
        """对图像执行完整的细胞计数流程。

        Args:
            image: BGR 彩色图像 (numpy array)

        Returns:
            dict:
                count: 细胞总数
                sizes: 细胞直径列表 (像素)
                mean_size: 平均直径
                median_size: 中位直径
                size_std: 直径标准差
                area_fraction: 细胞面积占比 (%)
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")

        h, w = image.shape[:2]
        total_px = h * w

        # 预处理
        binary = self._preprocess(image)

        # 细胞分离
        markers = self._separate_cells(binary)

        # 提取轮廓
        self.contours = self._extract_contours(markers)
        self.cell_count = len(self.contours)

        # 尺寸统计
        self.sizes = self._compute_sizes(self.contours)

        # 可视化
        self.annotated = self._draw_annotations(image, self.contours)
        self.mask = self._build_mask(image.shape, self.contours)

        # 面积占比
        if self.mask is not None:
            cell_px = cv2.countNonZero(self.mask)
            area_fraction = round(100.0 * cell_px / total_px, 2)
        else:
            area_fraction = 0.0

        sizes_arr = np.array(self.sizes) if self.sizes else np.array([0.0])

        return {
            "count": self.cell_count,
            "sizes": self.sizes,
            "mean_size": round(float(np.mean(sizes_arr)), 2),
            "median_size": round(float(np.median(sizes_arr)), 2),
            "size_std": round(float(np.std(sizes_arr)), 2),
            "min_size": round(float(np.min(sizes_arr)), 2),
            "max_size": round(float(np.max(sizes_arr)), 2),
            "area_fraction": area_fraction,
        }

    def get_annotated(self) -> np.ndarray | None:
        return self.annotated

    def get_mask(self) -> np.ndarray | None:
        return self.mask

    def get_contour_image(self, image: np.ndarray) -> np.ndarray:
        """获取仅包含轮廓叠加的图像（保留原图背景）。"""
        if not self.contours:
            return image
        return self._draw_annotations(image, self.contours)


def print_report(result: dict):
    """打印细胞计数报告。"""
    print("=" * 50)
    print("  显微镜细胞识别与计数报告")
    print("=" * 50)
    print(f"  细胞总数:     {result['count']}")
    print(f"  平均直径:     {result['mean_size']:.1f} px")
    print(f"  中位直径:     {result['median_size']:.1f} px")
    print(f"  直径标准差:   {result['size_std']:.1f} px")
    print(f"  最小直径:     {result['min_size']:.1f} px")
    print(f"  最大直径:     {result['max_size']:.1f} px")
    print(f"  细胞面积占比: {result['area_fraction']:.1f}%")
    print("=" * 50)

    # 尺寸分布直方图（ASCII）
    if result["sizes"]:
        sizes = result["sizes"]
        bins = [0, 10, 20, 40, 80, 160, 1e9]
        labels = ["<10", "10-20", "20-40", "40-80", "80-160", ">160"]
        print("\n  尺寸分布:")
        for i, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
            count = sum(1 for s in sizes if lo <= s < hi)
            bar = "#" * (count * 40 // max(1, len(sizes)) + 1)
            print(f"  {labels[i]:>8} px: {count:4d}  {bar}")


def main():
    parser = argparse.ArgumentParser(
        description="显微镜细胞识别与计数工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 cell_counter.py sample.jpg
  python3 cell_counter.py sample.jpg --output result.jpg
  python3 cell_counter.py sample.jpg --output result.jpg --json result.json
  python3 cell_counter.py sample.jpg --min-area 30 --dist-thresh 0.25
        """,
    )
    parser.add_argument("image", help="输入图像路径")
    parser.add_argument("--output", "-o", help="标注结果输出路径")
    parser.add_argument("--mask", "-m", help="分割 mask 输出路径")
    parser.add_argument("--json", "-j", help="JSON 报告输出路径")
    parser.add_argument("--min-area", type=int, default=50,
                       help="最小细胞面积 (像素，默认 50)")
    parser.add_argument("--max-area", type=int, default=50000,
                       help="最大细胞面积 (像素，默认 50000)")
    parser.add_argument("--dist-thresh", type=float, default=0.3,
                       help="距离变换阈值 (0~1，默认 0.3)")
    parser.add_argument("--blur", type=int, default=5,
                       help="高斯模糊核大小 (默认 5)")

    args = parser.parse_args()

    # 读取图像
    image = cv2.imread(args.image)
    if image is None:
        print(f"错误: 无法读取图像 {args.image}")
        sys.exit(1)

    print(f"输入图像: {args.image}")
    print(f"尺寸: {image.shape[1]}×{image.shape[0]} px")

    # 计数
    counter = CellCounter(
        min_area=args.min_area,
        max_area=args.max_area,
        blur_kernel=args.blur,
        dist_thresh=args.dist_thresh,
    )

    result = counter.count(image)
    print_report(result)

    # 输出
    if args.output:
        annotated = counter.get_annotated()
        if annotated is not None:
            cv2.imwrite(args.output, annotated)
            print(f"\n标注图已保存: {args.output}")

    if args.mask:
        mask = counter.get_mask()
        if mask is not None:
            cv2.imwrite(args.mask, mask)
            print(f"分割 mask 已保存: {args.mask}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"JSON 报告已保存: {args.json}")


if __name__ == "__main__":
    main()
