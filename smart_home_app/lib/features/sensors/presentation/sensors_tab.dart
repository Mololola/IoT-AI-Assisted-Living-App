import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../data/mock_data.dart';

class SensorsTab extends ConsumerWidget {
  const SensorsTab({super.key});

  IconData _getSensorIcon(String sensorType) {
    switch (sensorType.toLowerCase()) {
      case 'temperature':
        return Icons.thermostat;
      case 'humidity':
        return Icons.water_drop;
      case 'light':
        return Icons.lightbulb;
      case 'motion':
        return Icons.sensors;
      default:
        return Icons.device_unknown;
    }
  }

  Color _getSensorColor(String sensorType) {
    switch (sensorType.toLowerCase()) {
      case 'temperature':
        return Colors.orange;
      case 'humidity':
        return Colors.blue;
      case 'light':
        return Colors.amber;
      case 'motion':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sensors = ref.watch(mockSensorsProvider);
    final theme = Theme.of(context);
    final dateFormat = DateFormat('MMM d, y HH:mm:ss');

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sensors.length,
      itemBuilder: (context, index) {
        final sensor = sensors[index];
        final icon = _getSensorIcon(sensor.type);
        final color = _getSensorColor(sensor.type);

        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: color, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        sensor.room,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        sensor.type.toUpperCase(),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(
                            Icons.access_time,
                            size: 14,
                            color: theme.colorScheme.outline,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            dateFormat.format(sensor.lastUpdated),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.outline,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      sensor.value.toStringAsFixed(1),
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                    ),
                    Text(
                      sensor.unit,
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
    );
  }
}
