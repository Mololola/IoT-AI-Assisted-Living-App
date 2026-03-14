// FILE: lib/features/alerts/domain/alert.dart
// Domain model for Alert — matches the ACTUAL backend response format.
// Backend returns:
// {
//   "id": "69a31fe40c1f8ab60f6b3b72",
//   "alert_id": "RULE_BATHROOM_TOO_LONG_...",
//   "timestamp": "2026-02-28T11:03:34.636655",
//   "rule_type": "BATHROOM_TOO_LONG",
//   "severity": "HIGH",
//   "message": "Person in bathroom for 52 minutes...",
//   "sensor_data": {...},
//   "recommended_action": "Check on resident immediately",
//   "acknowledged": true,
//   "acknowledged_at": "2026-02-28T17:03:44.419000",
//   "created_at": "2026-02-28T17:03:32.658000"
// }

class Alert {
  final String id;
  final String alertId;
  final DateTime timestamp;
  final String ruleType;
  final String severity;
  final String message;
  final Map<String, dynamic> sensorData;
  final String? recommendedAction;
  final bool acknowledged;
  final DateTime? acknowledgedAt;
  final String? acknowledgedBy;

  Alert({
    required this.id,
    required this.alertId,
    required this.timestamp,
    required this.ruleType,
    required this.severity,
    required this.message,
    required this.sensorData,
    this.recommendedAction,
    this.acknowledged = false,
    this.acknowledgedAt,
    this.acknowledgedBy,
  });

  /// Parse from the actual backend JSON response
  factory Alert.fromBackendJson(Map<String, dynamic> json) {
    return Alert(
      // Backend uses "id" (not "_id")
      id: (json['id'] ?? json['_id'] ?? '').toString(),
      alertId: (json['alert_id'] ?? '').toString(),
      timestamp: _parseTimestamp(json['timestamp']),
      ruleType: (json['rule_type'] ?? 'unknown').toString(),
      severity: (json['severity'] ?? 'INFO').toString(),
      message: (json['message'] ?? '').toString(),
      sensorData: json['sensor_data'] is Map<String, dynamic>
          ? json['sensor_data'] as Map<String, dynamic>
          : {},
      recommendedAction: json['recommended_action']?.toString(),
      acknowledged: json['acknowledged'] == true,
      acknowledgedAt: json['acknowledged_at'] != null
          ? DateTime.tryParse(json['acknowledged_at'].toString())
          : null,
      acknowledgedBy: json['acknowledged_by']?.toString(),
    );
  }

  /// Parse timestamp — handles both ISO string and Unix float
  static DateTime _parseTimestamp(dynamic ts) {
    if (ts == null) return DateTime.now();
    if (ts is String) {
      return DateTime.tryParse(ts)?.toLocal() ?? DateTime.now();
    }
    if (ts is num) {
      return DateTime.fromMillisecondsSinceEpoch(
        (ts * 1000).toInt(),
        isUtc: true,
      ).toLocal();
    }
    return DateTime.now();
  }

  bool get isUrgent => severity == 'HIGH';

  String get displayRuleType {
    final clean = ruleType.replaceAll('_', ' ');
    // Capitalize each word
    return clean
        .split(' ')
        .map((word) {
          if (word.isEmpty) return word;
          return word[0].toUpperCase() + word.substring(1).toLowerCase();
        })
        .join(' ');
  }

  String get iconName {
    final type = ruleType.toLowerCase();
    if (type.contains('fall')) return 'warning';
    if (type.contains('wander')) return 'directions_walk';
    if (type.contains('bed')) return 'bed';
    if (type.contains('sleep')) return 'bedtime';
    if (type.contains('sensor')) return 'sensors';
    if (type.contains('bathroom')) return 'bathroom';
    if (type.contains('kitchen') || type.contains('meal')) return 'kitchen';
    if (type.contains('inactivity') || type.contains('no_activity')) {
      return 'accessibility';
    }
    if (type.contains('water')) return 'water_drop';
    if (type.contains('summary') || type.contains('daily')) return 'summarize';
    if (type.contains('ml_')) return 'psychology';
    return 'notification_important';
  }
}
