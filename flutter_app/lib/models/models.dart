class SystemStatus {
  final String state;
  final Position position;
  final int presets;

  SystemStatus({required this.state, required this.position, required this.presets});

  factory SystemStatus.fromJson(Map<String, dynamic> json) {
    return SystemStatus(
      state: json['state'] ?? 'UNKNOWN',
      position: Position.fromJson(json['position'] ?? {}),
      presets: json['presets'] ?? 0,
    );
  }

  bool get isIdle => state == 'IDLE';
  bool get isMoving => state == 'MOVING';
  bool get isHoming => state == 'HOMING';
  bool get isError => state == 'ERROR';
}

class Position {
  final int x;
  final int y;
  final int z;

  Position({required this.x, required this.y, required this.z});

  factory Position.fromJson(Map<String, dynamic> json) {
    return Position(
      x: (json['x'] ?? 0).toInt(),
      y: (json['y'] ?? 0).toInt(),
      z: (json['z'] ?? 0).toInt(),
    );
  }

  Position copyWith({int? x, int? y, int? z}) =>
      Position(x: x ?? this.x, y: y ?? this.y, z: z ?? this.z);
}

class LedState {
  final int brightness;
  final bool on;

  LedState({required this.brightness, required this.on});

  factory LedState.fromJson(Map<String, dynamic> json) {
    return LedState(
      brightness: (json['brightness'] ?? 0).toInt(),
      on: json['on'] ?? false,
    );
  }
}

class Preset {
  final int slot;
  final Map<String, dynamic> position;

  Preset({required this.slot, required this.position});

  factory Preset.fromJson(Map<String, dynamic> json) {
    return Preset(
      slot: json['slot'] ?? 0,
      position: Map<String, dynamic>.from(json['position'] ?? {}),
    );
  }

  String get posStr {
    final p = position;
    return 'X=${p['x']} Y=${p['y']} Z=${p['z']}';
  }
}

class CameraState {
  final bool initialized;
  final int width;
  final int height;
  final String format;
  final int fps;
  final bool previewing;

  CameraState({
    required this.initialized,
    required this.width,
    required this.height,
    required this.format,
    required this.fps,
    required this.previewing,
  });

  factory CameraState.fromJson(Map<String, dynamic> json) {
    return CameraState(
      initialized: json['initialized'] ?? false,
      width: (json['width'] ?? 0).toInt(),
      height: (json['height'] ?? 0).toInt(),
      format: json['format'] ?? '',
      fps: (json['fps'] ?? 0).toInt(),
      previewing: json['previewing'] ?? false,
    );
  }
}

class FileInfo {
  final String name;
  final int size;
  final bool isDir;

  FileInfo({required this.name, required this.size, required this.isDir});

  factory FileInfo.fromJson(Map<String, dynamic> json) {
    return FileInfo(
      name: json['name'] ?? '',
      size: (json['size'] ?? 0).toInt(),
      isDir: json['is_dir'] ?? false,
    );
  }

  String get sizeStr {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
