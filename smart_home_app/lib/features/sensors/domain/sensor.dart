// FILE: lib/features/sensors/domain/sensor.dart
// Domain model for Sensor — now maps to both:
//   1. The /sensor-readings/latest backend response (remote)
//   2. The old mock data format (for fallback)

class Sensor {
  final String id;
  final String type; // "pressure", "PIR", "presence"
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
  /// Backend returns:
  /// {
  ///   "_id": "...",
  ///   "sensor_type": "pressure",
  ///   "topic": "home/bedroom/pressure",
  ///   "value": 0.45,
  ///   "timestamp": 1707200000.0,
  ///   "unit": "bar",
  ///   "created_at": "2026-02-05T..."
  /// }
  factory Sensor.fromBackendJson(Map<String, dynamic> json) {
    final sensorType = json['sensor_type'] as String? ?? 'unknown';
    final topic = json['topic'] as String? ?? '';

    return Sensor(
      id: json['_id'] as String? ?? '',
      type: sensorType,
      room: _roomFromTopic(topic),
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      unit: json['unit'] as String? ?? _defaultUnit(sensorType),
      lastUpdated: _parseTimestamp(json['timestamp'], json['created_at']),
    );
  }

  /// Original fromJson for local/mock data compatibility
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

  /// Extract room name from MQTT topic.
  /// "home/bedroom/pressure" → "Bedroom"
  static String _roomFromTopic(String topic) {
    final parts = topic.split('/');
    if (parts.length >= 2) {
      final room = parts[1];
      return room[0].toUpperCase() + room.substring(1);
    }
    return 'Unknown';
  }

  /// Default unit based on sensor type
  static String _defaultUnit(String sensorType) {
    switch (sensorType.toLowerCase()) {
      case 'pressure':
        return 'bar';
      case 'pir':
        return ''; // boolean-like (0 or 1)
      case 'presence':
        return 'cm';
      case 'temperature':
        return '°C';
      case 'humidity':
        return '%';
      default:
        return '';
    }
  }

  /// Parse timestamp from either Unix float or ISO string
  static DateTime _parseTimestamp(dynamic unixTs, dynamic isoString) {
    if (unixTs != null && unixTs is num) {
      return DateTime.fromMillisecondsSinceEpoch(
        (unixTs * 1000).toInt(),
        isUtc: true,
      ).toLocal();
    }
    if (isoString != null && isoString is String) {
      return DateTime.parse(isoString).toLocal();
    }
    return DateTime.now();
  }

  /// Friendly display name for the sensor type
  String get displayName {
    switch (type.toLowerCase()) {
      case 'pressure':
        return 'Bed Pressure';
      case 'pir':
        return 'Motion (PIR)';
      case 'presence':
        return 'Presence (mmWave)';
      case 'temperature':
        return 'Temperature';
      case 'humidity':
        return 'Humidity';
      default:
        return type;
    }
  }

  /// Friendly formatted value string
  String get displayValue {
    switch (type.toLowerCase()) {
      case 'pir':
        return value > 0.5 ? 'Motion detected' : 'No motion';
      case 'pressure':
        return value > 0.3
            ? 'Occupied (${value.toStringAsFixed(2)} $unit)'
            : 'Empty (${value.toStringAsFixed(2)} $unit)';
      case 'presence':
        return value > 0
            ? 'Detected at ${value.toStringAsFixed(0)} $unit'
            : 'Not detected';
      default:
        return '${value.toStringAsFixed(1)} $unit';
    }
  }
}
