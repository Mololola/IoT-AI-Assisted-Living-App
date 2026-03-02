// FILE: lib/features/sensors/data/sensor_providers.dart
// Riverpod providers for sensors.
// The apiClientProvider is the single shared HTTP client.
// The sensorRepositoryProvider picks Mock or Remote based on config.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../../core/data/api_client.dart';
import 'sensor_repository.dart';
import '../domain/sensor.dart';

/// Single shared ApiClient instance for the whole app.
/// Declared here so other features can import it too.
final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient();
  ref.onDispose(() => client.dispose());
  return client;
});

/// Pick the right repository based on the feature flag.
/// Flip AppConfig.useRemoteBackend to switch.
final sensorRepositoryProvider = Provider<SensorRepository>((ref) {
  if (AppConfig.useRemoteBackend) {
    final apiClient = ref.watch(apiClientProvider);
    return RemoteSensorRepository(apiClient);
  }
  return MockSensorRepository(ref);
});

/// Provider that UI watches — returns sensor list.
/// Uses FutureProvider so the UI gets loading / data / error states
/// for free via AsyncValue.
final sensorListProvider = FutureProvider<List<Sensor>>((ref) async {
  final repository = ref.watch(sensorRepositoryProvider);
  return repository.getSensors();
});

/// Provider for backend connection status.
/// The Settings tab can watch this to show a green/red indicator.
final backendHealthProvider = FutureProvider<bool>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  return apiClient.healthCheck();
});
