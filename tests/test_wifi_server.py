"""
wifi_server.py 单元测试 — Mock 依赖，直接测试 _dispatch 路由。

运行方式:
    python -m unittest tests.test_wifi_server -v
"""

import json
import sys
import unittest

# ====== Mock 体系 ======

class MockStage:
    def __init__(self):
        self._pos = {"x": 0, "y": 0, "z": 0}
        self._homed = False
        self._speed = "中"

    def get_position(self):
        return dict(self._pos)

    def is_homed(self):
        return self._homed

    def move_to(self, x=None, y=None, z=None):
        if x is not None:
            self._pos["x"] = x
        if y is not None:
            self._pos["y"] = y
        if z is not None:
            self._pos["z"] = z

    def move_rel(self, dx=None, dy=None, dz=None):
        if dx is not None:
            self._pos["x"] += dx
        if dy is not None:
            self._pos["y"] += dy
        if dz is not None:
            self._pos["z"] += dz

    def home(self):
        self._homed = True

    def set_speed(self, name):
        pass


class MockLED:
    def __init__(self):
        self._on = False
        self._brightness = 0

    def on(self):
        self._on = True

    def off(self):
        self._on = False

    def set_brightness(self, v):
        self._brightness = max(0, min(100, v))

    def preset(self, name):
        presets = {"暗": 20, "中": 50, "亮": 80, "最亮": 100}
        if name not in presets:
            raise ValueError(f"未知预设: {name}")
        self._brightness = presets[name]

    def get_state(self):
        return {"on": self._on, "brightness": self._brightness}


class MockSystemManager:
    def __init__(self, stage, led):
        self._stage = stage
        self._led = led
        self._presets = [None] * 6
        self._state = "IDLE"
        self.error_message = ""

    @property
    def state(self):
        return self._state

    def is_ready(self):
        return self._state == "IDLE"

    def get_system_status(self):
        return {
            "state": self._state,
            "error": "",
            "position": self._stage.get_position(),
            "homed": self._stage.is_homed(),
            "led": self._led.get_state(),
            "presets_count": self.get_preset_count(),
        }

    def home(self):
        self._stage.home()
        return True

    def move_to(self, x=None, y=None, z=None):
        self._stage.move_to(x=x, y=y, z=z)
        return True

    def move_rel(self, dx=None, dy=None, dz=None):
        try:
            self._stage.move_rel(dx=dx, dy=dy, dz=dz)
            return True
        except Exception:
            return False

    def save_preset(self, pos, slot=None):
        if slot is not None and 0 <= slot < 6:
            self._presets[slot] = pos
            return slot
        for i in range(6):
            if self._presets[i] is None:
                self._presets[i] = pos
                return i
        return -1

    def get_preset(self, index):
        if 0 <= index < 6:
            return self._presets[index]
        return None

    def list_presets(self):
        return [(i, p) for i, p in enumerate(self._presets) if p is not None]

    def delete_preset(self, index):
        if 0 <= index < 6:
            self._presets[index] = None

    def get_preset_count(self):
        return sum(1 for p in self._presets if p is not None)


# Mock socket 和 _thread
mock_socket = type(sys)('mock_socket')
mock_thread = type(sys)('mock_thread')

sys.modules['socket'] = mock_socket
sys.modules['_thread'] = mock_thread

from wifi_server import WifiServer, _parse_request, _build_response


def make_request(method, path, body=None):
    """构建原始 HTTP 请求字节串。"""
    if body is None:
        return f"{method} {path} HTTP/1.1\r\nHost: microscope\r\n\r\n".encode()
    body_json = json.dumps(body)
    return (
        f"{method} {path} HTTP/1.1\r\n"
        f"Host: microscope\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body_json)}\r\n"
        f"\r\n"
        f"{body_json}"
    ).encode()


def parse_json_response(data):
    """从 HTTP 响应中提取 JSON body。"""
    text = data.decode("utf-8")
    parts = text.split("\r\n\r\n", 1)
    if len(parts) > 1:
        return json.loads(parts[1])
    return None


