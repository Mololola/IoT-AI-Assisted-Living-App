import 'package:flutter_riverpod/flutter_riverpod.dart';

// Mock Sensor Data
class MockSensor {
  final String id;
  final String type;
  final String room;
  final double value;
  final String unit;
  final DateTime lastUpdated;

  MockSensor({
    required this.id,
    required this.type,
    required this.room,
    required this.value,
    required this.unit,
    required this.lastUpdated,
  });
}

// Mock Routine Data
class MockRoutine {
  final int id;
  final String scope;
  final String description;
  final DateTime startTime;
  final DateTime endTime;
  final DateTime createdAt;

  MockRoutine({
    required this.id,
    required this.scope,
    required this.description,
    required this.startTime,
    required this.endTime,
    required this.createdAt,
  });
}

// Provider with mock sensors
final mockSensorsProvider = Provider<List<MockSensor>>((ref) {
  return [
    MockSensor(
      id: 'temp_001',
      type: 'temperature',
      room: 'Living Room',
      value: 22.5,
      unit: '°C',
      lastUpdated: DateTime.now().subtract(const Duration(minutes: 2)),
    ),
    MockSensor(
      id: 'hum_001',
      type: 'humidity',
      room: 'Bedroom',
      value: 65.0,
      unit: '%',
      lastUpdated: DateTime.now().subtract(const Duration(minutes: 5)),
    ),
    MockSensor(
      id: 'light_001',
      type: 'light',
      room: 'Kitchen',
      value: 450.0,
      unit: 'lux',
      lastUpdated: DateTime.now().subtract(const Duration(minutes: 1)),
    ),
  ];
});

// Routines state notifier
class RoutinesNotifier extends StateNotifier<List<MockRoutine>> {
  RoutinesNotifier() : super(_initialRoutines);

  static final List<MockRoutine> _initialRoutines = [
    MockRoutine(
      id: 1,
      scope: 'daily',
      description: 'Turn on lights at sunset',
      startTime: DateTime.now(),
      endTime: DateTime.now().add(const Duration(hours: 1)),
      createdAt: DateTime.now().subtract(const Duration(days: 1)),
    ),
  ];

  void addRoutine(MockRoutine routine) {
    state = [...state, routine];
  }
}

// Provider for routines
final mockRoutinesProvider =
    StateNotifierProvider<RoutinesNotifier, List<MockRoutine>>((ref) {
      return RoutinesNotifier();
    });
