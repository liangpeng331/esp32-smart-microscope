#!/usr/bin/env python3
"""
显微镜细胞分析桌面客户端。

从显微镜 HTTP API 下载照片，调用 CellCounter 识别计数，
生成标注图和 JSON 报告。

用法:
    python3 cell_analysis_client.py [显微镜IP] [选项]

示例:
    python3 cell_analysis_client.py 192.168.4.1
    python3 cell_analysis_client.py 192.168.4.1 --capture
    python3 cell_analysis_client.py 192.168.4.1 --file photo_001.jpg
    python3 cell_analysis_client.py 192.168.4.1 --batch 10 --interval 5
"""

import argparse
import json
import sys
import time
import os
import urllib.request
import urllib.error
from datetime import datetime

# 导入细胞计数引擎
from cell_counter import CellCounter, print_report


class MicroscopeClient:
    """显微镜 HTTP API 客户端。"""

    def __init__(self, host: str, port: int = 80):
        self.base = f"http://{host}:{port}" if port != 80 else f"http://{host}"

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(f"{self.base}{path}", timeout=5) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: dict | None = None) -> dict:
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            f"{self.base}{path}", data=body,
            headers={"Content-Type": "application/json"} if body else {},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def status(self) -> dict:
        return self._get("/api/status")

    def capture(self) -> dict:
        return self._post("/api/camera/capture")

    def list_files(self) -> list:
        data = self._get("/api/files")
        return data.get("files", [])

    def download(self, filename: str, dest: str) -> bool:
        url = f"{self.base}/api/files/download/{urllib.parse.quote(filename)}"
        try:
            urllib.request.urlretrieve(url, dest)
            return os.path.exists(dest) and os.path.getsize(dest) > 0
        except Exception:
            return False


def analyze_image(image_path: str, output_dir: str | None, **counter_kwargs):
    """分析单张图像。"""
    import cv2

    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取 {image_path}")
        return None

    counter = CellCounter(**counter_kwargs)
    result = counter.count(image)
    print_report(result)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(image_path))[0]

        # 标注图
        annotated = counter.get_annotated()
        if annotated is not None:
            out = os.path.join(output_dir, f"{base}_annotated.jpg")
            cv2.imwrite(out, annotated)
            print(f"标注图: {out}")

        # Mask
        mask = counter.get_mask()
        if mask is not None:
            out = os.path.join(output_dir, f"{base}_mask.png")
            cv2.imwrite(out, mask)
            print(f"分割图: {out}")

        # JSON
        out = os.path.join(output_dir, f"{base}_report.json")
        with open(out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"报告: {out}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="显微镜细胞分析桌面客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
操作模式:
  --capture        从显微镜拍照后分析
  --file NAME      分析显微镜 SD 卡上的指定文件
  --local PATH     分析本地图像文件
  --batch N        批量拍照 N 张并分析
  --live           持续监听模式（每 N 秒拍照分析）
        """,
    )
    parser.add_argument("host", nargs="?", default="192.168.4.1",
                       help="显微镜 IP 地址 (默认: 192.168.4.1)")
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--capture", action="store_true", help="拍照并分析")
    parser.add_argument("--file", help="从显微镜 SD 卡下载指定文件并分析")
    parser.add_argument("--local", help="分析本地图像文件")
    parser.add_argument("--batch", type=int, metavar="N", help="批量拍照 N 张")
    parser.add_argument("--interval", type=float, default=3.0,
                       help="批量间隔 (秒，默认 3)")
    parser.add_argument("--live", action="store_true", help="持续监听模式")
    parser.add_argument("--output", "-o", default="./analysis_output",
                       help="输出目录 (默认 ./analysis_output)")
    parser.add_argument("--min-area", type=int, default=50)
    parser.add_argument("--dist-thresh", type=float, default=0.3)

    args = parser.parse_args()

    output_dir = args.output
    counter_kwargs = {
        "min_area": args.min_area,
        "dist_thresh": args.dist_thresh,
    }

    client = MicroscopeClient(args.host, args.port) if not args.local else None

    # 测试连接
    if client:
        try:
            s = client.status()
            print(f"已连接显微镜: {args.host}")
            print(f"状态: {s.get('state', '?')}")
        except Exception as e:
            print(f"无法连接显微镜 ({args.host}): {e}")
            print("使用 --local 模式分析本地文件")
            client = None

    # 本地分析模式
    if args.local:
        analyze_image(args.local, output_dir, **counter_kwargs)
        return

    # 指定文件模式
    if args.file:
        if client is None:
            print("需要显微镜连接")
            sys.exit(1)
        local = os.path.join(output_dir, args.file)
        print(f"下载中: {args.file} ...")
        if client.download(args.file, local):
            analyze_image(local, output_dir, **counter_kwargs)
        else:
            print(f"下载失败: {args.file}")
        return

    # 单次拍照模式
    if args.capture:
        if client is None:
            print("需要显微镜连接")
            sys.exit(1)
        print("拍照中...")
        result = client.capture()
        filename = os.path.basename(result.get("file", ""))
        if not filename:
            print("拍照失败")
            sys.exit(1)
        local = os.path.join(output_dir, filename)
        print(f"下载中: {filename} ...")
        if client.download(filename, local):
            analyze_image(local, output_dir, **counter_kwargs)
        else:
            print(f"下载失败: {filename}")
        return

    # 批量模式
    if args.batch:
        if client is None:
            print("需要显微镜连接")
            sys.exit(1)
        os.makedirs(output_dir, exist_ok=True)
        all_results = []
        for i in range(args.batch):
            print(f"\n--- [{i+1}/{args.batch}] ---")
            result = client.capture()
            filename = os.path.basename(result.get("file", ""))
            if filename:
                local = os.path.join(output_dir, filename)
                if client.download(filename, local):
                    r = analyze_image(local, output_dir, **counter_kwargs)
                    if r:
                        r["_filename"] = filename
                        all_results.append(r)
            if i < args.batch - 1:
                time.sleep(args.interval)

        # 汇总报告
        if all_results:
            summary = {
                "batch_count": len(all_results),
                "total_cells": sum(r["count"] for r in all_results),
                "avg_cells": sum(r["count"] for r in all_results) / len(all_results),
            }
            print("\n" + "=" * 50)
            print(f"  批量分析汇总 ({len(all_results)} 张)")
            print(f"  总细胞数: {summary['total_cells']}")
            print(f"  平均每张: {summary['avg_cells']:.1f}")
            print("=" * 50)
        return

    # 持续监听模式
    if args.live:
        if client is None:
            print("需要显微镜连接")
            sys.exit(1)
        os.makedirs(output_dir, exist_ok=True)
        seq = 0
        print("持续监听模式 (Ctrl+C 停止)")
        try:
            while True:
                seq += 1
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 拍摄 #{seq} ...")
                try:
                    result = client.capture()
                    filename = os.path.basename(result.get("file", ""))
                    if filename:
                        local = os.path.join(output_dir, filename)
                        if client.download(filename, local):
                            analyze_image(local, output_dir, **counter_kwargs)
                except Exception as e:
                    print(f"  错误: {e}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n监听停止，共处理 {seq} 张")
        return

    # 默认：打印状态
    if client:
        s = client.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
