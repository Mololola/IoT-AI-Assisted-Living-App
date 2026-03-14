// FILE: lib/features/sensors/presentation/sensors_tab.dart
// Shows all sensors grouped by room.
// Each sensor card matches Álvaro's 14 sensor types with correct
// icons, labels, and human-readable values.
// Tapping a card opens a history screen with a line chart and
// three period filters: Last 7 days / Last 30 days / Last 90 days.

import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../data/sensor_providers.dart';
import '../domain/sensor.dart';

// ═══════════════════════════════════════════════════════════════
// MAIN TAB
// ═══════════════════════════════════════════════════════════════

class SensorsTab extends ConsumerWidget {
  const SensorsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sensorsAsync = ref.watch(sensorListProvider);
    final theme = Theme.of(context);

    return sensorsAsync.when(
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
              Text('Error loading sensors', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                error.toString(),
                style: theme.textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => ref.invalidate(sensorListProvider),
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
      data: (sensors) {
        if (sensors.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.sensors_off,
                  size: 64,
                  color: theme.colorScheme.outline,
                ),
                const SizedBox(height: 16),
                Text('No sensor data yet', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  'Sensors will appear here once the Pi starts sending readings.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          );
        }

        // Group sensors by room, preserving order:
        // Bedroom → Bathroom → Living room → Kitchen → Hallway → other
        final roomOrder = [
          'Bedroom',
          'Bathroom',
          'Livingroom',
          'Kitchen',
          'Hallway',
        ];
        final grouped = <String, List<Sensor>>{};
        for (final s in sensors) {
          grouped.putIfAbsent(s.room, () => []).add(s);
        }

        final orderedRooms = [
          ...roomOrder.where((r) => grouped.containsKey(r)),
          ...grouped.keys.where((r) => !roomOrder.contains(r)),
        ];

        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(sensorListProvider),
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: orderedRooms.length,
            itemBuilder: (context, i) {
              final room = orderedRooms[i];
              final roomSensors = grouped[room]!;
              return _RoomSection(room: room, sensors: roomSensors);
            },
          ),
        );
      },
    );
  }
}

// ═══════════════════════════════════════════════════════════════
// ROOM SECTION — header + sensor cards
// ═══════════════════════════════════════════════════════════════

class _RoomSection extends StatelessWidget {
  final String room;
  final List<Sensor> sensors;

  const _RoomSection({required this.room, required this.sensors});

