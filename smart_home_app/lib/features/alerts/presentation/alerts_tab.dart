// FILE: lib/features/alerts/presentation/alerts_tab.dart
// UPDATED: Alert lifecycle (active alerts only) + actuator action buttons
// + link to analytics screen

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/alert_providers.dart';
import '../domain/alert.dart';
import '../../actuators/domain/actuator.dart';
import '../../actuators/data/actuator_providers.dart';
import '../../analytics/presentation/analytics_screen.dart';
import 'package:intl/intl.dart';

class AlertsTab extends ConsumerWidget {
  const AlertsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsAsync = ref.watch(alertControllerProvider);

    return alertsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => _buildErrorState(context, ref, error),
      data: (alerts) {
        // Filter to active alerts: unacknowledged OR created in last 24 hours
        final now = DateTime.now();
        final activeAlerts = alerts.where((a) {
          if (!a.acknowledged) return true;
          return now.difference(a.timestamp).inHours < 24;
        }).toList();

        return Column(
          children: [
            // ── Top bar with analytics button ──
            _buildTopBar(context, ref, alerts.length, activeAlerts.length),

            // ── Alert list ──
            Expanded(
              child: activeAlerts.isEmpty
                  ? _buildEmptyState(context, ref)
                  : RefreshIndicator(
                      onRefresh: () async {
                        await ref
                            .read(alertControllerProvider.notifier)
                            .loadAlerts();
                      },
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                        itemCount: activeAlerts.length,
                        itemBuilder: (context, index) =>
                            _AlertCard(alert: activeAlerts[index]),
                      ),
                    ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildTopBar(
    BuildContext context,
    WidgetRef ref,
    int total,
    int active,
  ) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
      child: Row(
        children: [
          Text(
            '$active active',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
          ),
          if (total > active)
            Text(
              ' · ${total - active} archived',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.grey[400]),
            ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () {
              ref.read(alertControllerProvider.notifier).loadAlerts();
            },
            tooltip: 'Refresh',
          ),
          IconButton(
            icon: const Icon(Icons.analytics_outlined, size: 20),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const AnalyticsScreen(),
                ),
              );
            },
            tooltip: 'View Analytics',
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle_outline, size: 64, color: Colors.green[300]),
          const SizedBox(height: 16),
          Text('All clear', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'No active alerts right now',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              OutlinedButton.icon(
                onPressed: () {
                  ref.read(alertControllerProvider.notifier).loadAlerts();
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Refresh'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => const AnalyticsScreen(),
                    ),
                  );
                },
                icon: const Icon(Icons.analytics_outlined),
                label: const Text('View History'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, WidgetRef ref, Object error) {
    final isNetworkError = error.toString().contains('Network error');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isNetworkError ? Icons.cloud_off : Icons.error_outline,
              size: 64,
              color: Colors.orange[300],
            ),
            const SizedBox(height: 16),
            Text(
              isNetworkError ? 'Cannot reach server' : 'Something went wrong',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              isNetworkError
                  ? 'The backend may be waking up (free tier).\nTry again in 30 seconds.'
                  : error.toString(),
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () {
                ref.read(alertControllerProvider.notifier).loadAlerts();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ],
        ),
      ),
    );
  }
}

// ────────────────────── Alert Card Widget ──────────────────────

class _AlertCard extends ConsumerStatefulWidget {
  final Alert alert;
  const _AlertCard({required this.alert});

  @override
  ConsumerState<_AlertCard> createState() => _AlertCardState();
}

class _AlertCardState extends ConsumerState<_AlertCard> {
  final Map<String, bool> _commandSent = {};

