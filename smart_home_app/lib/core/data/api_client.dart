// FILE: lib/core/data/api_client.dart
// HTTP client for the FastAPI backend on Render.
// UPDATED: Added sendActuatorCommand + fetchAllAlerts for analytics.
// UPDATED: Added createException, fetchExceptions, deleteException for Routines tab.

import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../config/app_config.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  final http.Client _client;
  final String baseUrl;

  ApiClient({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  Uri _uri(String path, [Map<String, String>? queryParams]) {
    final uri = Uri.parse('$baseUrl$path');
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

  Future<dynamic> _getRaw(
    String path, [
    Map<String, String>? queryParams,
  ]) async {
    try {
      debugPrint('API GET: $baseUrl$path');
      final response = await _client
          .get(_uri(path, queryParams), headers: _headers)
          .timeout(AppConfig.coldStartTimeout);

      debugPrint(
        'API Response ${response.statusCode}: ${response.body.substring(0, response.body.length.clamp(0, 200))}',
      );

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body);
      }
      throw ApiException(response.statusCode, response.body);
    } catch (e) {
      if (e is ApiException) rethrow;
      debugPrint('API Error: $e');
      throw ApiException(0, 'Network error: $e');
    }
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    try {
      final response = await _client
          .post(_uri(path), headers: _headers, body: jsonEncode(body))
          .timeout(AppConfig.coldStartTimeout);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body);
      }
      throw ApiException(response.statusCode, response.body);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(0, 'Network error: $e');
    }
  }

  Future<dynamic> _put(String path, [Map<String, dynamic>? body]) async {
    try {
      final response = await _client
          .put(
            _uri(path),
            headers: _headers,
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(AppConfig.coldStartTimeout);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body);
      }
      throw ApiException(response.statusCode, response.body);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(0, 'Network error: $e');
    }
  }

  Future<dynamic> _delete(String path) async {
    try {
      final response = await _client
          .delete(_uri(path), headers: _headers)
          .timeout(AppConfig.coldStartTimeout);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        // Some DELETE endpoints return empty body — handle gracefully
        if (response.body.isEmpty) return null;
        return jsonDecode(response.body);
      }
      throw ApiException(response.statusCode, response.body);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(0, 'Network error: $e');
    }
  }

  // ────────────────────── Health ──────────────────────

  Future<bool> healthCheck() async {
    try {
      final data = await _getRaw('/health');
      return data is Map && data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  // ────────────────────── Residents ──────────────────────

  Future<List<Map<String, dynamic>>> fetchResidents({int limit = 20}) async {
    final data = await _getRaw('/residents', {'limit': limit.toString()});
    return _toListOfMaps(data);
  }

  Future<String> createResident({
    required String name,
    required String room,
    String? notes,
  }) async {
    final data = await _post('/residents', {
      'name': name,
      'room': room,
      if (notes != null) 'notes': notes,
    });
    return (data is Map ? data['inserted_id'] ?? data['id'] ?? '' : '')
        .toString();
  }

  // ────────────────────── Alerts ──────────────────────

  Future<List<Map<String, dynamic>>> fetchAlerts({
    String? severity,
    bool? acknowledged,
    int limit = 50,
    String? since,
  }) async {
    final params = <String, String>{'limit': limit.toString()};
    if (severity != null) params['severity'] = severity;
    if (acknowledged != null) params['acknowledged'] = acknowledged.toString();
    if (since != null) params['since'] = since;

    final data = await _getRaw('/alerts', params);
    return _toListOfMaps(data);
  }

  /// Fetch ALL alerts (larger limit) for analytics
  Future<List<Map<String, dynamic>>> fetchAllAlerts({int limit = 500}) async {
    final data = await _getRaw('/alerts', {'limit': limit.toString()});
    return _toListOfMaps(data);
  }

  Future<Map<String, dynamic>> fetchAlert(String alertId) async {
    final data = await _getRaw('/alerts/$alertId');
    return data is Map<String, dynamic> ? data : {};
  }

  Future<void> acknowledgeAlert(
    String alertId, {
    String? acknowledgedBy,
  }) async {
    await _put('/alerts/$alertId/acknowledge');
  }

  // ────────────────────── Sensor Readings ──────────────────────

  Future<List<Map<String, dynamic>>> fetchLatestReadings() async {
    final data = await _getRaw('/sensor-readings', {'limit': '200'});
    final all = _toListOfMaps(data);

    // Keep only the most recent reading per sensor_type + topic combination
    final Map<String, Map<String, dynamic>> latest = {};
    for (final reading in all) {
      final key = '${reading['sensor_type']}_${reading['topic']}';
      if (!latest.containsKey(key)) {
        latest[key] = reading; // API returns newest first, so first = latest
      }
    }
    return latest.values.toList();
  }

  Future<List<Map<String, dynamic>>> fetchSensorReadings({
    String? sensorType,
    int limit = 100,
  }) async {
    final params = <String, String>{'limit': limit.toString()};
    if (sensorType != null) params['sensor_type'] = sensorType;

    final data = await _getRaw('/sensor-readings', params);
    return _toListOfMaps(data);
  }

  // ────────────────────── Model Info ──────────────────────

  Future<Map<String, dynamic>?> fetchLatestModel() async {
    try {
      final data = await _getRaw('/models/latest');
      return data is Map<String, dynamic> ? data : null;
    } on ApiException catch (e) {
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }

  // ────────────────────── Exceptions (Routines) ──────────────────────
  // These map to the Routines tab in the app.
  // The Pi polls GET /exceptions every 15 real seconds and suppresses
  // alerts whenever the current simulated time falls inside a window.

  /// POST /exceptions — create a new exception (suppresses alerts in window)
  Future<String> createException({
    required String date, // "YYYY-MM-DD"
    required String startTime, // "HH:MM"
    required String endTime, // "HH:MM"
    required String description,
    String type = 'away_from_home',
    String createdBy = 'caregiver',
  }) async {
    final data = await _post('/exceptions', {
      'date': date,
      'start_time': startTime,
      'end_time': endTime,
      'type': type,
      'description': description,
      'created_by': createdBy,
      'message': description,
      'timestamp': DateTime.now().toUtc().toIso8601String(),
    });
    return (data is Map ? data['inserted_id'] ?? data['id'] ?? '' : '')
        .toString();
  }

  /// GET /exceptions — list all active/future exceptions
  Future<List<Map<String, dynamic>>> fetchExceptions() async {
    final data = await _getRaw('/exceptions');
    return _toListOfMaps(data);
  }

  /// DELETE /exceptions/{id} — remove an exception (resumes alerting on next Pi poll)
  Future<void> deleteException(String exceptionId) async {
    await _delete('/exceptions/$exceptionId');
  }

  // ────────────────────── Actuator Commands ──────────────────────

  Future<void> sendActuatorCommand({
    required String topic,
    required String payload,
    required String actuatorId,
  }) async {
    await _post('/actuators/command', {
      'topic': topic,
      'payload': payload,
      'actuator_id': actuatorId,
    });
  }

  // ────────────────────── Response Parsing ──────────────────────

  List<Map<String, dynamic>> _toListOfMaps(dynamic data) {
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    } else if (data is Map) {
      final items = data['items'];
      if (items is List) {
        return items.cast<Map<String, dynamic>>();
      }
      return [Map<String, dynamic>.from(data)];
    }
    return [];
  }

  void dispose() {
    _client.close();
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  bool get isNetworkError => statusCode == 0;
  bool get isNotFound => statusCode == 404;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
