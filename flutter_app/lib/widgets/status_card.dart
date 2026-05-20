import 'package:flutter/material.dart';
import '../models/models.dart';

/// 系统状态显示卡片。
class StatusCard extends StatelessWidget {
  final SystemStatus? status;
  final bool connected;

  const StatusCard({super.key, this.status, required this.connected});

  Color _stateColor(String state) {
    switch (state) {
      case 'IDLE':    return Colors.green;
      case 'MOVING':  return Colors.orange;
      case 'HOMING':  return Colors.blue;
      case 'ERROR':   return Colors.red;
      default:        return Colors.grey;
    }
  }

  String _stateLabel(String state) {
    switch (state) {
      case 'IDLE':   return '就绪';
      case 'MOVING': return '移动中';
      case 'HOMING': return '回零中';
      case 'ERROR':  return '错误';
      default:       return state;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 10, height: 10,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: connected ? Colors.green : Colors.red,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  connected ? '已连接' : '未连接',
                  style: TextStyle(
                    color: connected ? Colors.green : Colors.red,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (status != null) ...[
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: _stateColor(status!.state).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      _stateLabel(status!.state),
                      style: TextStyle(
                        color: _stateColor(status!.state),
                        fontSize: 12, fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            if (status != null) ...[
              const Divider(height: 16),
              _posRow('X', status!.position.x, 'μm'),
              _posRow('Y', status!.position.y, 'μm'),
              _posRow('Z', status!.position.z, 'μm'),
              const SizedBox(height: 4),
              Text(
                '预设点: ${status!.presets}',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _posRow(String axis, int value, String unit) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Row(
        children: [
          SizedBox(width: 16, child: Text(axis, style: const TextStyle(fontWeight: FontWeight.bold))),
          Expanded(
            child: LinearProgressIndicator(
              value: (value + 10000) / 20000,
              color: Colors.blue.shade300,
              backgroundColor: Colors.grey.shade200,
              minHeight: 6,
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 80,
            child: Text('$value $unit', style: const TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
