// FILE: lib/features/routines/data/routine_providers.dart
// Riverpod providers for routines - connects UI to repository layer
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'routine_repository.dart';
import '../domain/routine.dart';

/// Provider for routine repository
/// To switch to real API: change MockRoutineRepository → RemoteRoutineRepository
final routineRepositoryProvider = Provider<RoutineRepository>((ref) {
  return MockRoutineRepository(ref);
});

/// Controller for routine operations - exposes methods to UI
class RoutineController extends StateNotifier<AsyncValue<List<Routine>>> {
  final RoutineRepository _repository;

  RoutineController(this._repository) : super(const AsyncValue.loading()) {
    loadRoutines();
  }

  /// Load all routines from repository
  Future<void> loadRoutines() async {
    state = const AsyncValue.loading();
    try {
      final routines = await _repository.getRoutines();
      state = AsyncValue.data(routines);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  /// Add new routine through repository
  Future<void> addRoutine(Routine routine) async {
    try {
      await _repository.addRoutine(routine);
      // Reload to get updated list
      await loadRoutines();
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}

/// Provider that UI watches for routine list and operations
final routineListProvider =
    StateNotifierProvider<RoutineController, AsyncValue<List<Routine>>>((ref) {
      final repository = ref.watch(routineRepositoryProvider);
      return RoutineController(repository);
    });
