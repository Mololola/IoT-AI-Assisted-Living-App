// FILE: lib/features/routines/data/routine_providers.dart
// Riverpod providers for routines — wired to the real /exceptions backend.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../sensors/data/sensor_providers.dart'; // for apiClientProvider
import 'routine_repository.dart';
import '../domain/routine.dart';

/// Pick Mock or Remote repository based on config flag.
/// AppConfig.useRemoteBackend is currently true, so RemoteRoutineRepository is used.
final routineRepositoryProvider = Provider<RoutineRepository>((ref) {
  if (AppConfig.useRemoteBackend) {
    final apiClient = ref.watch(apiClientProvider);
    return RemoteRoutineRepository(apiClient);
  }
  return MockRoutineRepository();
});

/// Controller that the UI calls for all routine operations.
class RoutineController extends StateNotifier<AsyncValue<List<Routine>>> {
  final RoutineRepository _repository;

  RoutineController(this._repository) : super(const AsyncValue.loading()) {
    loadRoutines();
  }

  Future<void> loadRoutines() async {
    state = const AsyncValue.loading();
    try {
      final routines = await _repository.getRoutines();
      state = AsyncValue.data(routines);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> addRoutine({
    required String date,
    required String startTime,
    required String endTime,
    required String description,
    required String type,
  }) async {
    try {
      await _repository.addRoutine(
        date: date,
        startTime: startTime,
        endTime: endTime,
        description: description,
        type: type,
      );
      await loadRoutines(); // Refresh list after adding
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  /// Deletes the exception from the backend.
  /// The Pi will resume normal alerting on its next poll (within 15 real seconds).
  Future<void> deleteRoutine(String id) async {
    try {
      await _repository.deleteRoutine(id);
      await loadRoutines(); // Refresh list after deleting
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}

final routineListProvider =
    StateNotifierProvider<RoutineController, AsyncValue<List<Routine>>>((ref) {
      final repository = ref.watch(routineRepositoryProvider);
      return RoutineController(repository);
    });
