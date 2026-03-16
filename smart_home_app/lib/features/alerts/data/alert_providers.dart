// FILE: lib/features/alerts/data/alert_providers.dart
// Riverpod providers for alerts — connects UI to repository layer.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../sensors/data/sensor_providers.dart'; // for apiClientProvider
import 'alert_repository.dart';
import '../domain/alert.dart';

/// Pick Mock or Remote alert repository based on config
final alertRepositoryProvider = Provider<AlertRepository>((ref) {
  if (AppConfig.useRemoteBackend) {
    final apiClient = ref.watch(apiClientProvider);
    return RemoteAlertRepository(apiClient);
  }
  return MockAlertRepository();
});

/// Fetches all alerts — UI watches this
final alertListProvider = FutureProvider<List<Alert>>((ref) async {
  final repository = ref.watch(alertRepositoryProvider);
  return repository.getAlerts();
});

/// Fetches only unacknowledged alerts — for badge count
final unacknowledgedAlertCountProvider = FutureProvider<int>((ref) async {
  final repository = ref.watch(alertRepositoryProvider);
  final alerts = await repository.getAlerts(acknowledged: false);
  return alerts.length;
});

/// Fetches only HIGH severity unacknowledged alerts — for urgent banner
final urgentAlertsProvider = FutureProvider<List<Alert>>((ref) async {
  final repository = ref.watch(alertRepositoryProvider);
  return repository.getAlerts(severity: 'HIGH', acknowledged: false);
});

/// Controller for alert actions (acknowledge, refresh)
class AlertController extends StateNotifier<AsyncValue<List<Alert>>> {
  final AlertRepository _repository;
  final Ref _ref;

  AlertController(this._repository, this._ref)
    : super(const AsyncValue.loading()) {
    loadAlerts();
  }

  Future<void> loadAlerts() async {
    state = const AsyncValue.loading();
    try {
      final alerts = await _repository.getAlerts();
      state = AsyncValue.data(alerts);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> acknowledge(String alertId, {String? by}) async {
    // Optimistic: remove the alert from local state immediately
    // so the card disappears without waiting for the network round-trip
    final current = state.value ?? [];
    state = AsyncValue.data(current.where((a) => a.id != alertId).toList());

    try {
      await _repository.acknowledgeAlert(alertId, by: by);
      // Invalidate badge count and urgent alerts providers
      _ref.invalidate(unacknowledgedAlertCountProvider);
      _ref.invalidate(urgentAlertsProvider);
      // Full refresh in the background to sync with server
      await loadAlerts();
    } catch (error, stackTrace) {
      // If the API call failed, reload to restore accurate state
      await loadAlerts();
    }
  }
}

/// Stateful provider for alert list + actions
final alertControllerProvider =
    StateNotifierProvider<AlertController, AsyncValue<List<Alert>>>((ref) {
      final repository = ref.watch(alertRepositoryProvider);
      return AlertController(repository, ref);
    });
