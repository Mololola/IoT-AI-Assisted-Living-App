// FILE: lib/features/actuators/data/actuator_providers.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../sensors/data/sensor_providers.dart';
import 'actuator_repository.dart';

final actuatorRepositoryProvider = Provider<ActuatorRepository>((ref) {
  if (AppConfig.useRemoteBackend) {
    final apiClient = ref.watch(apiClientProvider);
    return RemoteActuatorRepository(apiClient);
  }
  return MockActuatorRepository();
});
