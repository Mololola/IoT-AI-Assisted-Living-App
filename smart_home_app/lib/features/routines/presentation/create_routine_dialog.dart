import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/mock_data.dart';

class CreateRoutineDialog extends ConsumerStatefulWidget {
  const CreateRoutineDialog({super.key});

  @override
  ConsumerState<CreateRoutineDialog> createState() =>
      _CreateRoutineDialogState();
}

class _CreateRoutineDialogState extends ConsumerState<CreateRoutineDialog> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  String _scope = 'daily';
  DateTime _startTime = DateTime.now();
  DateTime _endTime = DateTime.now().add(const Duration(hours: 1));

  @override
  void dispose() {
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _selectDateTime(BuildContext context, bool isStart) async {
    final date = await showDatePicker(
      context: context,
      initialDate: isStart ? _startTime : _endTime,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );

    if (date != null && context.mounted) {
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(isStart ? _startTime : _endTime),
      );

      if (time != null) {
        final dateTime = DateTime(
          date.year,
          date.month,
          date.day,
          time.hour,
          time.minute,
        );

        setState(() {
          if (isStart) {
            _startTime = dateTime;
          } else {
            _endTime = dateTime;
          }
        });
      }
    }
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      if (_endTime.isBefore(_startTime)) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('End time must be after start time')),
        );
        return;
      }

      final routine = MockRoutine(
        id: DateTime.now().millisecondsSinceEpoch,
        scope: _scope,
        description: _descriptionController.text.trim(),
        startTime: _startTime,
        endTime: _endTime,
        createdAt: DateTime.now(),
      );

      ref.read(mockRoutinesProvider.notifier).addRoutine(routine);

      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Routine created successfully')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Dialog(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Icon(Icons.event_note, color: theme.colorScheme.primary),
                    const SizedBox(width: 12),
                    Text(
                      'Create New Routine',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                DropdownButtonFormField<String>(
                  value: _scope,
                  decoration: const InputDecoration(
                    labelText: 'Scope',
                    prefixIcon: Icon(Icons.category),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'daily', child: Text('Daily')),
                    DropdownMenuItem(value: 'weekly', child: Text('Weekly')),
                    DropdownMenuItem(value: 'monthly', child: Text('Monthly')),
                    DropdownMenuItem(value: 'custom', child: Text('Custom')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _scope = value!;
                    });
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    prefixIcon: Icon(Icons.description),
                    hintText: 'E.g., Turn on living room lights',
                  ),
                  maxLines: 2,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a description';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () => _selectDateTime(context, true),
                  borderRadius: BorderRadius.circular(8),
                  child: InputDecorator(
                    decoration: const InputDecoration(
                      labelText: 'Start Time',
                      prefixIcon: Icon(Icons.schedule),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${_startTime.year}-${_startTime.month.toString().padLeft(2, '0')}-${_startTime.day.toString().padLeft(2, '0')} ${_startTime.hour.toString().padLeft(2, '0')}:${_startTime.minute.toString().padLeft(2, '0')}',
                          style: theme.textTheme.bodyLarge,
                        ),
                        Icon(
                          Icons.edit,
                          size: 18,
                          color: theme.colorScheme.primary,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () => _selectDateTime(context, false),
                  borderRadius: BorderRadius.circular(8),
                  child: InputDecorator(
                    decoration: const InputDecoration(
                      labelText: 'End Time',
                      prefixIcon: Icon(Icons.schedule),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${_endTime.year}-${_endTime.month.toString().padLeft(2, '0')}-${_endTime.day.toString().padLeft(2, '0')} ${_endTime.hour.toString().padLeft(2, '0')}:${_endTime.minute.toString().padLeft(2, '0')}',
                          style: theme.textTheme.bodyLarge,
                        ),
                        Icon(
                          Icons.edit,
                          size: 18,
                          color: theme.colorScheme.primary,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: _submit,
                      child: const Text('Create'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
