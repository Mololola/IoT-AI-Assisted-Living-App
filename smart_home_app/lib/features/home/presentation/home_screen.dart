// FILE: lib/features/home/presentation/home_screen.dart
// FIXED: Listens to navigateToTabNotifier from notification_service.dart
// so tapping a notification switches to the Alerts tab.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../sensors/presentation/sensors_tab.dart';
import '../../alerts/presentation/alerts_tab.dart';
import '../../routines/presentation/routines_tab.dart';
import '../../settings/presentation/settings_tab.dart';
import '../../../core/services/notification_service.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _tabs = const [
    SensorsTab(),
    AlertsTab(),
    RoutinesTab(),
    SettingsTab(),
  ];

  @override
  void initState() {
    super.initState();
    // Listen for notification taps that want to switch tabs
    navigateToTabNotifier.addListener(_onNavigateRequest);
  }

  @override
  void dispose() {
    navigateToTabNotifier.removeListener(_onNavigateRequest);
    super.dispose();
  }

  void _onNavigateRequest() {
    final targetTab = navigateToTabNotifier.value;
    if (targetTab != null && targetTab != _currentIndex) {
      setState(() {
        _currentIndex = targetTab;
      });
      // Reset the notifier so it can fire again next time
      navigateToTabNotifier.value = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_getTitle())),
      body: IndexedStack(index: _currentIndex, children: _tabs),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.sensors_outlined),
            selectedIcon: Icon(Icons.sensors),
            label: 'Sensors',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon: Icon(Icons.notifications),
            label: 'Alerts',
          ),
          NavigationDestination(
            icon: Icon(Icons.event_note_outlined),
            selectedIcon: Icon(Icons.event_note),
            label: 'Routines',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }

  String _getTitle() {
    switch (_currentIndex) {
      case 0:
        return 'Sensors';
      case 1:
        return 'Alerts';
      case 2:
        return 'Routines';
      case 3:
        return 'Settings';
      default:
        return 'Smart Home';
    }
  }
}
