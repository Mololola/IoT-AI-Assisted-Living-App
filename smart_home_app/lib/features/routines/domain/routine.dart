// FILE: lib/features/routines/domain/routine.dart
// Domain model for Routine — maps to the /exceptions endpoint on the backend.
// An "exception" tells the Pi to suppress alerts during a specific time window.
// Example: "Birthday party — resident out 10:00–22:00" → no false alarms.

class Routine {
  final String id; // MongoDB _id returned by the API
  final String date; // "YYYY-MM-DD"
  final String startTime; // "HH:MM" — compared against Pi's simulated clock
  final String endTime; // "HH:MM"
  final String type; // e.g. "away_from_home"
  final String description; // Human-readable label shown in the app
  final String createdBy; // "caregiver"
  final DateTime? createdAt;

  Routine({
    required this.id,
    required this.date,
    required this.startTime,
    required this.endTime,
    required this.description,
    this.type = 'away_from_home',
    this.createdBy = 'caregiver',
    this.createdAt,
  });

  /// Parse from backend GET /exceptions response.
  /// Backend returns:
  /// {
  ///   "id": "...",
  ///   "date": "2026-03-15",
  ///   "start_time": "10:00",
  ///   "end_time": "22:00",
  ///   "type": "away_from_home",
  ///   "description": "Birthday party",
  ///   "created_by": "caregiver"
  /// }
  factory Routine.fromJson(Map<String, dynamic> json) {
    return Routine(
      id: (json['id'] ?? json['_id'] ?? '').toString(),
      date: (json['date'] ?? '').toString(),
      startTime: (json['start_time'] ?? '').toString(),
      endTime: (json['end_time'] ?? '').toString(),
      type: (json['type'] ?? 'away_from_home').toString(),
      description: (json['description'] ?? '').toString(),
      createdBy: (json['created_by'] ?? 'caregiver').toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'date': date,
      'start_time': startTime,
      'end_time': endTime,
      'type': type,
      'description': description,
      'created_by': createdBy,
    };
  }

  /// Human-friendly label for the exception type
  String get typeLabel {
    switch (type) {
      case 'away_from_home':
        return 'Away from home';
      case 'visitor':
        return 'Visitor staying';
      case 'hospital':
        return 'Hospital visit';
      case 'other':
        return 'Other';
      default:
        return type;
    }
  }
}
