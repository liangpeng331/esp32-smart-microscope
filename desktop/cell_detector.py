"""
深度学习细胞检测引擎 (YOLOv8 + UNet)。

提供两套方案:
    YOLOv8 nano  — 轻量目标检测，框出每个细胞并计数
    UNet          — 语义分割，精确逐像素细胞/背景分类

在桌面端运行，通过显微镜 HTTP API 下载图像后推理。

用法:
    python3 cell_detector.py <image.jpg> --model yolov8n
    python3 cell_detector.py <image.jpg> --model unet --weights cells_unet.pt

依赖:
    pip install ultralytics torch torchvision opencv-python numpy
"""

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np


# ====== YOLOv8 细胞检测器 ======

class YoloCellDetector:
    """基于 YOLOv8 的细胞目标检测。

    Attributes:
        model_name: YOLOv8 模型名 (yolov8n / yolov8s / 自定义权重)
        conf_thresh: 置信度阈值
        iou_thresh: NMS IoU 阈值
    """

    def __init__(self, model_name="yolov8n.pt", conf_thresh=0.25, iou_thresh=0.45):
        self.model_name = model_name
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self._model = None
        self._results = None
        self._boxes = []
        self._annotated = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_name)
        except ImportError:
            raise ImportError("需要 ultralytics: pip install ultralytics")
        except Exception as e:
            raise RuntimeError(f"加载模型失败: {e}")

    def detect(self, image: np.ndarray) -> dict:
        """对图像执行细胞检测。

        Args:
            image: BGR 图像

        Returns:
            dict: count / boxes / sizes / mean_conf
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")

        self._load_model()
        results = self._model(image, conf=self.conf_thresh, iou=self.iou_thresh,
                             verbose=False)
        self._results = results

        boxes = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self._model.names.get(cls_id, f"cls_{cls_id}")
                w, h = x2 - x1, y2 - y1
                boxes.append({
                    "x": round(x1, 1), "y": round(y1, 1),
                    "w": round(w, 1), "h": round(h, 1),
                    "confidence": round(conf, 4),
                    "class": cls_name,
                    "diameter_px": round(np.sqrt(w * h), 1),
                })

        self._boxes = boxes
        self._annotated = results[0].plot() if results else image

        confs = [b["confidence"] for b in boxes]
        diameters = [b["diameter_px"] for b in boxes]

        return {
            "count": len(boxes),
            "boxes": boxes,
            "diameters": diameters,
            "mean_diameter": round(np.mean(diameters), 1) if diameters else 0,
            "mean_confidence": round(np.mean(confs), 4) if confs else 0,
            "median_confidence": round(np.median(confs), 4) if confs else 0,
        }

    def get_annotated(self) -> np.ndarray | None:
        """返回已标注的图像。"""
        return self._annotated


# ====== UNet 语义分割 ======

class UNetCellSegmenter:
    """基于 U-Net 的细胞语义分割。

    逐像素分类：细胞 vs 背景。适合测量细胞形态（面积、周长、圆度）。
    需要训练好的 .pt / .pth 权重文件。
    """

    def __init__(self, weights_path: str, device="cpu", input_size=512):
        self.weights_path = weights_path
        self.device = device
        self.input_size = input_size
        self._model = None
        self._mask = None
        self._contours = []

    def _load_model(self):
        if self._model is not None:
            return
        if not os.path.exists(self.weights_path):
            raise FileNotFoundError(f"权重文件不存在: {self.weights_path}")
        try:
            import torch
            self._model = torch.load(self.weights_path, map_location=self.device,
                                     weights_only=False)
            self._model.eval()
        except ImportError:
            raise ImportError("需要 torch: pip install torch torchvision")
        except Exception as e:
            raise RuntimeError(f"加载 UNet 模型失败: {e}")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理：缩放 + 归一化。"""
        h, w = image.shape[:2]
        scale = self.input_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(image, (new_w, new_h))

        # Pad 到 input_size × input_size
        padded = np.zeros((self.input_size, self.input_size, 3), dtype=np.float32)
        y_off = (self.input_size - new_h) // 2
        x_off = (self.input_size - new_w) // 2
        padded[y_off:y_off + new_h, x_off:x_off + new_w] = resized.astype(np.float32) / 255.0

        import torch
        tensor = torch.from_numpy(padded).permute(2, 0, 1).unsqueeze(0)
        return tensor, (h, w, scale, y_off, x_off)

    def segment(self, image: np.ndarray) -> dict:
        """执行语义分割。

        Returns:
            dict: count / contours / area_fraction / mean_area_px
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")

        self._load_model()
        import torch

        tensor, meta = self._preprocess(image)
        h_orig, w_orig, scale, y_off, x_off = meta

        with torch.no_grad():
            output = self._model(tensor)
            if isinstance(output, dict):
                output = output.get("out", next(iter(output.values())))
            pred = torch.sigmoid(output).squeeze().cpu().numpy()

        # 缩放回原始尺寸
        pred_cropped = pred[y_off:y_off + int(h_orig * scale),
                            x_off:x_off + int(w_orig * scale)]
        mask_full = cv2.resize(pred_cropped, (w_orig, h_orig))

        # 二值化
        binary = (mask_full > 0.5).astype(np.uint8) * 255

        # 后处理：开运算去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # 连通域
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 过滤小噪点
        min_area = 10
        contours = [c for c in contours if cv2.contourArea(c) >= min_area]
        self._contours = contours

        areas = [cv2.contourArea(c) for c in contours]
        total_cell_px = sum(areas)
        total_px = h_orig * w_orig

        self._mask = cleaned

        return {
            "count": len(contours),
            "countours": len(self._contours),
            "areas": [round(a, 1) for a in areas],
            "mean_area_px": round(np.mean(areas), 1) if areas else 0,
            "median_area_px": round(np.median(areas), 1) if areas else 0,
            "area_fraction": round(100.0 * total_cell_px / total_px, 2) if total_px > 0 else 0,
        }

    def get_mask(self) -> np.ndarray | None:
        return self._mask

    def get_annotated(self, image: np.ndarray) -> np.ndarray:
        """在图像上叠加分割结果。"""
        if self._mask is None:
            return image
        overlay = cv2.cvtColor(self._mask, cv2.COLOR_GRAY2BGR)
        overlay[self._mask > 0] = (0, 255, 0)
        return cv2.addWeighted(image, 0.7, overlay, 0.3, 0)


# ====== 模型训练脚本骨架 ======

def train_yolo(data_yaml: str, epochs=100, model="yolov8n.pt", imgsz=640):
    """训练 YOLOv8 细胞检测模型。

    Args:
        data_yaml: 数据集配置文件路径
        epochs: 训练轮数
        model: 预训练模型
        imgsz: 输入图像尺寸

    数据集格式 (data.yaml):
        path: ./dataset
        train: images/train
        val: images/val
        names:
          0: cell
          1: cluster
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("pip install ultralytics")
        sys.exit(1)

    yolo = YOLO(model)
    results = yolo.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=16,
        device="mps" if sys.platform == "darwin" else "cuda" if os.system("which nvidia-smi >/dev/null 2>&1") == 0 else "cpu",
        workers=4,
        patience=20,
        save=True,
        save_period=10,
        project="runs/cell_detect",
        name=f"train_{time.strftime('%Y%m%d_%H%M')}",
    )
    return results


