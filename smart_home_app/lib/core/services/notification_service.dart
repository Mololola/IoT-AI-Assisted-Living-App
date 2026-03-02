// FILE: lib/core/services/notification_service.dart
// Handles Firebase Cloud Messaging + local notifications.
//
// Three notification states:
//   1. FOREGROUND  — app is visible → show a banner/snackbar
//   2. BACKGROUND  — app is minimized → system notification (handled by FCM)
//   3. TERMINATED  — app is closed → system notification (handled by FCM)
//
// This service manages all three.

import 'dart:convert';
import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Top-level handler for background messages.
/// MUST be a top-level function (not inside a class).
/// This runs in a separate isolate when the app is in background/terminated.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Background messages are automatically shown as system notifications
  // by FCM if the message contains a 'notification' field.
  // We don't need to do anything extra here.
  print('Background message received: ${message.messageId}');
}

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  /// Callback when user taps a notification — set this from main.dart
  /// to navigate to the Alerts tab.
  void Function(String? alertId)? onNotificationTap;

  /// Initialize everything. Call this once from main.dart after Firebase.initializeApp().
  Future<void> initialize() async {
    // 1. Request permission (shows the system dialog on iOS + Android 13+)
    await _requestPermission();

    // 2. Set up local notifications (for showing banners when app is in foreground)
    await _setupLocalNotifications();

    // 3. Subscribe to the "alerts" topic — all alert notifications go here
    await _fcm.subscribeToTopic('alerts');
    print('Subscribed to FCM topic: alerts');

    // 4. Get the device token (useful for debugging)
    final token = await _fcm.getToken();
    print('FCM Device Token: $token');
    // In production you'd send this token to your backend
    // so it can send targeted notifications. But since we use
    // topic-based messaging, we don't strictly need this.

    // 5. Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // 6. Handle notification taps (when app is in background)
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

    // 7. Check if app was opened from a terminated state via notification
    final initialMessage = await _fcm.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationTap(initialMessage);
    }
  }

  // ────────────────────── Permission ──────────────────────

  Future<void> _requestPermission() async {
    final settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false, // Set to true for "quiet" notifications on iOS
      criticalAlert: false, // Set to true if you want to bypass Do Not Disturb
      announcement: false,
    );

    print('Notification permission: ${settings.authorizationStatus}');

    // On iOS, also request to show notifications in foreground
    if (Platform.isIOS) {
      await _fcm.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );
    }
  }

  // ────────────────────── Local Notifications Setup ──────────────────────

  Future<void> _setupLocalNotifications() async {
    // Android channel — this controls the notification appearance
    const androidChannel = AndroidNotificationChannel(
      'high_importance_channel', // Must match the channel_id in backend
      'Alert Notifications', // User-visible name
      description: 'Notifications for elderly care alerts',
      importance: Importance.high,
      playSound: true,
      enableVibration: true,
    );

    // Create the channel on Android
    await _localNotifications
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(androidChannel);

    // Initialize the plugin
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false, // We already requested above
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    await _localNotifications.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: (response) {
        // User tapped a LOCAL notification (foreground banner)
        final payload = response.payload;
        if (payload != null) {
          final data = jsonDecode(payload);
          onNotificationTap?.call(data['alert_id'] as String?);
        }
      },
    );
  }

  // ────────────────────── Foreground Message Handler ──────────────────────

  void _handleForegroundMessage(RemoteMessage message) {
    print('Foreground message: ${message.notification?.title}');

    final notification = message.notification;
    if (notification == null) return;

    // Show a local notification banner (because FCM doesn't auto-show
    // notifications when the app is in the foreground on Android)
    final severity = message.data['severity'] ?? 'INFO';

    _localNotifications.show(
      message.hashCode, // Unique ID for this notification
      notification.title ?? 'Alert',
      notification.body ?? '',
      NotificationDetails(
        android: AndroidNotificationDetails(
          'high_importance_channel',
          'Alert Notifications',
          importance: severity == 'HIGH' ? Importance.max : Importance.high,
          priority: severity == 'HIGH' ? Priority.max : Priority.high,
          icon: '@mipmap/ic_launcher',
          playSound: true,
          enableVibration: true,
          // Color-code the notification LED based on severity
          ledColor: severity == 'HIGH'
              ? const Color(0xFFFF0000)
              : const Color(0xFFFFA500),
          ledOnMs: 1000,
          ledOffMs: 500,
          enableLights: true,
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
      payload: jsonEncode(message.data), // Pass data for tap handling
    );
  }

  // ────────────────────── Notification Tap Handler ──────────────────────

  void _handleNotificationTap(RemoteMessage message) {
    print('Notification tapped: ${message.data}');
    final alertId = message.data['alert_id'] as String?;
    onNotificationTap?.call(alertId);
  }
}