  IconData _roomIcon(String room) {
    switch (room.toLowerCase()) {
      case 'bedroom':
        return Icons.bed_outlined;
      case 'bathroom':
        return Icons.shower_outlined;
      case 'livingroom':
        return Icons.weekend_outlined;
      case 'kitchen':
        return Icons.kitchen_outlined;
      case 'hallway':
        return Icons.meeting_room_outlined;
      default:
        return Icons.home_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Room header
        Padding(
          padding: const EdgeInsets.only(top: 8, bottom: 10),
          child: Row(
            children: [
              Icon(_roomIcon(room), size: 20, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                room,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(child: Divider(color: theme.colorScheme.outlineVariant)),
            ],
          ),
        ),
        // Sensor cards
        ...sensors.map((s) => _SensorCard(sensor: s)),
        const SizedBox(height: 8),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════════
// SENSOR CARD
// ═══════════════════════════════════════════════════════════════

class _SensorCard extends StatelessWidget {
  final Sensor sensor;
  const _SensorCard({required this.sensor});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = SensorMeta.color(sensor.type);
    final timeAgo = _timeAgo(sensor.lastUpdated);
    final isStale =
        DateTime.now().difference(sensor.lastUpdated).inMinutes > 10;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => SensorHistoryScreen(sensor: sensor),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // Icon badge
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  SensorMeta.icon(sensor.type),
                  color: color,
                  size: 26,
                ),
              ),
              const SizedBox(width: 14),

              // Label + timestamp
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      sensor.displayName,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Icon(
                          isStale ? Icons.warning_amber_rounded : Icons.circle,
                          size: 8,
                          color: isStale ? Colors.orange : Colors.green,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          timeAgo,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.outline,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Value + chevron
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    sensor.displayValue,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                    textAlign: TextAlign.end,
                  ),
                  const SizedBox(height: 2),
                  Icon(
                    Icons.chevron_right,
                    size: 18,
                    color: theme.colorScheme.outline,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _timeAgo(DateTime t) {
    final diff = DateTime.now().difference(t);
    if (diff.inSeconds < 60) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

// ═══════════════════════════════════════════════════════════════
// HISTORY SCREEN
// ═══════════════════════════════════════════════════════════════

class SensorHistoryScreen extends ConsumerStatefulWidget {
  final Sensor sensor;
  const SensorHistoryScreen({super.key, required this.sensor});

  @override
  ConsumerState<SensorHistoryScreen> createState() =>
      _SensorHistoryScreenState();
}

class _SensorHistoryScreenState extends ConsumerState<SensorHistoryScreen> {
  HistoryPeriod _period = HistoryPeriod.week;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = SensorMeta.color(widget.sensor.type);
    final historyAsync = ref.watch(
      sensorHistoryProvider((widget.sensor.type, _period)),
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.sensor.displayName),
        centerTitle: false,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Current value banner ──
          Container(
            width: double.infinity,
            color: color.withOpacity(0.08),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    SensorMeta.icon(widget.sensor.type),
                    color: color,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Current reading',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.outline,
                      ),
                    ),
                    Text(
                      widget.sensor.displayValue,
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                    ),
                    Text(
                      widget.sensor.room,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.outline,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // ── Period selector ──
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Row(
              children: HistoryPeriod.values.map((p) {
                final selected = p == _period;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(p.label),
                    selected: selected,
                    onSelected: (_) => setState(() => _period = p),
                  ),
                );
              }).toList(),
            ),
          ),

          const SizedBox(height: 8),

          // ── Chart area ──
          Expanded(
            child: historyAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 48,
                        color: theme.colorScheme.error,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Could not load history',
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        e.toString(),
                        style: theme.textTheme.bodySmall,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
              data: (readings) {
                if (readings.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.bar_chart,
                          size: 64,
                          color: theme.colorScheme.outline,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No data for this period',
                          style: theme.textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'The sensor hasn\'t sent readings in the last ${_period.days} days.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.outline,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: [
                    // Chart
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(8, 8, 16, 8),
                        child: _SensorLineChart(
                          readings: readings,
                          color: color,
                          sensorType: widget.sensor.type,
                        ),
                      ),
                    ),

                    // Stats strip
                    _StatsStrip(readings: readings, color: color),
                    const SizedBox(height: 16),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════
// LINE CHART (drawn with Canvas — no extra package needed)
// ═══════════════════════════════════════════════════════════════

class _SensorLineChart extends StatelessWidget {
  final List<Sensor> readings;
  final Color color;
  final String sensorType;

  const _SensorLineChart({
    required this.readings,
    required this.color,
    required this.sensorType,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return CustomPaint(
      painter: _LinePainter(
        readings: readings,
        lineColor: color,
        gridColor: theme.colorScheme.outlineVariant,
        labelColor: theme.colorScheme.onSurfaceVariant,
        sensorType: sensorType,
      ),
      child: const SizedBox.expand(),
    );
  }
}

class _LinePainter extends CustomPainter {
  final List<Sensor> readings;
  final Color lineColor;
  final Color gridColor;
  final Color labelColor;
  final String sensorType;

  _LinePainter({
    required this.readings,
    required this.lineColor,
    required this.gridColor,
    required this.labelColor,
    required this.sensorType,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (readings.length < 2) return;

    const leftPad = 52.0;
    const rightPad = 12.0;
    const topPad = 12.0;
    const bottomPad = 36.0;

    final chartW = size.width - leftPad - rightPad;
    final chartH = size.height - topPad - bottomPad;

    final values = readings.map((r) => r.value).toList();
    final minVal = values.reduce(math.min);
    final maxVal = values.reduce(math.max);
    final valRange = (maxVal - minVal) == 0 ? 1.0 : maxVal - minVal;

    final times = readings
        .map((r) => r.lastUpdated.millisecondsSinceEpoch.toDouble())
        .toList();
    final minT = times.first;
    final maxT = times.last;
    final tRange = (maxT - minT) == 0 ? 1.0 : maxT - minT;

    // ── Grid lines (5 horizontal) ──
    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 0.8;

    final labelPainterStyle = TextStyle(color: labelColor, fontSize: 10);

    for (int i = 0; i <= 4; i++) {
      final y = topPad + chartH * (1 - i / 4);
      canvas.drawLine(
        Offset(leftPad, y),
        Offset(leftPad + chartW, y),
        gridPaint,
      );

      // Y-axis label
      final labelVal = minVal + (valRange * i / 4);
      final tp = TextPainter(
        text: TextSpan(text: _formatYLabel(labelVal), style: labelPainterStyle),
        textDirection: ui.TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(leftPad - tp.width - 4, y - tp.height / 2));
    }

    // ── X-axis labels (3: start, mid, end) ──
    final dateFormat = DateFormat('d MMM');
    for (int i = 0; i <= 2; i++) {
      final t = DateTime.fromMillisecondsSinceEpoch(
        (minT + tRange * i / 2).toInt(),
      );
      final x = leftPad + chartW * i / 2;
      final tp = TextPainter(
        text: TextSpan(text: dateFormat.format(t), style: labelPainterStyle),
        textDirection: ui.TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(x - tp.width / 2, topPad + chartH + 6));
    }

    // ── Gradient fill under the line ──
    final points = List.generate(readings.length, (i) {
      final x = leftPad + chartW * (times[i] - minT) / tRange;
      final y = topPad + chartH * (1 - (values[i] - minVal) / valRange);
      return Offset(x, y);
    });

    final fillPath = Path()..moveTo(points.first.dx, topPad + chartH);
    for (final p in points) fillPath.lineTo(p.dx, p.dy);
    fillPath
      ..lineTo(points.last.dx, topPad + chartH)
      ..close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [lineColor.withOpacity(0.25), lineColor.withOpacity(0.02)],
      ).createShader(Rect.fromLTWH(leftPad, topPad, chartW, chartH));
    canvas.drawPath(fillPath, fillPaint);

    // ── Line ──
    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (int i = 1; i < points.length; i++) {
      linePath.lineTo(points[i].dx, points[i].dy);
    }
    canvas.drawPath(linePath, linePaint);

    // ── Dot on last point ──
    canvas.drawCircle(points.last, 4, Paint()..color = lineColor);
    canvas.drawCircle(
      points.last,
      4,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
  }

  String _formatYLabel(double v) {
    switch (sensorType.toLowerCase()) {
      case 'pressure':
        return v.toStringAsFixed(0);
      case 'presence':
        return '${v.toStringAsFixed(0)}cm';
      default:
        return v.toStringAsFixed(1);
    }
  }

  @override
  bool shouldRepaint(_LinePainter old) =>
      old.readings != readings || old.lineColor != lineColor;
}

// ═══════════════════════════════════════════════════════════════
// STATS STRIP — min / avg / max
// ═══════════════════════════════════════════════════════════════

class _StatsStrip extends StatelessWidget {
  final List<Sensor> readings;
  final Color color;

  const _StatsStrip({required this.readings, required this.color});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final values = readings.map((r) => r.value).toList();
    final min = values.reduce(math.min);
    final max = values.reduce(math.max);
    final avg = values.reduce((a, b) => a + b) / values.length;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _StatBox(
            label: 'Min',
            value: min.toStringAsFixed(1),
            color: color,
            theme: theme,
          ),
          const SizedBox(width: 8),
          _StatBox(
            label: 'Avg',
            value: avg.toStringAsFixed(1),
            color: color,
            theme: theme,
          ),
          const SizedBox(width: 8),
          _StatBox(
            label: 'Max',
            value: max.toStringAsFixed(1),
            color: color,
            theme: theme,
          ),
          const SizedBox(width: 8),
          _StatBox(
            label: 'Readings',
            value: readings.length.toString(),
            color: color,
            theme: theme,
          ),
        ],
      ),
    );
  }
}

class _StatBox extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  final ThemeData theme;

  const _StatBox({
    required this.label,
    required this.value,
    required this.color,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════
// SENSOR META — maps Álvaro's 14 sensor types to icons + colours
// ═══════════════════════════════════════════════════════════════

class SensorMeta {
  static IconData icon(String type) {
    switch (type.toLowerCase()) {
      case 'pressure':
        return Icons.bed_outlined;
      case 'pir':
        return Icons.directions_walk;
      case 'presence':
        return Icons.radar;
      case 'light':
        return Icons.wb_sunny_outlined;
      case 'sink':
        return Icons.water_drop_outlined;
      case 'temperature':
        return Icons.thermostat_outlined;
      case 'humidity':
        return Icons.opacity_outlined;
      default:
        return Icons.sensors;
    }
  }

  static Color color(String type) {
    switch (type.toLowerCase()) {
      case 'pressure':
        return Colors.indigo;
      case 'pir':
        return Colors.deepPurple;
      case 'presence':
        return Colors.teal;
      case 'light':
        return Colors.amber;
      case 'sink':
        return Colors.blue;
      case 'temperature':
        return Colors.orange;
      case 'humidity':
        return Colors.cyan;
      default:
        return Colors.blueGrey;
    }
  }
}
