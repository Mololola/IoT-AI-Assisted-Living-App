// FILE: lib/core/data/api_client.dart
// HTTP client for communicating with the FastAPI backend on Render.
// FIXED: Matches the actual backend response format (plain arrays).

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

  // ────────────────────── helpers ──────────────────────

  Uri _uri(String path, [Map<String, String>? queryParams]) {
    final uri = Uri.parse('$baseUrl$path');
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

  /// Generic GET that returns a parsed JSON (could be Map or List)
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

  /// Generic POST request
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

  /// Generic PUT request
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
  }) async {
    final params = <String, String>{'limit': limit.toString()};
    if (severity != null) params['severity'] = severity;
    if (acknowledged != null) params['acknowledged'] = acknowledged.toString();

    final data = await _getRaw('/alerts', params);
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
    // Daniel's endpoint is /alerts/{id}/acknowledge (not /ack)
    // and it uses the MongoDB _id, not alert_id
    await _put('/alerts/$alertId/acknowledge');
  }

  // ────────────────────── Sensor Readings ──────────────────────

  Future<List<Map<String, dynamic>>> fetchLatestReadings() async {
    final data = await _getRaw('/sensor-readings/latest');
    return _toListOfMaps(data);
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

  // ────────────────────── Response Parsing ──────────────────────

  /// Handles both response formats:
  /// - Plain array: [{...}, {...}]
  /// - Wrapped: {"items": [{...}, {...}], "count": 2}
  List<Map<String, dynamic>> _toListOfMaps(dynamic data) {
    if (data is List) {
      // Backend returns a plain JSON array
      return data.cast<Map<String, dynamic>>();
    } else if (data is Map) {
      // Backend returns {"items": [...]} wrapper
      final items = data['items'];
      if (items is List) {
        return items.cast<Map<String, dynamic>>();
      }
      // Single object — wrap in list
      return [Map<String, dynamic>.from(data)];
    }
    return [];
  }

  void dispose() {
    _client.close();
  }
}

/// Custom exception for API errors
class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  bool get isNetworkError => statusCode == 0;
  bool get isNotFound => statusCode == 404;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
