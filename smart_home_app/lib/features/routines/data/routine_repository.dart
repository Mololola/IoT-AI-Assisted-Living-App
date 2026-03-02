// FILE: lib/features/routines/data/routine_repository.dart
// Repository pattern for routines - abstraction layer for routine operations
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/routine.dart';

/// Abstract repository interface for routines
/// Defines operations: read all routines, add new routine
abstract class RoutineRepository {
  Future<List<Routine>> getRoutines();
  Future<void> addRoutine(Routine routine);
}

/// Mock implementation using StateNotifier for in-memory storage
/// In production, RemoteRoutineRepository would call FastAPI backend
class MockRoutineRepository implements RoutineRepository {
  final Ref ref;

  MockRoutineRepository(this.ref);

  @override
  Future<List<Routine>> getRoutines() async {
    // In mock mode, routines are stored in a StateNotifier provider
    return ref.read(_mockRoutinesStateProvider);
  }

  @override
  Future<void> addRoutine(Routine routine) async {
    // Simulate API call delay
    await Future.delayed(const Duration(milliseconds: 300));

    // Add to in-memory state
    ref.read(_mockRoutinesStateProvider.notifier).addRoutine(routine);
  }
}

/// Internal StateNotifier for mock routine storage
/// This mimics a local cache that would sync with backend in production
class _MockRoutinesNotifier extends StateNotifier<List<Routine>> {
  _MockRoutinesNotifier() : super([]) {
    // Initialize with default routine
    state = [
      Routine(
        id: 1,
        scope: 'daily',
        description: 'Turn on lights at sunset',
        startTime: DateTime.now(),
        endTime: DateTime.now().add(const Duration(hours: 1)),
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
    ];
  }

  void addRoutine(Routine routine) {
    state = [...state, routine];
  }
}

/// Private provider for mock storage - only accessed through repository
final _mockRoutinesStateProvider =
    StateNotifierProvider<_MockRoutinesNotifier, List<Routine>>((ref) {
      return _MockRoutinesNotifier();
    });
