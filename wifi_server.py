"""
WiFi Web 远程控制 HTTP API 服务器。

轻量实现，不依赖第三方 HTTP 框架，适配 MicroPython socket API。
作为后台线程运行，不阻塞 UI 事件循环。

API 端点：
    GET  /api/status          — 系统状态
    POST /api/move            — 移动载物台
    POST /api/home            — 回零
    GET  /api/led             — LED 状态
    POST /api/led             — LED 控制
    GET  /api/presets         — 预设点列表
    POST /api/presets         — 保存预设点
    DELETE /api/presets/<n>   — 删除预设点
    GET  /api/camera          — 摄像头状态
    POST /api/camera/capture  — 拍照
    POST /api/camera/preview  — 取景开关
    GET  /api/camera/stream   — MJPEG 实时视频流
"""

import json
import socket
import _thread
import time


# ====== HTTP 工具 ======

STATUS_TEXTS = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

JSON_CONTENT = "application/json; charset=utf-8"
MJPEG_BOUNDARY = "FRAME"


def _parse_request(data):
    """解析原始 HTTP 请求，返回 (method, path, body)。

    只处理第一个请求（不支持 keep-alive 多请求）。
    """
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return None, None, None

    lines = text.split("\r\n")
    if not lines:
        return None, None, None

    # 请求行
    parts = lines[0].split(" ", 2)
    if len(parts) < 2:
        return None, None, None
    method = parts[0].upper()
    path = parts[1].split("?")[0]  # 去查询参数

    # 找到空行后的 body
    body = ""
    try:
        idx = lines.index("")
        body = "\r\n".join(lines[idx + 1:])
    except ValueError:
        pass

    return method, path, body


def _build_response(status, body=None):
    """构建 HTTP 响应字节串。"""
    reason = STATUS_TEXTS.get(status, "Unknown")
    if body is None:
        header = f"HTTP/1.1 {status} {reason}\r\n\r\n"
        return header.encode("utf-8")
    data = json.dumps(body)
    header = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: {JSON_CONTENT}\r\n"
        f"Content-Length: {len(data)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{data}"
    )
    return header.encode("utf-8")


def _build_mjpeg_header():
    """构建 MJPEG 流初始 HTTP 响应头。"""
    return (
        "HTTP/1.1 200 OK\r\n"
        f"Content-Type: multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")


def _build_mjpeg_frame(jpeg_data):
    """将 JPEG 字节包装为 MJPEG 帧。"""
    return (
        f"--{MJPEG_BOUNDARY}\r\n"
        f"Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg_data)}\r\n"
        f"\r\n"
    ).encode("utf-8") + jpeg_data + b"\r\n"


# ====== 路由调度 ======

