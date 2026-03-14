// FILE: lib/features/routines/data/routine_repository.dart
// Repository for routines — backed by the /exceptions API endpoint.
// Creating a routine tells the Pi to suppress alerts in that time window.
// Deleting a routine resumes normal alerting on the next Pi poll (≤15s).

import '../domain/routine.dart';
import '../../../core/data/api_client.dart';

abstract class RoutineRepository {
  Future<List<Routine>> getRoutines();
  Future<void> addRoutine({
    required String date,
    required String startTime,
    required String endTime,
    required String description,
    required String type,
  });
  Future<void> deleteRoutine(String id);
}

// ────────────────────── REMOTE (real backend) ──────────────────────

class RemoteRoutineRepository implements RoutineRepository {
  final ApiClient _apiClient;

  RemoteRoutineRepository(this._apiClient);

  @override
  Future<List<Routine>> getRoutines() async {
    try {
      final jsonList = await _apiClient.fetchExceptions();
      return jsonList.map((json) => Routine.fromJson(json)).toList();
    } on ApiException catch (e) {
      if (e.isNotFound) return [];
      rethrow;
    }
  }

  @override
  Future<void> addRoutine({
    required String date,
    required String startTime,
    required String endTime,
    required String description,
    required String type,
  }) async {
    await _apiClient.createException(
      date: date,
      startTime: startTime,
      endTime: endTime,
      description: description,
      type: type,
    );
  }

  @override
  Future<void> deleteRoutine(String id) async {
    await _apiClient.deleteException(id);
  }
}

// ────────────────────── MOCK (for testing without backend) ──────────────────────

class MockRoutineRepository implements RoutineRepository {
  final List<Routine> _routines = [
    Routine(
      id: 'mock_1',
      date: '2026-03-15',
      startTime: '10:00',
      endTime: '22:00',
      description: 'Birthday party — resident out all day',
      type: 'away_from_home',
    ),
  ];

  @override
  Future<List<Routine>> getRoutines() async {
    await Future.delayed(const Duration(milliseconds: 300));
    return List.from(_routines);
  }

  @override
  Future<void> addRoutine({
    required String date,
    required String startTime,
    required String endTime,
    required String description,
    required String type,
  }) async {
    await Future.delayed(const Duration(milliseconds: 300));
    _routines.add(
      Routine(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        date: date,
        startTime: startTime,
        endTime: endTime,
        description: description,
        type: type,
      ),
    );
  }

  @override
  Future<void> deleteRoutine(String id) async {
    await Future.delayed(const Duration(milliseconds: 300));
    _routines.removeWhere((r) => r.id == id);
  }
}
