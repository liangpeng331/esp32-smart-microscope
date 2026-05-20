import 'package:flutter/material.dart';

/// LED 亮度滑块 + 预设按钮。
class LedSlider extends StatelessWidget {
  final int brightness;
  final bool on;
  final ValueChanged<int>? onBrightnessChanged;
  final VoidCallback? onToggle;
  final ValueChanged<String>? onPreset;

  static const presets = ['暗', '中', '亮', '最亮'];

  const LedSlider({
    super.key,
    required this.brightness,
    required this.on,
    this.onBrightnessChanged,
    this.onToggle,
    this.onPreset,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.lightbulb, color: on ? Colors.amber : Colors.grey),
            const SizedBox(width: 8),
            Text('LED 照明', style: Theme.of(context).textTheme.titleSmall),
            const Spacer(),
            Switch(
              value: on,
              onChanged: (_) => onToggle?.call(),
              activeTrackColor: Colors.amber,
            ),
          ],
        ),
        Row(
          children: [
            Expanded(
              child: Slider(
                value: brightness.toDouble(),
                min: 0, max: 100, divisions: 20,
                label: '$brightness%',
                activeColor: on ? Colors.amber : Colors.grey,
                onChanged: (v) => onBrightnessChanged?.call(v.round()),
              ),
            ),
            SizedBox(
              width: 48,
              child: Text('$brightness%', style: const TextStyle(fontSize: 14)),
            ),
          ],
        ),
        Wrap(
          spacing: 8,
          children: presets.map((p) => ActionChip(
            label: Text(p, style: const TextStyle(fontSize: 13)),
            onPressed: () => onPreset?.call(p),
          )).toList(),
        ),
      ],
    );
  }
}
