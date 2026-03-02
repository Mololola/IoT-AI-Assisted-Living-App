// FILE: lib/features/alerts/data/alert_repository.dart
// Repository pattern for alerts — fetching, filtering, and acknowledging.

import '../domain/alert.dart';
import '../../../core/data/api_client.dart';

/// Abstract interface for alert data access
abstract class AlertRepository {
  Future<List<Alert>> getAlerts({String? severity, bool? acknowledged});
  Future<void> acknowledgeAlert(String alertId, {String? by});
}

// ────────────────────── REMOTE (real backend) ──────────────────────

class RemoteAlertRepository implements AlertRepository {
  final ApiClient _apiClient;

  RemoteAlertRepository(this._apiClient);

  @override
  Future<List<Alert>> getAlerts({
    String? severity,
    bool? acknowledged,
  }) async {
    try {
      final jsonList = await _apiClient.fetchAlerts(
        severity: severity,
        acknowledged: acknowledged,
      );
      return jsonList.map((json) => Alert.fromBackendJson(json)).toList();
    } on ApiException catch (e) {
      if (e.isNotFound) return []; // Backend doesn't have /alerts yet
      rethrow;
    }
  }

  @override
  Future<void> acknowledgeAlert(String alertId, {String? by}) async {
    await _apiClient.acknowledgeAlert(alertId, acknowledgedBy: by);
  }
}

// ────────────────────── MOCK (for testing) ──────────────────────

class MockAlertRepository implements AlertRepository {
  final List<Alert> _mockAlerts = [
    Alert(
      id: 'mock_1',
      alertId: 'alert-001',
      timestamp: DateTime.now().subtract(const Duration(minutes: 10)),
      ruleType: 'night_wandering',
      severity: 'HIGH',
      message: 'Night wandering detected — out of bed for 15 minutes',
      sensorData: {'pressure': 0.05, 'pir': 1, 'presence': true},
      recommendedAction: 'Check on resident',
    ),
    Alert(
      id: 'mock_2',
      alertId: 'alert-002',
      timestamp: DateTime.now().subtract(const Duration(hours: 2)),
      ruleType: 'restless_sleep',
      severity: 'MEDIUM',
      message: 'Restless sleep detected — frequent motion while in bed',
      sensorData: {'pressure': 0.48, 'pir': 1},
      recommendedAction: 'Monitor — may need attention if persists',
    ),
    Alert(
      id: 'mock_3',
      alertId: 'alert-003',
      timestamp: DateTime.now().subtract(const Duration(hours: 6)),
      ruleType: 'sensor_health',
      severity: 'LOW',
      message: 'PIR sensor has not reported for 5 minutes',
      sensorData: {},
      recommendedAction: 'Check sensor battery or connection',
      acknowledged: true,
      acknowledgedBy: 'Luis',
      acknowledgedAt: DateTime.now().subtract(const Duration(hours: 5)),
    ),
  ];

  @override
  Future<List<Alert>> getAlerts({
    String? severity,
    bool? acknowledged,
  }) async {
    await Future.delayed(const Duration(milliseconds: 300));
    var results = List<Alert>.from(_mockAlerts);
    if (severity != null) {
      results = results.where((a) => a.severity == severity).toList();
    }
    if (acknowledged != null) {
      results = results.where((a) => a.acknowledged == acknowledged).toList();
    }
    return results;
  }

  @override
  Future<void> acknowledgeAlert(String alertId, {String? by}) async {
    await Future.delayed(const Duration(milliseconds: 200));
    // In mock mode this is a no-op — the list doesn't actually update.
    // For a real demo you'd modify _mockAlerts in place.
  }
}
