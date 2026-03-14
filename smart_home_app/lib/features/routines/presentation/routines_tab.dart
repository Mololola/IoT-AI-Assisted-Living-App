// FILE: lib/features/routines/presentation/routines_tab.dart
// Displays active exceptions (routines) fetched from the backend.
// Each card shows the date, time window, and reason.
// Deleting a card calls DELETE /exceptions/{id} — the Pi resumes alerting
// on its next poll cycle (within 15 real seconds).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/routine_providers.dart';
import '../domain/routine.dart';
import 'create_routine_dialog.dart';

class RoutinesTab extends ConsumerWidget {
  const RoutinesTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routinesAsync = ref.watch(routineListProvider);
    final theme = Theme.of(context);

    return Scaffold(
      body: routinesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.error_outline,
                  size: 64,
                  color: theme.colorScheme.error,
                ),
                const SizedBox(height: 16),
                Text(
                  'Error loading exceptions',
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  error.toString(),
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: () =>
                      ref.read(routineListProvider.notifier).loadRoutines(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
        data: (routines) => routines.isEmpty
            ? _EmptyState(theme: theme)
            : RefreshIndicator(
                onRefresh: () =>
                    ref.read(routineListProvider.notifier).loadRoutines(),
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: routines.length,
                  itemBuilder: (context, index) => _RoutineCard(
                    routine: routines[index],
                    onDelete: () =>
                        _confirmDelete(context, ref, routines[index]),
                  ),
                ),
              ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showDialog(
          context: context,
          builder: (_) => const CreateRoutineDialog(),
        ),
        icon: const Icon(Icons.add),
        label: const Text('New Exception'),
      ),
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    Routine routine,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Exception'),
        content: Text(
          'Delete "${routine.description}"?\n\nThe sensor system will resume normal alerting within 15 seconds.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(routineListProvider.notifier).deleteRoutine(routine.id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Exception deleted — alerts resumed')),
        );
      }
    }
  }
}

// ────────────────────── Routine card ──────────────────────

class _RoutineCard extends StatelessWidget {
  final Routine routine;
  final VoidCallback onDelete;

  const _RoutineCard({required this.routine, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Type badge + delete button ──
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.tertiaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    routine.typeLabel.toUpperCase(),
                    style: theme.textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onTertiaryContainer,
                    ),
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: Icon(
                    Icons.delete_outline,
                    color: theme.colorScheme.error,
                  ),
                  tooltip: 'Delete exception',
                  onPressed: onDelete,
                ),
              ],
            ),
            const SizedBox(height: 10),

            // ── Description ──
            Text(
              routine.description,
              style: theme.textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),

            // ── Date ──
            Row(
              children: [
                Icon(
                  Icons.calendar_today_outlined,
                  size: 15,
                  color: theme.colorScheme.outline,
                ),
                const SizedBox(width: 6),
                Text(
                  routine.date,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),

            // ── Time window ──
            Row(
              children: [
                Icon(
                  Icons.schedule_outlined,
                  size: 15,
                  color: theme.colorScheme.outline,
                ),
                const SizedBox(width: 6),
                Text(
                  '${routine.startTime} → ${routine.endTime}  (alerts suppressed)',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ────────────────────── Empty state ──────────────────────

class _EmptyState extends StatelessWidget {
  final ThemeData theme;
  const _EmptyState({required this.theme});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.event_available,
              size: 64,
              color: theme.colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text('No exceptions set', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              'Create an exception when the resident is away or has a visitor — alerts will be suppressed automatically.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
