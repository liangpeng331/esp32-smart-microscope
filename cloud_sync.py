"""
云端同步模块。

将显微镜分析结果和照片上传到云端，支持:
    - MQTT 遥测上报 (设备端，轻量)
    - HTTP Webhook 推送 (设备端/桌面端)
    - OSS 对象存储上传 (桌面端)

ESP32-P4 设备端用 MQTT 或 HTTP POST 上报摘要，
桌面端负责大文件（照片、标注图）的 OSS 上传。

用法:
    # 设备端
    from cloud_sync import CloudSync
    cs = CloudSync(mqtt_broker="mqtt.example.com")
    cs.publish_analysis({"count": 42})

    # 桌面端
    from cloud_sync import upload_to_oss, webhook_notify
    upload_to_oss("photo.jpg", endpoint="oss-cn-shenzhen.aliyuncs.com")
"""

import json
import time

# MicroPython / CPython 兼容
if hasattr(time, 'sleep_ms'):
    _sleep_ms = time.sleep_ms
else:
    _sleep_ms = lambda ms: time.sleep(ms / 1000.0)

_MQTT_AVAILABLE = False
_HTTP_AVAILABLE = False

try:
    import urequests as requests
    _HTTP_AVAILABLE = True
except ImportError:
    try:
        import requests
        _HTTP_AVAILABLE = True
    except ImportError:
        pass

try:
    import umqtt.simple as mqtt
    _MQTT_AVAILABLE = True
except ImportError:
    try:
        import paho.mqtt.client as mqtt
        _MQTT_AVAILABLE = True
    except ImportError:
        pass


# ====== 设备端云同步 ======

class CloudSync:
    """设备端云同步客户端。

    Args:
        mqtt_broker: MQTT 服务地址
        mqtt_topic: MQTT 上报主题
        webhook_url: HTTP Webhook URL
        device_id: 设备标识
    """

    def __init__(self, mqtt_broker=None, mqtt_topic="microscope/report",
                 webhook_url=None, device_id="esp32p4-001"):
        self._mqtt_broker = mqtt_broker
        self._mqtt_topic = mqtt_topic
        self._webhook_url = webhook_url
        self._device_id = device_id
        self._mqtt_client = None
        self._connected = False

    # ---- MQTT ----

    def mqtt_connect(self):
        """连接 MQTT 服务器。"""
        if not _MQTT_AVAILABLE:
            return False
        if self._mqtt_broker is None:
            return False
        try:
            if "umqtt" in str(type):
                self._mqtt_client = mqtt.MQTTClient(self._device_id, self._mqtt_broker)
                self._mqtt_client.connect()
            else:
                self._mqtt_client = mqtt.Client(self._device_id)
                self._mqtt_client.connect(self._mqtt_broker)
            self._connected = True
            return True
        except Exception:
            return False

    def mqtt_disconnect(self):
        if self._mqtt_client:
            try:
                self._mqtt_client.disconnect()
            except Exception:
                pass
            self._mqtt_client = None
        self._connected = False

    def publish(self, payload: dict):
        """通过 MQTT 上报数据。

        Returns:
            bool: 上报成功返回 True
        """
        if not self._connected:
            if not self.mqtt_connect():
                return False

        try:
            data = json.dumps({
                "device_id": self._device_id,
                "timestamp": time.time() if hasattr(time, 'time') else 0,
                **payload,
            })
            if hasattr(self._mqtt_client, 'publish'):
                self._mqtt_client.publish(self._mqtt_topic, data)

            _sleep_ms(100)
            return True
        except Exception:
            self._connected = False
            return False

    def publish_analysis(self, result: dict):
        """上报细胞分析结果（精简版，不含图片）。"""
        return self.publish({
            "type": "analysis",
            "count": result.get("count", result.get("estimated_count", 0)),
            "method": result.get("method", "unknown"),
        })

    def publish_status(self, status: dict):
        """上报设备状态。"""
        return self.publish({
            "type": "status",
            "state": status.get("state", "?"),
            "uptime_sec": time.time() if hasattr(time, 'time') else 0,
        })

    # ---- HTTP Webhook ----

    def webhook(self, payload: dict):
        """通过 HTTP POST 推送数据到 Webhook URL。"""
        if not _HTTP_AVAILABLE or self._webhook_url is None:
            return False
        try:
            data = json.dumps({
                "device_id": self._device_id,
                "timestamp": time.time() if hasattr(time, 'time') else 0,
                **payload,
            })
            requests.post(self._webhook_url, data=data,
                         headers={"Content-Type": "application/json"},
                         timeout=5)
            return True
        except Exception:
            return False

    # ---- 状态 ----

    def get_state(self):
        return {
            "device_id": self._device_id,
            "mqtt_connected": self._connected,
            "mqtt_broker": self._mqtt_broker,
            "webhook_url": self._webhook_url is not None,
        }


# ====== 桌面端 OSS 上传 ======

def upload_to_oss(filepath: str, endpoint: str, bucket: str, access_key: str,
                  secret_key: str, object_name=None) -> bool:
    """上传文件到 OSS (阿里云/兼容 S3)。

    依赖: pip install oss2

    Args:
        filepath: 本地文件路径
        endpoint: OSS Endpoint
        bucket: Bucket 名称
        access_key: AccessKey ID
        secret_key: AccessKey Secret
        object_name: OSS 对象名（默认用文件名）

    Returns:
        bool: 上传成功返回 True
    """
    if not os.path.exists(filepath):
        return False

    if object_name is None:
        object_name = os.path.basename(filepath)

    try:
        import oss2
        auth = oss2.Auth(access_key, secret_key)
        bucket_obj = oss2.Bucket(auth, endpoint, bucket)
        bucket_obj.put_object_from_file(object_name, filepath)
        print(f"已上传: {filepath} → oss://{bucket}/{object_name}")
        return True
    except ImportError:
        print("需要 oss2: pip install oss2")
        return False
    except Exception as e:
        print(f"上传失败: {e}")
        return False


def webhook_notify(webhook_url: str, payload: dict) -> bool:
    """向 Webhook URL 发送通知（桌面端）。"""
    if not _HTTP_AVAILABLE:
        return False
    try:
        requests.post(webhook_url, json=payload, timeout=10)
        return True
    except Exception:
        return False
