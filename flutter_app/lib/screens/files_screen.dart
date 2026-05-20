import 'dart:async';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import '../api/microscope_api.dart';
import '../models/models.dart';

class FilesScreen extends StatefulWidget {
  final MicroscopeApi api;

  const FilesScreen({super.key, required this.api});

  @override
  State<FilesScreen> createState() => _FilesScreenState();
}

class _FilesScreenState extends State<FilesScreen> {
  List<FileInfo> _files = [];
  bool _loading = true;
  Set<String> _downloading = {};
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadFiles();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) => _loadFiles());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadFiles() async {
    try {
      final data = await widget.api.getFiles();
      if (!mounted) return;
      final list = (data['files'] as List?)
          ?.map((f) => FileInfo.fromJson(f))
          .toList() ?? [];
      setState(() { _files = list; _loading = false; });
    } catch (_) {}
  }

  Future<void> _download(FileInfo file) async {
    setState(() => _downloading.add(file.name));
    try {
      final url = widget.api.downloadUrl(file.name);
      final response = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        final dir = await getApplicationDocumentsDirectory();
        final localFile = File('${dir.path}/${file.name}');
        await localFile.writeAsBytes(response.bodyBytes);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已下载: ${file.name} (${file.sizeStr})')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('下载失败: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _downloading.remove(file.name));
    }
  }

  Future<void> _deleteFile(FileInfo file) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除 ${file.name} 吗？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirm != true) return;
    try {
      await widget.api.deleteFile(file.name);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已删除: ${file.name}')),
      );
      _loadFiles();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('删除失败: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final photos = _files.where((f) => !f.isDir && f.name.endsWith('.jpg')).toList();
    return Scaffold(
      appBar: AppBar(
        title: Text('SD 卡文件 (${photos.length} 张照片)'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadFiles),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : photos.isEmpty
              ? const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text('暂无照片', style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                )
              : GridView.builder(
                  padding: const EdgeInsets.all(8),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 8,
                    mainAxisSpacing: 8,
                    childAspectRatio: 1.0,
                  ),
                  itemCount: photos.length,
                  itemBuilder: (context, index) {
                    final file = photos[index];
                    final downloading = _downloading.contains(file.name);
                    return Card(
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.image, size: 48, color: Colors.blueGrey),
                              const SizedBox(height: 8),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 4),
                                child: Text(
                                  file.name,
                                  style: const TextStyle(fontSize: 11),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  textAlign: TextAlign.center,
                                ),
                              ),
                              Text(file.sizeStr, style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
                            ],
                          ),
                          Positioned(
                            right: 0, top: 0,
                            child: PopupMenuButton<String>(
                              itemBuilder: (_) => [
                                const PopupMenuItem(value: 'download', child: Text('下载')),
                                const PopupMenuItem(value: 'delete', child: Text('删除', style: TextStyle(color: Colors.red))),
                              ],
                              onSelected: (action) {
                                if (action == 'download') _download(file);
                                if (action == 'delete') _deleteFile(file);
                              },
                            ),
                          ),
                          if (downloading)
                            Container(
                              color: Colors.black38,
                              child: const Center(child: CircularProgressIndicator(color: Colors.white)),
                            ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
