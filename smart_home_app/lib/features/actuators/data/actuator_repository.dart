// FILE: lib/features/actuators/data/actuator_repository.dart
// Sends actuator commands to the backend.
// The backend then publishes to MQTT → Pi → ESP32 actuator.
// Backend endpoint: POST /actuators/command
// This endpoint needs to be added by Daniel.

import '../../../core/data/api_client.dart';
import '../domain/actuator.dart';

abstract class ActuatorRepository {
  Future<bool> sendCommand(Actuator actuator, ActuatorCommand command);
}

class RemoteActuatorRepository implements ActuatorRepository {
  final ApiClient _apiClient;

  RemoteActuatorRepository(this._apiClient);

  @override
  Future<bool> sendCommand(Actuator actuator, ActuatorCommand command) async {
    try {
      await _apiClient.sendActuatorCommand(
        topic: actuator.mqttTopic,
        payload: command.payload,
        actuatorId: actuator.id,
      );
      return true;
    } catch (e) {
      print('Actuator command failed: $e');
      return false;
    }
  }
}

/// Mock implementation for testing without the backend
class MockActuatorRepository implements ActuatorRepository {
  @override
  Future<bool> sendCommand(Actuator actuator, ActuatorCommand command) async {
    await Future.delayed(const Duration(milliseconds: 500));
    print('MOCK: ${actuator.name} → ${command.payload}');
    return true;
  }
}