class WifiServer:
    """HTTP API 服务器，封装路由和请求处理。"""

    BUFFER_SIZE = 1024
    MAX_PRESETS = 6

    def __init__(self, system_manager, stage, led, cam=None):
        """
        Args:
            system_manager: SystemManager 实例
            stage: StageController 实例
            led: LedController 实例
            cam: CameraController 实例 (可选)
        """
        self._sys = system_manager
        self._stage = stage
        self._led = led
        self._cam = cam
        self._sock = None
        self._running = False

        # 路由表
        self._routes = {
            ("GET", "/api/status"): self._handle_status,
            ("POST", "/api/move"): self._handle_move,
            ("POST", "/api/home"): self._handle_home,
            ("GET", "/api/led"): self._handle_get_led,
            ("POST", "/api/led"): self._handle_set_led,
            ("GET", "/api/presets"): self._handle_get_presets,
            ("POST", "/api/presets"): self._handle_save_preset,
            ("GET", "/api/camera"): self._handle_get_camera,
            ("POST", "/api/camera/capture"): self._handle_camera_capture,
            ("POST", "/api/camera/preview"): self._handle_camera_preview,
            ("GET", "/api/files"): self._handle_files_list,
        }
        # 流式端点（不返回响应体，直接写 socket）
        self._stream_routes = {
            ("GET", "/api/camera/stream"): self._handle_stream,
        }

    # ====== 服务器生命周期 ======

    def start(self, host="0.0.0.0", port=80):
        """启动 HTTP 服务器（在后台线程运行）。"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(5)
        self._sock.settimeout(1.0)
        self._running = True

        _thread.start_new_thread(self._serve, ())

    def stop(self):
        """停止服务器。"""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _serve(self):
        """主服务循环，运行在独立线程中。"""
        while self._running:
            try:
                conn, addr = self._sock.accept()
            except OSError:
                continue

            try:
                data = conn.recv(self.BUFFER_SIZE)
                if not data:
                    conn.close()
                    continue

                method, path, body = _parse_request(data)
                if method is None:
                    conn.sendall(_build_response(400, {"error": "无法解析请求"}))
                    conn.close()
                    continue

                # 流式端点：连接保持打开，在 handler 内部关闭
                stream_handler = self._stream_routes.get((method, path))
                if stream_handler is not None:
                    stream_handler(conn, path, body)
                    continue

                # 文件下载（流式）
                if method == "GET" and path.startswith("/api/files/download/"):
                    response = self._handle_file_download(path, conn)
                    if response is not None:
                        conn.sendall(response)
                        conn.close()
                    continue

                # 普通端点
                response = self._dispatch(data)
                conn.sendall(response)
            except Exception:
                try:
                    conn.sendall(_build_response(500, {"error": "内部服务器错误"}))
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    # ====== 请求分发 ======

    def _dispatch(self, raw_data):
        method, path, body = _parse_request(raw_data)
        if method is None:
            return _build_response(400, {"error": "无法解析请求"})

        handler = self._routes.get((method, path))
        if handler is not None:
            return handler(path, body)

        if method == "DELETE" and path.startswith("/api/presets/"):
            return self._handle_delete_preset(path)

        if method == "DELETE" and path.startswith("/api/files/delete/"):
            return self._handle_file_delete(path, body)

        return _build_response(404, {"error": f"未知端点: {method} {path}"})

    # ====== 处理函数 ======

    def _handle_status(self, path, body):
        return _build_response(200, self._sys.get_system_status())

    def _handle_move(self, path, body):
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            return _build_response(400, {"error": "JSON 格式错误"})

        # 相对移动
        if data.get("rel"):
            try:
                self._sys.move_rel(
                    dx=data.get("dx"),
                    dy=data.get("dy"),
                    dz=data.get("dz"),
                )
            except ValueError as e:
                return _build_response(400, {"error": str(e)})
            return _build_response(200, self._sys.get_system_status())

        # 绝对定位
        try:
            self._sys.move_to(
                x=data.get("x"),
                y=data.get("y"),
                z=data.get("z"),
            )
        except ValueError as e:
            return _build_response(400, {"error": str(e)})
        return _build_response(200, self._sys.get_system_status())

    def _handle_home(self, path, body):
        ok = self._sys.home()
        if ok:
            return _build_response(200, self._sys.get_system_status())
        return _build_response(400, {"error": self._sys.error_message or "系统忙"})

    def _handle_get_led(self, path, body):
        return _build_response(200, self._led.get_state())

    def _handle_set_led(self, path, body):
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            return _build_response(400, {"error": "JSON 格式错误"})

        if "preset" in data:
            try:
                self._led.preset(data["preset"])
            except ValueError:
                return _build_response(400, {"error": f"无效预设: {data['preset']}"})
        else:
            if "brightness" in data:
                self._led.set_brightness(data["brightness"])
            if "on" in data:
                if data["on"]:
                    self._led.on()
                else:
                    self._led.off()

        return _build_response(200, self._led.get_state())

    def _handle_get_presets(self, path, body):
        presets = self._sys.list_presets()
        return _build_response(200, {
            "count": self._sys.get_preset_count(),
            "max": self.MAX_PRESETS,
            "presets": [{"slot": i, "position": p} for i, p in presets],
        })

    def _handle_save_preset(self, path, body):
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            return _build_response(400, {"error": "JSON 格式错误"})

        pos = self._stage.get_position()
        slot = data.get("slot", None)
        saved_slot = self._sys.save_preset(pos, slot=slot)
        if saved_slot < 0:
            return _build_response(400, {"error": "预设槽位已满"})
        return _build_response(201, {
            "slot": saved_slot,
            "position": self._sys.get_preset(saved_slot),
        })

    def _handle_delete_preset(self, path):
        try:
            idx = int(path.rsplit("/", 1)[-1])
        except (ValueError, IndexError):
            return _build_response(400, {"error": "无效槽位编号"})

        if not (0 <= idx < self.MAX_PRESETS):
            return _build_response(404, {"error": f"槽位 {idx} 不存在"})

        self._sys.delete_preset(idx)
        return _build_response(200, {"deleted": idx})

    # ====== 摄像头处理 ======

    def _handle_get_camera(self, path, body):
        if self._cam is None:
            return _build_response(404, {"error": "摄像头未连接"})
        return _build_response(200, self._cam.get_state())

    def _handle_camera_capture(self, path, body):
        if self._cam is None:
            return _build_response(404, {"error": "摄像头未连接"})
        import time
        filename = f"/sd/photo_{int(time.time())}.jpg"
        if self._cam.capture_to_file(filename):
            return _build_response(201, {"file": filename})
        return _build_response(500, {"error": "拍照失败"})

    def _handle_camera_preview(self, path, body):
        if self._cam is None:
            return _build_response(404, {"error": "摄像头未连接"})
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            return _build_response(400, {"error": "JSON 格式错误"})
        enable = data.get("enable", False)
        if enable:
            ok = self._cam.start_preview()
        else:
            self._cam.stop_preview()
            ok = True
        if ok:
            return _build_response(200, self._cam.get_state())
        return _build_response(500, {"error": "预览操作失败"})

    # ====== MJPEG 流 ======

    def _handle_stream(self, conn, path, body):
        """MJPEG 实时视频流。

        持续从摄像头采集 JPEG 帧，通过 multipart 响应推流。
        客户端断开或服务器停止时结束。
        """
        if self._cam is None:
            conn.sendall(_build_response(404, {"error": "摄像头未连接"}))
            conn.close()
            return

        try:
            # 发送 MJPEG 响应头
            conn.sendall(_build_mjpeg_header())

            # 持续推流
            fps_delay = 1.0 / max(1, min(30, self._cam._fps))
            while self._running:
                try:
                    jpeg = self._cam.capture()
                    if jpeg:
                        frame = _build_mjpeg_frame(jpeg)
                        conn.sendall(frame)
                    time.sleep(fps_delay)
                except OSError:
                    break  # 客户端断开
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ====== 文件管理 ======

    def _handle_files_list(self, path, body):
        """列出 SD 卡文件。"""
        import os as _os
        try:
            files = []
            for name in _os.listdir("/sd"):
                try:
                    stat = _os.stat(f"/sd/{name}")
                    files.append({
                        "name": name,
                        "size": stat[6],
                        "is_dir": stat[0] & 0x4000 != 0,
                    })
                except OSError:
                    pass
            files.sort(key=lambda f: f["name"])
            return _build_response(200, {"files": files, "count": len(files)})
        except OSError:
            return _build_response(500, {"error": "SD 卡不可用"})

    def _handle_file_download(self, path, conn):
        """下载文件（流式传输给调用方）。"""
        filename = path.split("/api/files/download/", 1)[-1]
        filepath = f"/sd/{filename}"

        # 安全检查：防止目录穿越
        if ".." in filename or "/" in filename:
            return _build_response(400, {"error": "无效文件名"})

        import os as _os
        try:
            stat = _os.stat(filepath)
            size = stat[6]
        except OSError:
            return _build_response(404, {"error": f"文件不存在: {filename}"})

        try:
            header = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/octet-stream\r\n"
                f"Content-Length: {size}\r\n"
                f"Content-Disposition: attachment; filename=\"{filename}\"\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode("utf-8")
            conn.sendall(header)

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    conn.sendall(chunk)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return None  # 已在 handler 内关闭连接

    def _handle_file_delete(self, path, body):
        """删除文件。"""
        filename = path.split("/api/files/delete/", 1)[-1]
        if ".." in filename or "/" in filename:
            return _build_response(400, {"error": "无效文件名"})

        try:
            import os as _os
            _os.remove(f"/sd/{filename}")
            return _build_response(200, {"deleted": filename})
        except OSError:
            return _build_response(404, {"error": f"文件不存在: {filename}"})
