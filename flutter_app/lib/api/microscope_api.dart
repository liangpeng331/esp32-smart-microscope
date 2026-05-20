import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class MicroscopeApi {
  final String baseUrl;
  final Duration timeout;

  MicroscopeApi(this.baseUrl, {this.timeout = const Duration(seconds: 5)});

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> _get(String path) async {
    final r = await http.get(_uri(path)).timeout(timeout);
    if (r.statusCode == 200) return json.decode(r.body);
    throw ApiException(r.statusCode, r.body);
  }

  Future<Map<String, dynamic>> _post(String path, [Map<String, dynamic>? body]) async {
    final r = await http
        .post(_uri(path),
            headers: {'Content-Type': 'application/json'},
            body: body != null ? json.encode(body) : null)
        .timeout(timeout);
    if (r.statusCode == 200 || r.statusCode == 201) {
      return r.body.isNotEmpty ? json.decode(r.body) : {};
    }
    throw ApiException(r.statusCode, r.body);
  }

  // ---- 状态 ----
  Future<Map<String, dynamic>> getStatus() => _get('/api/status');

  // ---- 移动 ----
  Future<Map<String, dynamic>> moveRel({int dx = 0, int dy = 0, int dz = 0}) =>
      _post('/api/move', {'rel': true, 'dx': dx, 'dy': dy, 'dz': dz});

  Future<Map<String, dynamic>> moveTo({int? x, int? y, int? z}) =>
      _post('/api/move', {'x': x, 'y': y, 'z': z});

  Future<Map<String, dynamic>> home() => _post('/api/home');

  // ---- LED ----
  Future<Map<String, dynamic>> getLed() => _get('/api/led');

  Future<Map<String, dynamic>> setLedBrightness(int pct) =>
      _post('/api/led', {'brightness': pct});

  Future<Map<String, dynamic>> setLedPreset(String preset) =>
      _post('/api/led', {'preset': preset});

  Future<Map<String, dynamic>> setLedOn(bool on) =>
      _post('/api/led', {'on': on});

  // ---- 摄像头 ----
  Future<Map<String, dynamic>> getCamera() => _get('/api/camera');

  Future<Map<String, dynamic>> capture() => _post('/api/camera/capture');

  Future<Map<String, dynamic>> setPreview(bool enable) =>
      _post('/api/camera/preview', {'enable': enable});

  String get streamUrl => '$baseUrl/api/camera/stream';

  // ---- 预设点 ----
  Future<Map<String, dynamic>> getPresets() => _get('/api/presets');

  Future<Map<String, dynamic>> savePreset({int? slot}) =>
      _post('/api/presets', {'slot': slot});

  Future<Map<String, dynamic>> deletePreset(int slot) async {
    final r = await http.delete(_uri('/api/presets/$slot')).timeout(timeout);
    if (r.statusCode == 200) return json.decode(r.body);
    throw ApiException(r.statusCode, r.body);
  }

  // ---- 自动曝光 ----
  Future<Map<String, dynamic>> getAutoExposure() => _get('/api/autoexposure');

  Future<Map<String, dynamic>> setAutoExposure(bool enable) =>
      _post('/api/autoexposure', {'enable': enable});

  // ---- 文件管理 ----
  Future<Map<String, dynamic>> getFiles() => _get('/api/files');

  String downloadUrl(String filename) =>
      '$baseUrl/api/files/download/${Uri.encodeComponent(filename)}';

  Future<Map<String, dynamic>> deleteFile(String filename) async {
    final r = await http
        .delete(_uri('/api/files/delete/${Uri.encodeComponent(filename)}'))
        .timeout(timeout);
    if (r.statusCode == 200) return json.decode(r.body);
    throw ApiException(r.statusCode, r.body);
  }

  // ---- 连接测试 ----
  Future<bool> ping() async {
    try {
      await getStatus();
      return true;
    } catch (_) {
      return false;
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  ApiException(this.statusCode, this.body);

  @override
  String toString() => 'API $statusCode: $body';
}
