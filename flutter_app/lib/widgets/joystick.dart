import 'dart:async';
import 'package:flutter/material.dart';

/// XY 四方向摇杆控件，适合显微镜载物台操控。
/// 支持按下移动（可调速）和松开停止两种模式。
class StageJoystick extends StatefulWidget {
  final void Function(int dx, int dy)? onMove;
  final VoidCallback? onStop;
  final int stepSize;

  const StageJoystick({
    super.key,
    this.onMove,
    this.onStop,
    this.stepSize = 100,
  });

  @override
  State<StageJoystick> createState() => _StageJoystickState();
}

class _StageJoystickState extends State<StageJoystick> {
  int _dx = 0;
  int _dy = 0;
  Timer? _repeatTimer;

  void _startMove(int dx, int dy) {
    _dx = dx;
    _dy = dy;
    widget.onMove?.call(dx * widget.stepSize, dy * widget.stepSize);
    _repeatTimer?.cancel();
    _repeatTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      widget.onMove?.call(dx * widget.stepSize, dy * widget.stepSize);
    });
  }

  void _stopMove() {
    _dx = 0;
    _dy = 0;
    _repeatTimer?.cancel();
    widget.onStop?.call();
  }

  @override
  void dispose() {
    _repeatTimer?.cancel();
    super.dispose();
  }

  Widget _arrowBtn(String label, IconData icon, int dx, int dy, Alignment align) {
    final active = (_dx == dx && _dy == dy);
    return GestureDetector(
      onTapDown: (_) => _startMove(dx, dy),
      onTapUp: (_) => _stopMove(),
      onTapCancel: _stopMove,
      child: Container(
        width: 64, height: 64,
        alignment: align,
        decoration: BoxDecoration(
          color: active ? Colors.blue.shade700 : Colors.blue.shade200,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 28),
            if (label.isNotEmpty) Text(label, style: const TextStyle(color: Colors.white, fontSize: 10)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _arrowBtn('Y+', Icons.keyboard_arrow_up, 0, 1, Alignment.center),
        const SizedBox(height: 4),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _arrowBtn('X−', Icons.keyboard_arrow_left, -1, 0, Alignment.center),
            const SizedBox(width: 4),
            Container(
              width: 64, height: 64,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(child: Icon(Icons.home, color: Colors.grey)),
            ),
            const SizedBox(width: 4),
            _arrowBtn('X+', Icons.keyboard_arrow_right, 1, 0, Alignment.center),
          ],
        ),
        const SizedBox(height: 4),
        _arrowBtn('Y−', Icons.keyboard_arrow_down, 0, -1, Alignment.center),
      ],
    );
  }
}
