// FILE: lib/features/analytics/presentation/analytics_screen.dart
// Full analytics dashboard for alert history.
// Shows: summary stats, alerts by type (bar), severity (pie),
// alerts over time (line), and average response time.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../alerts/domain/alert.dart';
import '../../sensors/data/sensor_providers.dart';
import '../../../core/data/api_client.dart';
import 'package:intl/intl.dart';
import 'dart:math' as math;

class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  List<Alert>? _alerts;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final apiClient = ref.read(apiClientProvider);
      final jsonList = await apiClient.fetchAllAlerts(limit: 500);
      setState(() {
        _alerts = jsonList.map((j) => Alert.fromBackendJson(j)).toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alert Analytics'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(child: Text('Error: $_error'))
          : _alerts == null || _alerts!.isEmpty
          ? const Center(child: Text('No alert data available'))
          : _buildDashboard(),
    );
  }

  Widget _buildDashboard() {
    final alerts = _alerts!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _SummaryStatsCard(alerts: alerts),
        const SizedBox(height: 16),
        _AlertsByTypeCard(alerts: alerts),
        const SizedBox(height: 16),
        _SeverityBreakdownCard(alerts: alerts),
        const SizedBox(height: 16),
        _AlertsOverTimeCard(alerts: alerts),
        const SizedBox(height: 16),
        _ResponseTimeCard(alerts: alerts),
        const SizedBox(height: 32),
      ],
    );
  }
}

// ────────────────────── 1. Summary Stats ──────────────────────

class _SummaryStatsCard extends StatelessWidget {
  final List<Alert> alerts;
  const _SummaryStatsCard({required this.alerts});

