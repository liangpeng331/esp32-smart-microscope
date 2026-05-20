import 'dart:async';
import 'package:flutter/material.dart';
import '../api/microscope_api.dart';
import '../models/models.dart';

class PresetsScreen extends StatefulWidget {
  final MicroscopeApi api;

  const PresetsScreen({super.key, required this.api});

  @override
  State<PresetsScreen> createState() => _PresetsScreenState();
}

class _PresetsScreenState extends State<PresetsScreen> {
  List<Preset> _presets = [];
  bool _loading = true;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadPresets();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => _loadPresets());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadPresets() async {
    try {
      final data = await widget.api.getPresets();
      if (!mounted) return;
      final list = (data['presets'] as List?)
          ?.map((p) => Preset.fromJson(p))
          .toList() ?? [];
      setState(() { _presets = list; _loading = false; });
    } catch (_) {}
  }

  Future<void> _savePreset({int? slot}) async {
    try {
      final result = await widget.api.savePreset(slot: slot);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已保存到槽位 ${result['slot']}')),
      );
      _loadPresets();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('保存失败: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _deletePreset(int slot) async {
    try {
      await widget.api.deletePreset(slot);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已删除槽位 $slot')),
      );
      _loadPresets();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('删除失败: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  void _showSaveDialog() {
    final slotCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('保存当前位置'),
        content: TextField(
          controller: slotCtrl,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            hintText: '留空自动分配槽位',
            labelText: '槽位编号 (0-5)',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          ElevatedButton(
            onPressed: () {
              final slot = int.tryParse(slotCtrl.text);
              Navigator.pop(ctx);
              _savePreset(slot: slot);
            },
            child: const Text('保存'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('预设点'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showSaveDialog,
            tooltip: '保存当前位置',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _presets.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.bookmark_border, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text('暂无预设点', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: _showSaveDialog,
                        icon: const Icon(Icons.add_location),
                        label: const Text('保存当前位置'),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _presets.length,
                  itemBuilder: (context, index) {
                    final p = _presets[index];
                    final pos = p.position;
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: Colors.blue.shade100,
                          child: Text('${p.slot}', style: TextStyle(color: Colors.blue.shade800)),
                        ),
                        title: Text('槽位 ${p.slot}'),
                        subtitle: Text('X=${pos['x']}  Y=${pos['y']}  Z=${pos['z']}'),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete_outline, color: Colors.red),
                          onPressed: () => _deletePreset(p.slot),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
