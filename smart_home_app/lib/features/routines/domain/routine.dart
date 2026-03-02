// FILE: lib/features/routines/domain/routine.dart
// Domain model for Routine - represents a routine entity independent of data source
class Routine {
  final int id;
  final String scope;
  final String description;
  final DateTime startTime;
  final DateTime endTime;
  final DateTime createdAt;

  Routine({
    required this.id,
    required this.scope,
    required this.description,
    required this.startTime,
    required this.endTime,
    required this.createdAt,
  });

  // For future API integration
  factory Routine.fromJson(Map<String, dynamic> json) {
    return Routine(
      id: json['id'] as int,
      scope: json['scope'] as String,
      description: json['description'] as String,
      startTime: DateTime.parse(json['startTime'] as String),
      endTime: DateTime.parse(json['endTime'] as String),
      createdAt: DateTime.parse(json['createdAt'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'scope': scope,
      'description': description,
      'startTime': startTime.toIso8601String(),
      'endTime': endTime.toIso8601String(),
      'createdAt': createdAt.toIso8601String(),
    };
  }
}