def train_unet(image_dir: str, mask_dir: str, epochs=50, lr=1e-4):
    """训练 UNet 细胞分割模型。

    数据要求:
        image_dir/   — 原始显微镜图像 (.jpg)
        mask_dir/    — 二值标注 mask (.png), 白色=细胞 黑色=背景
    """
    print("训练 UNet 需要完整的数据集准备，请参考:")
    print("  https://github.com/milesial/Pytorch-UNet")
    print(f"  images: {image_dir}")
    print(f"  masks:  {mask_dir}")
    print(f"  epochs: {epochs}  lr: {lr}")
    # 实际训练代码取决于具体UNet实现
    # 框架示例见 train_unet_cells.ipynb


# ====== CLI ======

def main():
    parser = argparse.ArgumentParser(
        description="深度学习细胞检测 (YOLOv8 / UNet)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 cell_detector.py sample.jpg --model yolov8n
  python3 cell_detector.py sample.jpg --model yolov8s --conf 0.3
  python3 cell_detector.py sample.jpg --model unet --weights cells_unet.pt
  python3 cell_detector.py --train data.yaml --epochs 100
        """,
    )
    parser.add_argument("image", nargs="?", help="输入图像路径")
    parser.add_argument("--model", default="yolov8n",
                       choices=["yolov8n", "yolov8s", "yolov8m", "unet"])
    parser.add_argument("--weights", help="模型权重路径 (UNet 必填)")
    parser.add_argument("--conf", type=float, default=0.25,
                       help="YOLO 置信度阈值 (默认 0.25)")
    parser.add_argument("--output", "-o", help="标注结果输出路径")
    parser.add_argument("--json", "-j", help="JSON 报告输出路径")
    parser.add_argument("--train", help="训练 YOLO 模型 (传入 data.yaml)")

    args = parser.parse_args()

    # 训练模式
    if args.train:
        train_yolo(args.train)
        return

    if not args.image:
        parser.print_help()
        return

    image = cv2.imread(args.image)
    if image is None:
        print(f"错误: 无法读取图像 {args.image}")
        sys.exit(1)

    if args.model == "unet":
        if not args.weights:
            print("错误: UNet 需要 --weights 参数")
            sys.exit(1)
        detector = UNetCellSegmenter(args.weights)
        result = detector.segment(image)
        annotated = detector.get_annotated(image)
    else:
        detector = YoloCellDetector(model_name=f"{args.model}.pt", conf_thresh=args.conf)
        result = detector.detect(image)
        annotated = detector.get_annotated()

    # 输出
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.output and annotated is not None:
        cv2.imwrite(args.output, annotated)
        print(f"标注图: {args.output}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"JSON: {args.json}")


if __name__ == "__main__":
    main()
