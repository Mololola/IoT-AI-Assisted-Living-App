// FILE: lib/features/sensors/data/sensor_repository.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/sensor.dart';
import '../../../core/data/api_client.dart';

abstract class SensorRepository {
  Future<List<Sensor>> getSensors();
  Future<List<Sensor>> getSensorHistory({
    required String sensorType,
    required int days,
  });
}

// ────────────────────── REMOTE ──────────────────────

class RemoteSensorRepository implements SensorRepository {
  final ApiClient _apiClient;
  RemoteSensorRepository(this._apiClient);

  @override
  Future<List<Sensor>> getSensors() async {
    try {
      final jsonList = await _apiClient.fetchLatestReadings();
      return jsonList.map((json) => Sensor.fromBackendJson(json)).toList();
    } on ApiException catch (e) {
      if (e.isNotFound) return [];
      rethrow;
    }
  }

  @override
  Future<List<Sensor>> getSensorHistory({
    required String sensorType,
    required int days,
  }) async {
    try {
      // Fetch a large batch and filter client-side by date.
      // limit=1000 covers 5-second posting intervals for up to 90 days
      // (90 days × 17280 readings/day would be too many, so we cap at 1000
      // which gives a good chart resolution without hammering the API).
      final jsonList = await _apiClient.fetchSensorReadings(
        sensorType: sensorType,
        limit: 1000,
      );

      final cutoff = DateTime.now().subtract(Duration(days: days));
      final all = jsonList.map((json) => Sensor.fromBackendJson(json)).toList();

      // Keep only readings within the requested period
      return all.where((s) => s.lastUpdated.isAfter(cutoff)).toList()
        ..sort((a, b) => a.lastUpdated.compareTo(b.lastUpdated));
    } on ApiException catch (e) {
      if (e.isNotFound) return [];
      rethrow;
    }
  }
}

// ────────────────────── MOCK ──────────────────────

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
        value: 2400,
        unit: '',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 1)),
      ),
      Sensor(
        id: 'pir_001',
        type: 'pir',
        room: 'Bedroom',
        value: 1.0,
        unit: '',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 2)),
      ),
      Sensor(
        id: 'presence_001',
        type: 'presence',
        room: 'Bedroom',
        value: 35.0,
        unit: 'cm',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 1)),
      ),
      Sensor(
        id: 'light_001',
        type: 'light',
        room: 'Bedroom',
        value: 0.0,
        unit: '',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 3)),
      ),
      Sensor(
        id: 'sink_001',
        type: 'sink',
        room: 'Bathroom',
        value: 0.0,
        unit: '',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 5)),
      ),
      Sensor(
        id: 'presence_002',
        type: 'presence',
        room: 'Bathroom',
        value: 0.0,
        unit: 'cm',
        lastUpdated: DateTime.now().subtract(const Duration(minutes: 5)),
      ),
    ];
  }

  @override
  Future<List<Sensor>> getSensorHistory({
    required String sensorType,
    required int days,
  }) async {
    await Future.delayed(const Duration(milliseconds: 400));
    final now = DateTime.now();
    final readings = <Sensor>[];
    // Generate one mock reading every 4 hours over the requested period
    for (int h = days * 24; h >= 0; h -= 4) {
      final t = now.subtract(Duration(hours: h));
      readings.add(
        Sensor(
          id: 'mock_hist_$h',
          type: sensorType,
          room: 'Bedroom',
          value: (500 + (h % 7) * 300).toDouble(),
          unit: '',
          lastUpdated: t,
        ),
      );
    }
    return readings;
  }
}
