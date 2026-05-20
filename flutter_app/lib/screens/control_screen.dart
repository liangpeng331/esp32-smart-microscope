import 'dart:async';
import 'package:flutter/material.dart';
import '../api/microscope_api.dart';
import '../models/models.dart';
import '../widgets/joystick.dart';
import '../widgets/z_buttons.dart';
import '../widgets/led_slider.dart';
import '../widgets/status_card.dart';

class ControlScreen extends StatefulWidget {
  final MicroscopeApi api;

  const ControlScreen({super.key, required this.api});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  SystemStatus? _status;
  LedState? _led;
  Timer? _pollTimer;
  bool _previewing = false;

  @override
  void initState() {
    super.initState();
    _poll();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _poll());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final s = await widget.api.getStatus();
      if (!mounted) return;
      setState(() => _status = SystemStatus.fromJson(s));
    } catch (_) {}

    try {
      final l = await widget.api.getLed();
      if (!mounted) return;
      setState(() => _led = LedState.fromJson(l));
    } catch (_) {}
  }

  Future<void> _moveRel(int dx, int dy) async {
    try {
      await widget.api.moveRel(dx: dx, dy: dy);
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _moveZ(int dz) async {
    try {
      await widget.api.moveRel(dz: dz);
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _doHome() async {
    try {
      await widget.api.home();
      await _poll();
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _setBrightness(int pct) async {
    try {
      await widget.api.setLedBrightness(pct);
      _led = LedState.fromJson(await widget.api.getLed());
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _toggleLed() async {
    try {
      final newOn = !(_led?.on ?? false);
      await widget.api.setLedOn(newOn);
      _led = LedState.fromJson(await widget.api.getLed());
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _setPreset(String p) async {
    try {
      await widget.api.setLedPreset(p);
      _led = LedState.fromJson(await widget.api.getLed());
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _capture() async {
    try {
      final result = await widget.api.capture();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('拍照成功: ${result['file'] ?? 'ok'}')),
      );
    } catch (e) {
      if (mounted) _showError(e);
    }
  }

  Future<void> _togglePreview() async {
    try {
      _previewing = !_previewing;
      await widget.api.setPreview(_previewing);
      setState(() {});
    } catch (e) {
      _previewing = !_previewing;
      if (mounted) _showError(e);
    }
  }

  void _showError(Object e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('错误: $e'), backgroundColor: Colors.red),
    );
  }

  String _formatPos(int value) => '${(value / 1000).toStringAsFixed(2)} mm';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('显微镜控制'),
        actions: [
          IconButton(icon: const Icon(Icons.home), onPressed: _doHome, tooltip: '回零'),
          IconButton(icon: const Icon(Icons.camera_alt), onPressed: _capture, tooltip: '拍照'),
          IconButton(
            icon: Icon(_previewing ? Icons.videocam : Icons.videocam_off),
            onPressed: _togglePreview,
            tooltip: '实时取景',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            // 状态卡片
            StatusCard(
              status: _status,
              connected: _status != null,
            ),
            const SizedBox(height: 12),

            // 位置显示
            if (_status != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      Text('载物台位置', style: Theme.of(context).textTheme.titleSmall),
                      const SizedBox(height: 8),
                      Text('X: ${_formatPos(_status!.position.x)}  Y: ${_formatPos(_status!.position.y)}  Z: ${_formatPos(_status!.position.z)}'),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),

            // XY 摇杆 + Z 按钮
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(
                  child: Center(
                    child: StageJoystick(
                      stepSize: 100,
                      onMove: _moveRel,
                    ),
                  ),
                ),
                ZButtons(
                  stepSize: 50,
                  onMove: _moveZ,
                  onAutofocus: () => _moveZ(0), // placeholder
                ),
              ],
            ),
            const SizedBox(height: 12),

            // LED 控制
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: LedSlider(
                  brightness: _led?.brightness ?? 0,
                  on: _led?.on ?? false,
                  onBrightnessChanged: _setBrightness,
                  onToggle: _toggleLed,
                  onPreset: _setPreset,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
