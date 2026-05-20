import 'dart:async';
import 'package:flutter/material.dart';
import '../api/microscope_api.dart';
import '../models/models.dart';
import '../widgets/mjpeg_viewer.dart';

class CameraScreen extends StatefulWidget {
  final MicroscopeApi api;

  const CameraScreen({super.key, required this.api});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraState? _camera;
  bool _streaming = false;
  bool _capturing = false;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _pollCamera();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) => _pollCamera());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _pollCamera() async {
    try {
      final data = await widget.api.getCamera();
      if (!mounted) return;
      setState(() => _camera = CameraState.fromJson(data));
    } catch (_) {}
  }

  Future<void> _capture() async {
    setState(() => _capturing = true);
    try {
      final result = await widget.api.capture();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('照片已保存: ${result['file'] ?? 'ok'}')),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('拍照失败: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _capturing = false);
    }
  }

  void _toggleStream() {
    setState(() => _streaming = !_streaming);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('摄像头')),
      body: Column(
        children: [
          // 视频区域
          Expanded(
            flex: 3,
            child: _streaming
                ? MjpegViewer(url: widget.api.streamUrl, playing: true)
                : Container(
                    color: Colors.black,
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.videocam_off, color: Colors.white54, size: 64),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: _toggleStream,
                            icon: const Icon(Icons.play_arrow),
                            label: const Text('开启实时取景'),
                          ),
                        ],
                      ),
                    ),
                  ),
          ),

          // 控制栏
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              border: Border(top: BorderSide(color: Colors.grey.shade300)),
            ),
            child: Row(
              children: [
                // 拍照按钮
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _capturing ? null : _capture,
                    icon: _capturing
                        ? const SizedBox(width: 18, height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.camera),
                    label: const Text('拍照'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // 取景开关
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _toggleStream,
                    icon: Icon(_streaming ? Icons.stop : Icons.play_arrow),
                    label: Text(_streaming ? '停止取景' : '实时取景'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // 状态信息
          if (_camera != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _infoChip('分辨率', '${_camera!.width}×${_camera!.height}'),
                  _infoChip('格式', _camera!.format),
                  _infoChip('帧率', '${_camera!.fps} FPS'),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _infoChip(String label, String value) {
    return Chip(
      label: Text('$label: $value', style: const TextStyle(fontSize: 12)),
      backgroundColor: Colors.grey.shade200,
    );
  }
}