  @override
  Widget build(BuildContext context) {
    final alert = widget.alert;
    final actuatorActions = ActuatorRegistry.actionsForAlert(alert.ruleType);

    return Card(
      elevation: alert.isUrgent ? 4 : 1,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: _severityColor.withOpacity(0.5),
          width: alert.isUrgent ? 2 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header: severity badge + type + time ──
            Row(
              children: [
                _SeverityBadge(severity: alert.severity),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    alert.displayRuleType,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  _formatTime(alert.timestamp),
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.grey[500]),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // ── Message ──
            Text(alert.message, style: Theme.of(context).textTheme.bodyMedium),

            // ── Recommended action ──
            if (alert.recommendedAction != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.lightbulb_outline,
                      size: 18,
                      color: Colors.blue[700],
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        alert.recommendedAction!,
                        style: TextStyle(color: Colors.blue[800], fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // ── Actuator Action Buttons ──
            if (actuatorActions.isNotEmpty && !alert.acknowledged) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.orange[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.electric_bolt,
                          size: 16,
                          color: Colors.orange[800],
                        ),
                        const SizedBox(width: 6),
                        Text(
                          'Quick Actions',
                          style: TextStyle(
                            color: Colors.orange[800],
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: actuatorActions.map((action) {
                        final key = '${alert.id}_${action.actuator.id}';
                        final sent = _commandSent[key] == true;

                        return _ActuatorButton(
                          actuatorName: action.actuator.name,
                          commandLabel: action.command.label,
                          sent: sent,
                          onPressed: () async {
                            final repo = ref.read(actuatorRepositoryProvider);
                            final success = await repo.sendCommand(
                              action.actuator,
                              action.command,
                            );
                            if (success) {
                              setState(() => _commandSent[key] = true);
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      '${action.actuator.name}: ${action.command.label}',
                                    ),
                                    duration: const Duration(seconds: 2),
                                  ),
                                );
                              }
                            } else {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      'Failed to send command to ${action.actuator.name}',
                                    ),
                                    backgroundColor: Colors.red[400],
                                  ),
                                );
                              }
                            }
                          },
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 12),

            // ── Footer: acknowledge ──
            if (alert.acknowledged)
              Row(
                children: [
                  Icon(Icons.check_circle, size: 18, color: Colors.green[400]),
                  const SizedBox(width: 6),
                  Text(
                    'Acknowledged${alert.acknowledgedBy != null ? ' by ${alert.acknowledgedBy}' : ''}',
                    style: TextStyle(color: Colors.green[600], fontSize: 13),
                  ),
                ],
              )
            else
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  onPressed: () {
                    ref
                        .read(alertControllerProvider.notifier)
                        .acknowledge(alert.id);
                  },
                  child: const Text('Acknowledge'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Color get _severityColor {
    switch (widget.alert.severity) {
      case 'HIGH':
        return Colors.red;
      case 'MEDIUM':
        return Colors.orange;
      case 'LOW':
        return Colors.yellow[700]!;
      default:
        return Colors.blue;
    }
  }

  String _formatTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return DateFormat('MMM d, HH:mm').format(dt);
  }
}

// ────────────────────── Actuator Button ──────────────────────

class _ActuatorButton extends StatelessWidget {
  final String actuatorName;
  final String commandLabel;
  final bool sent;
  final VoidCallback onPressed;

  const _ActuatorButton({
    required this.actuatorName,
    required this.commandLabel,
    required this.sent,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: sent ? null : onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: sent ? Colors.green[700] : Colors.orange[800],
        side: BorderSide(
          color: sent
              ? Colors.green.withOpacity(0.5)
              : Colors.orange.withOpacity(0.5),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        visualDensity: VisualDensity.compact,
      ),
      icon: Icon(sent ? Icons.check : Icons.electric_bolt, size: 16),
      label: Text(
        sent ? '$actuatorName ✓' : '$commandLabel $actuatorName',
        style: const TextStyle(fontSize: 12),
      ),
    );
  }
}

// ────────────────────── Severity Badge ──────────────────────

class _SeverityBadge extends StatelessWidget {
  final String severity;
  const _SeverityBadge({required this.severity});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        severity,
        style: TextStyle(
          color: _color,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Color get _color {
    switch (severity) {
      case 'HIGH':
        return Colors.red;
      case 'MEDIUM':
        return Colors.orange;
      case 'LOW':
        return Colors.amber[700]!;
      default:
        return Colors.blue;
    }
  }
}