  @override
  Widget build(BuildContext context) {
    final total = alerts.length;
    final highCount = alerts.where((a) => a.severity == 'HIGH').length;
    final unacked = alerts.where((a) => !a.acknowledged).length;
    final ackedAlerts = alerts.where(
      (a) => a.acknowledged && a.acknowledgedAt != null,
    );

    // Most common alert type
    final typeCounts = <String, int>{};
    for (final a in alerts) {
      typeCounts[a.ruleType] = (typeCounts[a.ruleType] ?? 0) + 1;
    }
    final mostCommon = typeCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final mostCommonType = mostCommon.isNotEmpty
        ? mostCommon.first.key.replaceAll('_', ' ')
        : 'N/A';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Summary',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _StatTile(
                  label: 'Total Alerts',
                  value: '$total',
                  color: Colors.blue,
                ),
                _StatTile(
                  label: 'High Severity',
                  value: '$highCount',
                  color: Colors.red,
                ),
                _StatTile(
                  label: 'Pending',
                  value: '$unacked',
                  color: Colors.orange,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _StatTile(
                  label: 'Most Common',
                  value: mostCommonType.length > 15
                      ? '${mostCommonType.substring(0, 15)}...'
                      : mostCommonType,
                  color: Colors.purple,
                ),
                _StatTile(
                  label: 'Acknowledged',
                  value: '${ackedAlerts.length}',
                  color: Colors.green,
                ),
                _StatTile(
                  label: 'Ack Rate',
                  value: total > 0
                      ? '${(ackedAlerts.length / total * 100).toStringAsFixed(0)}%'
                      : 'N/A',
                  color: Colors.teal,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatTile({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(fontSize: 11, color: Colors.grey[600]),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ────────────────────── 2. Alerts by Type (Bar Chart) ──────────────────────

class _AlertsByTypeCard extends StatelessWidget {
  final List<Alert> alerts;
  const _AlertsByTypeCard({required this.alerts});

  @override
  Widget build(BuildContext context) {
    final typeCounts = <String, int>{};
    for (final a in alerts) {
      final displayType = a.displayRuleType;
      typeCounts[displayType] = (typeCounts[displayType] ?? 0) + 1;
    }
    final sorted = typeCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final maxCount = sorted.isNotEmpty ? sorted.first.value : 1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Alerts by Type',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            ...sorted
                .take(8)
                .map(
                  (entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Flexible(
                              child: Text(
                                entry.key,
                                style: const TextStyle(fontSize: 13),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            Text(
                              '${entry.value}',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: entry.value / maxCount,
                            minHeight: 8,
                            backgroundColor: Colors.grey[200],
                            valueColor: AlwaysStoppedAnimation(
                              _barColor(entry.key),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Color _barColor(String type) {
    final lower = type.toLowerCase();
    if (lower.contains('fall')) return Colors.red;
    if (lower.contains('wander')) return Colors.orange;
    if (lower.contains('bathroom')) return Colors.amber;
    if (lower.contains('inactivity') || lower.contains('no activity'))
      return Colors.red[300]!;
    if (lower.contains('kitchen') || lower.contains('water'))
      return Colors.blue;
    if (lower.contains('bed')) return Colors.purple;
    if (lower.contains('ml') || lower.contains('missed')) return Colors.teal;
    if (lower.contains('summary') || lower.contains('daily'))
      return Colors.grey;
    return Colors.indigo;
  }
}

// ────────────────────── 3. Severity Breakdown (Pie-like) ──────────────────────

class _SeverityBreakdownCard extends StatelessWidget {
  final List<Alert> alerts;
  const _SeverityBreakdownCard({required this.alerts});

  @override
  Widget build(BuildContext context) {
    final counts = {
      'HIGH': alerts.where((a) => a.severity == 'HIGH').length,
      'MEDIUM': alerts.where((a) => a.severity == 'MEDIUM').length,
      'LOW': alerts.where((a) => a.severity == 'LOW').length,
      'INFO': alerts.where((a) => a.severity == 'INFO').length,
    };
    final total = alerts.length;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Severity Breakdown',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),

            // Visual bar
            if (total > 0)
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  height: 32,
                  child: Row(
                    children: [
                      if (counts['HIGH']! > 0)
                        Expanded(
                          flex: counts['HIGH']!,
                          child: Container(color: Colors.red),
                        ),
                      if (counts['MEDIUM']! > 0)
                        Expanded(
                          flex: counts['MEDIUM']!,
                          child: Container(color: Colors.orange),
                        ),
                      if (counts['LOW']! > 0)
                        Expanded(
                          flex: counts['LOW']!,
                          child: Container(color: Colors.amber),
                        ),
                      if (counts['INFO']! > 0)
                        Expanded(
                          flex: counts['INFO']!,
                          child: Container(color: Colors.blue[300]),
                        ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 16),

            // Legend
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _SeverityLegend('HIGH', counts['HIGH']!, total, Colors.red),
                _SeverityLegend(
                  'MEDIUM',
                  counts['MEDIUM']!,
                  total,
                  Colors.orange,
                ),
                _SeverityLegend('LOW', counts['LOW']!, total, Colors.amber),
                _SeverityLegend(
                  'INFO',
                  counts['INFO']!,
                  total,
                  Colors.blue[300]!,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SeverityLegend extends StatelessWidget {
  final String label;
  final int count;
  final int total;
  final Color color;
  const _SeverityLegend(this.label, this.count, this.total, this.color);

  @override
  Widget build(BuildContext context) {
    final pct = total > 0 ? (count / total * 100).toStringAsFixed(0) : '0';
    return Column(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(height: 4),
        Text(
          '$count',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        Text(
          '$label ($pct%)',
          style: TextStyle(fontSize: 10, color: Colors.grey[600]),
        ),
      ],
    );
  }
}

// ────────────────────── 4. Alerts Over Time (Line-like) ──────────────────────

class _AlertsOverTimeCard extends StatelessWidget {
  final List<Alert> alerts;
  const _AlertsOverTimeCard({required this.alerts});

  @override
  Widget build(BuildContext context) {
    // Group alerts by day
    final dayCounts = <String, int>{};
    for (final a in alerts) {
      final dayKey = DateFormat('MMM d').format(a.timestamp);
      dayCounts[dayKey] = (dayCounts[dayKey] ?? 0) + 1;
    }

    // Sort by date and take last 14 days
    final sortedAlerts = List<Alert>.from(alerts)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    final dayEntries = <MapEntry<String, int>>[];
    final seen = <String>{};
    for (final a in sortedAlerts) {
      final dayKey = DateFormat('MMM d').format(a.timestamp);
      if (!seen.contains(dayKey)) {
        seen.add(dayKey);
        dayEntries.add(MapEntry(dayKey, dayCounts[dayKey]!));
      }
    }
    final recent = dayEntries.length > 14
        ? dayEntries.sublist(dayEntries.length - 14)
        : dayEntries;
    final maxDay = recent.isNotEmpty
        ? recent.map((e) => e.value).reduce(math.max)
        : 1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Alerts Over Time',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              'Last ${recent.length} days',
              style: TextStyle(fontSize: 12, color: Colors.grey[500]),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 120,
              child: recent.isEmpty
                  ? const Center(child: Text('No data'))
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: recent.map((entry) {
                        final height = (entry.value / maxDay * 100).clamp(
                          4.0,
                          100.0,
                        );
                        return Expanded(
                          child: Tooltip(
                            message: '${entry.key}: ${entry.value} alerts',
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 2,
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  Text(
                                    '${entry.value}',
                                    style: TextStyle(
                                      fontSize: 9,
                                      color: Colors.grey[600],
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Container(
                                    height: height,
                                    decoration: BoxDecoration(
                                      color: Colors.blue[400],
                                      borderRadius: BorderRadius.circular(3),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
            ),
            const SizedBox(height: 8),
            // X-axis labels (first and last)
            if (recent.length >= 2)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    recent.first.key,
                    style: TextStyle(fontSize: 10, color: Colors.grey[500]),
                  ),
                  Text(
                    recent.last.key,
                    style: TextStyle(fontSize: 10, color: Colors.grey[500]),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

// ────────────────────── 5. Average Response Time ──────────────────────

class _ResponseTimeCard extends StatelessWidget {
  final List<Alert> alerts;
  const _ResponseTimeCard({required this.alerts});

  @override
  Widget build(BuildContext context) {
    final ackedAlerts = alerts
        .where((a) => a.acknowledged && a.acknowledgedAt != null)
        .toList();

    double avgMinutes = 0;
    double fastestMin = double.infinity;
    double slowestMin = 0;

    if (ackedAlerts.isNotEmpty) {
      double totalMin = 0;
      for (final a in ackedAlerts) {
        final diff = a.acknowledgedAt!.difference(a.timestamp).inSeconds / 60.0;
        totalMin += diff.abs();
        if (diff.abs() < fastestMin) fastestMin = diff.abs();
        if (diff.abs() > slowestMin) slowestMin = diff.abs();
      }
      avgMinutes = totalMin / ackedAlerts.length;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Response Time',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              'Time between alert creation and acknowledgement',
              style: TextStyle(fontSize: 12, color: Colors.grey[500]),
            ),
            const SizedBox(height: 16),
            if (ackedAlerts.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('No acknowledged alerts yet'),
                ),
              )
            else
              Row(
                children: [
                  _StatTile(
                    label: 'Average',
                    value: _formatMinutes(avgMinutes),
                    color: Colors.blue,
                  ),
                  _StatTile(
                    label: 'Fastest',
                    value: _formatMinutes(fastestMin),
                    color: Colors.green,
                  ),
                  _StatTile(
                    label: 'Slowest',
                    value: _formatMinutes(slowestMin),
                    color: Colors.red,
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  String _formatMinutes(double minutes) {
    if (minutes < 1) return '${(minutes * 60).toStringAsFixed(0)}s';
    if (minutes < 60) return '${minutes.toStringAsFixed(1)}m';
    final hours = minutes / 60;
    return '${hours.toStringAsFixed(1)}h';
  }
}
