// FILE: lib/core/services/notification_service.dart
// FIXED: Uses a global ValueNotifier for tab navigation.
// This is simpler and more reliable than passing ProviderContainer.

import 'dart:convert';
import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Top-level handler for background messages.
/// MUST be a top-level function (not inside a class).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print('Background message received: ${message.messageId}');
}

/// Global notifier that HomeScreen listens to.
/// When a notification is tapped, this is set to 1 (Alerts tab).
/// HomeScreen picks up the change and switches tabs.
final navigateToTabNotifier = ValueNotifier<int?>(null);

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  /// Initialize everything. Call once from main.dart after Firebase.initializeApp().
  Future<void> initialize() async {
    await _requestPermission();
    await _setupLocalNotifications();

    await _fcm.subscribeToTopic('alerts');
    print('Subscribed to FCM topic: alerts');

    final token = await _fcm.getToken();
    print('FCM Device Token: $token');

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle notification taps (app in background)
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

    // Check if app was opened from terminated state via notification
    final initialMessage = await _fcm.getInitialMessage();
    if (initialMessage != null) {
      // Delay to let the app finish building before switching tabs
      Future.delayed(const Duration(milliseconds: 800), () {
        _handleNotificationTap(initialMessage);
      });
    }
  }

  // ────────────────────── Permission ──────────────────────

  Future<void> _requestPermission() async {
    final settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
      criticalAlert: false,
      announcement: false,
    );

    print('Notification permission: ${settings.authorizationStatus}');

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
    const androidChannel = AndroidNotificationChannel(
      'high_importance_channel',
      'Alert Notifications',
      description: 'Notifications for elderly care alerts',
      importance: Importance.high,
      playSound: true,
      enableVibration: true,
    );

    await _localNotifications
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(androidChannel);

    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    await _localNotifications.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: (response) {
        // User tapped a LOCAL notification (foreground banner)
        _navigateToAlerts();
      },
    );
  }

  // ────────────────────── Foreground Message Handler ──────────────────────

  void _handleForegroundMessage(RemoteMessage message) {
    print('Foreground message: ${message.notification?.title}');

    final notification = message.notification;
    if (notification == null) return;

    final severity = message.data['severity'] ?? 'INFO';

    _localNotifications.show(
      message.hashCode,
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
      payload: jsonEncode(message.data),
    );
  }

  // ────────────────────── Notification Tap Handler ──────────────────────

  void _handleNotificationTap(RemoteMessage message) {
    print('Notification tapped: ${message.data}');
    _navigateToAlerts();
  }

  /// Signal the HomeScreen to switch to the Alerts tab
  void _navigateToAlerts() {
    print('Navigating to Alerts tab');
    navigateToTabNotifier.value = 1; // 1 = Alerts tab
  }
}
