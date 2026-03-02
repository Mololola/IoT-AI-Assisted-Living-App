// FILE: lib/features/sensors/data/sensor_repository.dart
// Repository pattern for sensors.
// Contains BOTH MockSensorRepository (for testing) and
// RemoteSensorRepository (for the real Render backend).
// The provider in sensor_providers.dart picks which one to use.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/sensor.dart';
import '../../../core/data/api_client.dart';

/// Abstract repository interface — UI code only depends on this
abstract class SensorRepository {
  Future<List<Sensor>> getSensors();
}

// ────────────────────── REMOTE (real backend) ──────────────────────

/// Fetches sensor data from the FastAPI backend on Render.
/// Calls GET /sensor-readings/latest to get the most recent
/// reading for each sensor type.
class RemoteSensorRepository implements SensorRepository {
  final ApiClient _apiClient;

  RemoteSensorRepository(this._apiClient);

  @override
  Future<List<Sensor>> getSensors() async {
    try {
      final jsonList = await _apiClient.fetchLatestReadings();
      return jsonList.map((json) => Sensor.fromBackendJson(json)).toList();
    } on ApiException catch (e) {
      if (e.isNotFound) {
        // /sensor-readings/latest doesn't exist yet on backend
        // Return empty list — the UI should show "No sensor data yet"
        return [];
      }
      rethrow;
    }
  }
}

// ────────────────────── MOCK (for testing) ──────────────────────

/// Mock implementation using hardcoded data.
/// Used when AppConfig.useRemoteBackend is false.
class MockSensorRepository implements SensorRepository {
  final Ref ref;

  MockSensorRepository(this.ref);

  @override
  Future<List<Sensor>> getSensors() async {
    await Future.delayed(const Duration(milliseconds: 300));

    return [
      Sensor(
        id: 'pressure_001',
        type: 'pressure',
        room: 'Bedroom',
        value: 0.45,
        unit: 'bar',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 1)),
      ),
      Sensor(
        id: 'pir_001',
        type: 'PIR',
        room: 'Bedroom',
        value: 1.0,
        unit: '',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 2)),
      ),
      Sensor(
        id: 'presence_001',
        type: 'presence',
        room: 'Bedroom',
        value: 120.0,
        unit: 'cm',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 1)),
      ),
    ];
  }
}
