// FILE: lib/core/config/app_config.dart
// Centralized configuration for the app — backend URL, timeouts, etc.

class AppConfig {
  // ──── Backend API ────
  // Your FastAPI deployed on Render
  static const String apiBaseUrl =
      'https://assisted-living-platform.onrender.com';

  // HTTP client settings
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 15);

  // Render free tier sleeps after 15min of inactivity.
  // First request after sleep can take 30-50 seconds.
  // This longer timeout handles that cold-start.
  static const Duration coldStartTimeout = Duration(seconds: 60);

  // ──── Polling intervals ────
  // How often the app fetches fresh data from the backend.
  // These are only used if you add periodic refresh later.
  static const Duration alertPollInterval = Duration(seconds: 30);
  static const Duration sensorPollInterval = Duration(seconds: 60);

  // ──── Feature flags ────
  // Flip this to false to fall back to mock data for testing
  static const bool useRemoteBackend = true;
}
