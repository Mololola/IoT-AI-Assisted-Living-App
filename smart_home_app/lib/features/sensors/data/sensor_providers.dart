// FILE: lib/features/sensors/data/sensor_providers.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../../core/data/api_client.dart';
import 'sensor_repository.dart';
import '../domain/sensor.dart';

/// Single shared ApiClient instance for the whole app.
final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient();
  ref.onDispose(() => client.dispose());
  return client;
});

/// Pick the right repository based on the feature flag.
final sensorRepositoryProvider = Provider<SensorRepository>((ref) {
  if (AppConfig.useRemoteBackend) {
    final apiClient = ref.watch(apiClientProvider);
    return RemoteSensorRepository(apiClient);
  }
  return MockSensorRepository(ref);
});

/// Latest reading for each sensor — what the main Sensors tab shows.
final sensorListProvider = FutureProvider<List<Sensor>>((ref) async {
  final repository = ref.watch(sensorRepositoryProvider);
  return repository.getSensors();
});

/// History periods the user can pick from.
enum HistoryPeriod { week, month, threeMonths }

extension HistoryPeriodLabel on HistoryPeriod {
  String get label {
    switch (this) {
      case HistoryPeriod.week:
        return 'Last 7 days';
      case HistoryPeriod.month:
        return 'Last 30 days';
      case HistoryPeriod.threeMonths:
        return 'Last 90 days';
    }
  }

  int get days {
    switch (this) {
      case HistoryPeriod.week:
        return 7;
      case HistoryPeriod.month:
        return 30;
      case HistoryPeriod.threeMonths:
        return 90;
    }
  }
}

/// Fetches historical readings for one specific sensor type.
/// Key is (sensorType, period) so each combination is cached separately.
final sensorHistoryProvider =
    FutureProvider.family<List<Sensor>, (String, HistoryPeriod)>((
      ref,
      args,
    ) async {
      final sensorType = args.$1;
      final period = args.$2;
      final repository = ref.watch(sensorRepositoryProvider);
      return repository.getSensorHistory(
        sensorType: sensorType,
        days: period.days,
      );
    });

/// Backend health — used by Settings tab.
final backendHealthProvider = FutureProvider<bool>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  return apiClient.healthCheck();
});