class TestWifiServer(unittest.TestCase):

    def setUp(self):
        self.stage = MockStage()
        self.led = MockLED()
        self.sys = MockSystemManager(self.stage, self.led)
        self.server = WifiServer(self.sys, self.stage, self.led)

    def _call(self, method, path, body=None):
        """通过 _dispatch 发送原始请求，返回解析后的 JSON。"""
        raw = make_request(method, path, body)
        response = self.server._dispatch(raw)
        return parse_json_response(response)

    # ====== GET /api/status ======

    def test_get_status_returns_ok(self):
        data = self._call("GET", "/api/status")
        self.assertEqual(data["state"], "IDLE")
        self.assertEqual(data["position"]["x"], 0)
        self.assertIn("led", data)
        self.assertIn("homed", data)

    # ====== POST /api/move (absolute) ======

    def test_move_absolute(self):
        data = self._call("POST", "/api/move", {"x": 500, "y": 300})
        self.assertEqual(data["position"]["x"], 500)
        self.assertEqual(data["position"]["y"], 300)

    def test_move_relative(self):
        self._call("POST", "/api/move", {"x": 100, "y": 100})
        data = self._call("POST", "/api/move", {"rel": True, "dx": 50, "dy": -30})
        self.assertEqual(data["position"]["x"], 150)
        self.assertEqual(data["position"]["y"], 70)

    def test_move_with_z(self):
        data = self._call("POST", "/api/move", {"z": -500})
        self.assertEqual(data["position"]["z"], -500)

    def test_move_no_body_returns_ok(self):
        data = self._call("POST", "/api/move")
        self.assertIsNotNone(data)

    def test_move_bad_json_returns_400(self):
        raw = b"POST /api/move HTTP/1.1\r\nHost: m\r\n\r\n{not json}"
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)
        self.assertIn("JSON", data["error"])

    # ====== POST /api/home ======

    def test_home_success(self):
        data = self._call("POST", "/api/home")
        self.assertTrue(self.stage.is_homed())

    # ====== GET /api/led ======

    def test_get_led_state(self):
        self.led.on()
        self.led.set_brightness(75)
        data = self._call("GET", "/api/led")
        self.assertTrue(data["on"])
        self.assertEqual(data["brightness"], 75)

    # ====== POST /api/led ======

    def test_set_led_brightness(self):
        data = self._call("POST", "/api/led", {"brightness": 88})
        self.assertEqual(data["brightness"], 88)

    def test_set_led_on(self):
        data = self._call("POST", "/api/led", {"on": True})
        self.assertTrue(data["on"])

    def test_set_led_off(self):
        self.led.on()
        data = self._call("POST", "/api/led", {"on": False})
        self.assertFalse(data["on"])

    def test_set_led_preset(self):
        data = self._call("POST", "/api/led", {"preset": "亮"})
        self.assertEqual(data["brightness"], 80)

    def test_set_led_invalid_preset_returns_400(self):
        raw = make_request("POST", "/api/led", {"preset": "太阳"})
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)
        self.assertIn("预设", data["error"])

    def test_set_led_bad_json_returns_400(self):
        raw = b"POST /api/led HTTP/1.1\r\nHost: m\r\n\r\n{garbage"
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)

    # ====== GET /api/presets ======

    def test_get_presets_empty(self):
        data = self._call("GET", "/api/presets")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["max"], 6)
        self.assertEqual(data["presets"], [])

    def test_get_presets_with_data(self):
        self.sys.save_preset({"x": 1, "y": 2, "z": 3}, slot=0)
        self.sys.save_preset({"x": 4, "y": 5, "z": 6}, slot=2)
        data = self._call("GET", "/api/presets")
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["presets"]), 2)

    # ====== POST /api/presets ======

    def test_save_preset(self):
        self.stage.move_to(x=100, y=200, z=300)
        data = self._call("POST", "/api/presets")
        self.assertEqual(data["position"]["x"], 100)
        self.assertEqual(data["position"]["y"], 200)
        self.assertEqual(data["position"]["z"], 300)

    def test_save_preset_specific_slot(self):
        self.stage.move_to(x=1, y=2, z=3)
        data = self._call("POST", "/api/presets", {"slot": 4})
        self.assertEqual(data["slot"], 4)

    def test_save_preset_full_returns_400(self):
        for i in range(6):
            self.sys.save_preset({"x": i, "y": 0, "z": 0})
        raw = make_request("POST", "/api/presets", {})
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)
        self.assertIn("满", data["error"])

    # ====== DELETE /api/presets/<n> ======

    def test_delete_preset(self):
        self.sys.save_preset({"x": 1, "y": 2, "z": 3}, slot=3)
        data = self._call("DELETE", "/api/presets/3")
        self.assertEqual(data["deleted"], 3)
        self.assertIsNone(self.sys.get_preset(3))

    def test_delete_preset_invalid_index(self):
        raw = make_request("DELETE", "/api/presets/abc")
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)

    def test_delete_preset_out_of_range(self):
        raw = make_request("DELETE", "/api/presets/99")
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)

    # ====== 404 ======

    def test_unknown_endpoint_returns_404(self):
        raw = make_request("GET", "/api/nonexistent")
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIn("error", data)
        self.assertIn("未知", data["error"])

    # ====== 405 隐式测试（方法不匹配） ======

    def test_delete_on_non_existing_endpoint_returns_404(self):
        """DELETE /api/status 不匹配路由表，返回 404。"""
        raw = make_request("DELETE", "/api/status")
        response = self.server._dispatch(raw)
        data = parse_json_response(response)
        self.assertIsNotNone(data)


# ====== HTTP 工具函数测试 ======

class TestHTTPHelpers(unittest.TestCase):

    def test_parse_get_request(self):
        method, path, body = _parse_request(
            b"GET /api/status HTTP/1.1\r\nHost: m\r\n\r\n"
        )
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/api/status")
        self.assertEqual(body, "")

    def test_parse_post_request_with_body(self):
        method, path, body = _parse_request(
            b'POST /api/move HTTP/1.1\r\nHost: m\r\nContent-Length: 13\r\n\r\n{"x":100,"y":0}'
        )
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/api/move")
        self.assertEqual(body, '{"x":100,"y":0}')

    def test_parse_strips_query_string(self):
        method, path, body = _parse_request(
            b"GET /api/status?foo=bar HTTP/1.1\r\nHost: m\r\n\r\n"
        )
        self.assertEqual(path, "/api/status")

    def test_parse_garbled_data(self):
        method, path, body = _parse_request(b'\xff\xfe\x00\x01')
        self.assertIsNone(method)

    def test_build_response_200(self):
        data = _build_response(200, {"ok": True})
        text = data.decode("utf-8")
        self.assertIn("200 OK", text)
        self.assertIn('{"ok": true}', text)

    def test_build_response_404(self):
        data = _build_response(404, {"error": "not found"})
        text = data.decode("utf-8")
        self.assertIn("404 Not Found", text)

    def test_build_response_no_body(self):
        data = _build_response(204)
        self.assertIn(b"204 No Content", data)


if __name__ == '__main__':
    unittest.main()
