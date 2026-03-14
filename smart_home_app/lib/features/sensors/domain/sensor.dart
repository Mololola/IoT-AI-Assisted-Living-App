// FILE: lib/features/sensors/domain/sensor.dart

class Sensor {
  final String id;
  final String type;
  final String room;
  final double value;
  final String unit;
  final DateTime lastUpdated;

  Sensor({
    required this.id,
    required this.type,
    required this.room,
    required this.value,
    required this.unit,
    required this.lastUpdated,
  });

  /// Parse from the backend /sensor-readings response.
  factory Sensor.fromBackendJson(Map<String, dynamic> json) {
    final sensorType = (json['sensor_type'] ?? 'unknown').toString();
    final topic = (json['topic'] ?? '').toString();
    final sensorId = (json['sensor_id'] ?? '').toString();

    // Derive room from topic if available, otherwise fall back to sensor_id
    String room = 'Unknown';
    if (topic.isNotEmpty) {
      room = _roomFromTopic(topic);
    } else if (sensorId.isNotEmpty) {
      room = _roomFromSensorId(sensorId);
    }

    return Sensor(
      id: (json['_id'] ?? json['id'] ?? '').toString(),
      type: sensorType,
      room: room,
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      unit: (json['unit'] as String?) ?? _defaultUnit(sensorType),
      lastUpdated: _parseTimestamp(json['timestamp'], json['created_at']),
    );
  }

  /// Original fromJson for mock data compatibility
  factory Sensor.fromJson(Map<String, dynamic> json) {
    return Sensor(
      id: json['id'] as String,
      type: json['type'] as String,
      room: json['room'] as String,
      value: (json['value'] as num).toDouble(),
      unit: json['unit'] as String,
      lastUpdated: DateTime.parse(json['lastUpdated'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'room': room,
      'value': value,
      'unit': unit,
      'lastUpdated': lastUpdated.toIso8601String(),
    };
  }

  // ── Static helpers ──────────────────────────────────────────

  /// Extract room from MQTT topic: "home/bedroom/pressure" → "Bedroom"
  static String _roomFromTopic(String topic) {
    final parts = topic.split('/');
    if (parts.length >= 2) {
      final room = parts[1];
      return room[0].toUpperCase() + room.substring(1);
    }
    return 'Unknown';
  }

  /// Fallback: extract room from sensor_id: "bedroom_pressure_01" → "Bedroom"
  static String _roomFromSensorId(String sensorId) {
    final parts = sensorId.split('_');
    if (parts.isNotEmpty && parts[0].isNotEmpty) {
      final room = parts[0];
      return room[0].toUpperCase() + room.substring(1);
    }
    return 'Unknown';
  }

  /// Default unit per sensor type
  static String _defaultUnit(String sensorType) {
    switch (sensorType.toLowerCase()) {
      case 'pressure':
        return '';
      case 'pir':
        return '';
      case 'presence':
        return 'cm';
      case 'temperature':
        return '°C';
      case 'humidity':
        return '%';
      case 'sink':
        return '';
      default:
        return '';
    }
  }

  /// Parse timestamp from Unix float or ISO string
  static DateTime _parseTimestamp(dynamic unixTs, dynamic isoString) {
    if (unixTs != null && unixTs is num) {
      return DateTime.fromMillisecondsSinceEpoch(
        (unixTs * 1000).toInt(),
        isUtc: true,
      ).toLocal();
    }
    if (isoString != null && isoString is String) {
      return DateTime.tryParse(isoString)?.toLocal() ?? DateTime.now();
    }
    return DateTime.now();
  }

  // ── Display helpers ─────────────────────────────────────────

  /// Human-readable sensor name
  String get displayName {
    switch (type.toLowerCase()) {
      case 'pressure':
        return 'Bed Pressure';
      case 'pir':
        return 'Motion (PIR)';
      case 'presence':
        return 'Presence (mmWave)';
      case 'light':
        return 'Light';
      case 'sink':
        return 'Sink Flow';
      case 'temperature':
        return 'Temperature';
      case 'humidity':
        return 'Humidity';
      default:
        return type;
    }
  }

  /// Human-readable value string
  String get displayValue {
    switch (type.toLowerCase()) {
      case 'pir':
        return value > 0.5 ? 'Motion detected' : 'No motion';
      case 'pressure':
        return value > 500
            ? 'Occupied (${value.toStringAsFixed(0)})'
            : 'Empty (${value.toStringAsFixed(0)})';
      case 'presence':
        return value > 0
            ? 'Detected at ${value.toStringAsFixed(0)} cm'
            : 'Not detected';
      case 'light':
        return value > 0.5 ? 'Day' : 'Night';
      case 'sink':
        return value > 0 ? 'Flowing (${value.toStringAsFixed(1)})' : 'Off';
      case 'temperature':
        return '${value.toStringAsFixed(1)} °C';
      case 'humidity':
        return '${value.toStringAsFixed(1)} %';
      default:
        return unit.isNotEmpty
            ? '${value.toStringAsFixed(1)} $unit'
            : value.toStringAsFixed(1);
    }
  }
}
