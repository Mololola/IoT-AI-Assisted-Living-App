import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../data/mock_data.dart';
import 'create_routine_dialog.dart';

class RoutinesTab extends ConsumerWidget {
  const RoutinesTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routines = ref.watch(mockRoutinesProvider);
    final theme = Theme.of(context);

    return Scaffold(
      body: routines.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.event_note,
                    size: 64,
                    color: theme.colorScheme.outline,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No routines created',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tap the + button to create your first routine',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.outline,
                    ),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: routines.length,
              itemBuilder: (context, index) {
                final routine = routines[index];
                final dateFormat = DateFormat('MMM d, y HH:mm');

                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            routine.scope.toUpperCase(),
                            style: theme.textTheme.labelSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: theme.colorScheme.onPrimaryContainer,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          routine.description,
                          style: theme.textTheme.bodyLarge?.copyWith(
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Icon(
                              Icons.schedule,
                              size: 16,
                              color: theme.colorScheme.outline,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              '${dateFormat.format(routine.startTime)} - ${dateFormat.format(routine.endTime)}',
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
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          showDialog(
            context: context,
            builder: (context) => const CreateRoutineDialog(),
          );
        },
        icon: const Icon(Icons.add),
        label: const Text('New Routine'),
      ),
    );
  }
}
