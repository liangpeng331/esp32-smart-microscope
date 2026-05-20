import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/microscope_api.dart';

class ConnectionScreen extends StatefulWidget {
  final MicroscopeApi? api;
  final void Function(MicroscopeApi api)? onConnected;

  const ConnectionScreen({super.key, this.api, this.onConnected});

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final _hostCtrl = TextEditingController(text: '192.168.4.1');
  final _portCtrl = TextEditingController(text: '80');
  bool _connecting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSaved();
  }

  Future<void> _loadSaved() async {
    final prefs = await SharedPreferences.getInstance();
    final host = prefs.getString('microscope_host');
    if (host != null && mounted) {
      setState(() => _hostCtrl.text = host);
    }
  }

  Future<void> _connect() async {
    setState(() { _connecting = true; _error = null; });

    final host = _hostCtrl.text.trim();
    final port = int.tryParse(_portCtrl.text.trim()) ?? 80;
    final url = 'http://$host${port == 80 ? '' : ':$port'}';

    try {
      final api = MicroscopeApi(url);
      final ok = await api.ping();
      if (!mounted) return;

      if (ok) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('microscope_host', host);
        widget.onConnected?.call(api);
      } else {
        setState(() => _error = '无法连接到显微镜');
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _connecting = false);
    }
  }

  @override
  void dispose() {
    _hostCtrl.dispose();
    _portCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.biotech, size: 80, color: Colors.blue),
              const SizedBox(height: 16),
              Text(
                '智能显微镜',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                '3-Axis Digital Microscope',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
              ),
              const SizedBox(height: 40),
              TextField(
                controller: _hostCtrl,
                decoration: const InputDecoration(
                  labelText: '显微镜 IP 地址',
                  hintText: '192.168.4.1',
                  prefixIcon: Icon(Icons.router),
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _portCtrl,
                decoration: const InputDecoration(
                  labelText: '端口',
                  hintText: '80',
                  prefixIcon: Icon(Icons.settings_ethernet),
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _connecting ? null : _connect,
                  child: _connecting
                      ? const SizedBox(
                          width: 20, height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('连接显微镜', style: TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                '请先连接显微镜的 WiFi 热点\nMicroscope / 12345678',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
