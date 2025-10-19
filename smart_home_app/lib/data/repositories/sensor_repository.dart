import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../database/app_database.dart';
import '../models/sensor.dart';

class SensorRepository {
  final AppDatabase _db;

  SensorRepository(this._db);

  Stream<List<SensorWithReading>> watchAllSensorsWithReadings() {
    final query = _db.select(_db.sensors).join([
      leftOuterJoin(
        _db.sensorReadings,
        _db.sensorReadings.sensorId.equalsExp(_db.sensors.id),
      ),
    ]);

    return query.watch().map((rows) {
      final sensorMap = <String, SensorWithReading>{};

      for (final row in rows) {
        final sensor = row.readTable(_db.sensors);
        final reading = row.readTableOrNull(_db.sensorReadings);

        final existing = sensorMap[sensor.id];
        if (existing == null ||
            (reading != null &&
                (existing.lastValue == null ||
                    reading.timestamp.isAfter(
                      DateTime.parse(existing.lastUpdated.toIso8601String()),
                    )))) {
          sensorMap[sensor.id] = SensorWithReading(
            id: sensor.id,
            sensorType: sensor.sensorType,
            room: sensor.room,
            lastUpdated: reading?.timestamp ?? sensor.lastUpdated,
            lastValue: reading?.value,
            unit: reading?.unit,
          );
        }
      }

      return sensorMap.values.toList()
        ..sort((a, b) => b.lastUpdated.compareTo(a.lastUpdated));
    });
  }

  Future<void> saveSensorData(SensorData data) async {
    await _db.upsertSensor(
      SensorsCompanion(
        id: Value(data.sensorId),
        sensorType: Value(data.sensorType),
        room: Value(data.room),
        lastUpdated: Value(data.timestamp),
      ),
    );

    await _db.insertReading(
      SensorReadingsCompanion(
        sensorId: Value(data.sensorId),
        value: Value(data.value),
        unit: Value(data.unit),
        timestamp: Value(data.timestamp),
      ),
    );
  }

  Future<List<SensorReading>> getReadingsForSensor(
    String sensorId, {
    int limit = 100,
  }) {
    return _db.getReadingsForSensor(sensorId, limit: limit);
  }

  Future<void> cleanupOldData(int retentionDays) async {
    await _db.cleanupOldReadings(retentionDays);
  }
}

final sensorRepositoryProvider = Provider<SensorRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return SensorRepository(db);
});

final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(() => db.close());
  return db;
});
