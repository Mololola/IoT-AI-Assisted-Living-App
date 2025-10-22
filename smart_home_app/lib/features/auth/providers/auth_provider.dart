import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthState {
  final bool isAuthenticated;
  final String? error;
  final bool isLoading;

  AuthState({
    required this.isAuthenticated,
    this.error,
    this.isLoading = false,
  });

  AuthState copyWith({bool? isAuthenticated, String? error, bool? isLoading}) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      error: error,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(AuthState(isAuthenticated: false)) {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    final prefs = await SharedPreferences.getInstance();
    final isLoggedIn = prefs.getBool('is_logged_in') ?? false;
    state = AuthState(isAuthenticated: isLoggedIn);
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    await Future.delayed(const Duration(milliseconds: 500));

    // Simple validation - accept any email/password combo
    if (email.contains('@') && password.length >= 6) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('is_logged_in', true);
      await prefs.setString('user_email', email);
      state = AuthState(isAuthenticated: true);
    } else {
      state = state.copyWith(
        isLoading: false,
        error: 'Invalid email or password (min 6 chars)',
      );
    }
  }

  Future<void> signUp(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    await Future.delayed(const Duration(milliseconds: 500));

    if (email.contains('@') && password.length >= 6) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('is_logged_in', true);
      await prefs.setString('user_email', email);
      state = AuthState(isAuthenticated: true);
    } else {
      state = state.copyWith(
        isLoading: false,
        error:
            'Invalid credentials. Email must contain @ and password must be 6+ characters.',
      );
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_logged_in', false);
    await prefs.remove('user_email');
    state = AuthState(isAuthenticated: false);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});
