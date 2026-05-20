import 'dart:async';
import 'package:flutter/material.dart';

/// Z 轴对焦控制按钮组。
class ZButtons extends StatefulWidget {
  final void Function(int dz)? onMove;
  final VoidCallback? onStop;
  final VoidCallback? onAutofocus;
  final int stepSize;

  const ZButtons({
    super.key,
    this.onMove,
    this.onStop,
    this.onAutofocus,
    this.stepSize = 50,
  });

  @override
  State<ZButtons> createState() => _ZButtonsState();
}

class _ZButtonsState extends State<ZButtons> {
  int _dz = 0;
  Timer? _repeat;

  void _start(int dz) {
    _dz = dz;
    widget.onMove?.call(dz * widget.stepSize);
    _repeat?.cancel();
    _repeat = Timer.periodic(const Duration(milliseconds: 150), (_) {
      widget.onMove?.call(dz * widget.stepSize);
    });
  }

  void _stop() {
    _dz = 0;
    _repeat?.cancel();
    widget.onStop?.call();
  }

  @override
  void dispose() {
    _repeat?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        GestureDetector(
          onTapDown: (_) => _start(1),
          onTapUp: (_) => _stop(),
          onTapCancel: _stop,
          child: Container(
            width: 64, height: 48,
            decoration: BoxDecoration(
              color: _dz == 1 ? Colors.teal.shade700 : Colors.teal.shade200,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.expand_less, color: Colors.white, size: 32),
          ),
        ),
        const SizedBox(height: 8),
        Text('Z 对焦', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
        if (widget.onAutofocus != null) ...[
          const SizedBox(height: 8),
          SizedBox(
            height: 36,
            child: OutlinedButton.icon(
              onPressed: widget.onAutofocus,
              icon: const Icon(Icons.center_focus_strong, size: 18),
              label: const Text('AF', style: TextStyle(fontSize: 13)),
            ),
          ),
        ],
        const SizedBox(height: 8),
        GestureDetector(
          onTapDown: (_) => _start(-1),
          onTapUp: (_) => _stop(),
          onTapCancel: _stop,
          child: Container(
            width: 64, height: 48,
            decoration: BoxDecoration(
              color: _dz == -1 ? Colors.teal.shade700 : Colors.teal.shade200,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.expand_more, color: Colors.white, size: 32),
          ),
        ),
      ],
    );
  }
}
