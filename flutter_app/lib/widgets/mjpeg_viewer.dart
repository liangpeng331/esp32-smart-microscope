import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

/// MJPEG 实时视频流组件。
///
/// 从显微镜 HTTP 服务器获取 `/api/camera/stream` 的 multipart 流，
/// 解析每一帧 JPEG 并显示。
class MjpegViewer extends StatefulWidget {
  final String url;
  final bool playing;

  const MjpegViewer({super.key, required this.url, this.playing = true});

  @override
  State<MjpegViewer> createState() => _MjpegViewerState();
}

class _MjpegViewerState extends State<MjpegViewer> {
  http.Client? _client;
  StreamSubscription<Uint8List>? _sub;
  Uint8List? _currentFrame;
  String? _error;
  int _frameCount = 0;
  String _boundary = 'FRAME';

  @override
  void initState() {
    super.initState();
    if (widget.playing) _connect();
  }

  @override
  void didUpdateWidget(MjpegViewer old) {
    super.didUpdateWidget(old);
    if (widget.playing != old.playing || widget.url != old.url) {
      if (widget.playing) {
        _connect();
      } else {
        _disconnect();
      }
    }
  }

  void _connect() {
    _disconnect();
    _error = null;
    _client = http.Client();

    final request = http.Request('GET', Uri.parse(widget.url));
    _client!.send(request).then((response) {
      if (response.statusCode != 200) {
        setState(() => _error = 'HTTP ${response.statusCode}');
        return;
      }
      _parseStream(response.stream);
    }).catchError((e) {
      setState(() => _error = '连接失败: $e');
    });
  }

  void _parseStream(http.ByteStream stream) {
    var buffer = <int>[];
    _sub = stream.listen(
      (chunk) {
        buffer.addAll(chunk);
        _tryExtractFrame(buffer);
      },
      onError: (e) => setState(() => _error = '流错误: $e'),
      onDone: () => setState(() => _error ??= '流结束'),
      cancelOnError: false,
    );
  }

  void _tryExtractFrame(List<int> buffer) {
    final boundaryBytes = utf8.encode('--$_boundary');
    while (true) {
      final boundaryIdx = _indexOf(buffer, boundaryBytes);
      if (boundaryIdx == -1) return;

      // 找下一个边界
      final nextIdx = _indexOf(buffer, boundaryBytes, boundaryIdx + boundaryBytes.length);
      if (nextIdx == -1) return;

      final part = buffer.sublist(boundaryIdx, nextIdx);
      buffer.removeRange(0, nextIdx);

      // 找到 JPEG 数据起始位置 (\r\n\r\n)
      final headerEnd = _doubleCrlf(part);
      if (headerEnd == -1) continue;

      final jpegBytes = part.sublist(headerEnd);
      // 去掉尾部 \r\n
      var end = jpegBytes.length;
      while (end > 0 && (jpegBytes[end - 1] == 10 || jpegBytes[end - 1] == 13)) {
        end--;
      }

      if (end > 100) {
        setState(() {
          _currentFrame = Uint8List.fromList(jpegBytes.sublist(0, end));
          _frameCount++;
        });
      }
    }
  }

  int _indexOf(List<int> data, List<int> pattern, [int start = 0]) {
    for (var i = start; i <= data.length - pattern.length; i++) {
      var match = true;
      for (var j = 0; j < pattern.length; j++) {
        if (data[i + j] != pattern[j]) {
          match = false;
          break;
        }
      }
      if (match) return i;
    }
    return -1;
  }

  int _doubleCrlf(List<int> data) {
    for (var i = 0; i < data.length - 3; i++) {
      if (data[i] == 13 && data[i + 1] == 10 && data[i + 2] == 13 && data[i + 3] == 10) {
        return i + 4;
      }
    }
    return -1;
  }

  void _disconnect() {
    _sub?.cancel();
    _sub = null;
    _client?.close();
    _client = null;
  }

  @override
  void dispose() {
    _disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Container(
        color: Colors.black,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red, size: 48),
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.red)),
              const SizedBox(height: 8),
              ElevatedButton(onPressed: _connect, child: const Text('重试')),
            ],
          ),
        ),
      );
    }

    if (_currentFrame != null) {
      return Stack(
        fit: StackFit.expand,
        children: [
          Image.memory(_currentFrame!, fit: BoxFit.contain, gaplessPlayback: true),
          Positioned(
            top: 8, right: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '$_frameCount 帧',
                style: const TextStyle(color: Colors.white, fontSize: 11),
              ),
            ),
          ),
        ],
      );
    }

    return Container(
      color: Colors.black,
      child: const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 12),
            Text('等待视频流...', style: TextStyle(color: Colors.white70)),
          ],
        ),
      ),
    );
  }
}
