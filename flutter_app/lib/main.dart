import 'package:flutter/material.dart';
import 'api/microscope_api.dart';
import 'screens/connection_screen.dart';
import 'screens/control_screen.dart';
import 'screens/camera_screen.dart';
import 'screens/presets_screen.dart';
import 'screens/files_screen.dart';

void main() {
  runApp(const MicroscopeApp());
}

class MicroscopeApp extends StatelessWidget {
  const MicroscopeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '智能显微镜',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  MicroscopeApi? _api;
  int _currentTab = 0;

  void _onConnected(MicroscopeApi api) {
    setState(() => _api = api);
  }

  void _disconnect() {
    setState(() { _api = null; _currentTab = 0; });
  }

  @override
  Widget build(BuildContext context) {
    if (_api == null) {
      return ConnectionScreen(api: _api, onConnected: _onConnected);
    }

    final screens = [
      ControlScreen(api: _api!),
      CameraScreen(api: _api!),
      PresetsScreen(api: _api!),
      FilesScreen(api: _api!),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _currentTab,
        children: screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentTab,
        onDestinationSelected: (i) => setState(() => _currentTab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.gamepad), label: '控制'),
          NavigationDestination(icon: Icon(Icons.videocam), label: '摄像头'),
          NavigationDestination(icon: Icon(Icons.bookmark), label: '预设'),
          NavigationDestination(icon: Icon(Icons.folder), label: '文件'),
        ],
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(color: Colors.blue.shade700),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Icon(Icons.biotech, color: Colors.white, size: 48),
                  SizedBox(height: 8),
                  Text('智能显微镜 v1.2.0',
                       style: TextStyle(color: Colors.white, fontSize: 18)),
                  Text('3-Axis Digital Microscope',
                       style: TextStyle(color: Colors.white70, fontSize: 12)),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.router),
              title: const Text('重新连接'),
              onTap: _disconnect,
            ),
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: Text('已连接: ${_api!.baseUrl}'),
            ),
            const Divider(),
            const ListTile(
              leading: Icon(Icons.lightbulb_outline),
              title: Text('提示：输入 "xiaotian"'),
              subtitle: Text('唤醒后说中文语音指令'),
            ),
          ],
        ),
      ),
    );
  }
}
