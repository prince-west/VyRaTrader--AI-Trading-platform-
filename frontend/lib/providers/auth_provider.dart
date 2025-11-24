// lib/providers/auth_provider.dart
import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/secure_storage.dart';
import '../models/user.dart';
import '../core/security/security_manager.dart';
import '../core/security/input_validator.dart';

/// Authentication state provider
/// Manages login, signup, logout, and user session
class AuthProvider extends ChangeNotifier {
  final ApiClient api;

  User? _user;
  bool _loading = false;
  String? _error;
  final bool _hasAcceptedTerms = false;
  final bool _isPaperTrading = false;

  AuthProvider({required this.api});

  // ============================================================================
  // GETTERS
  // ============================================================================

  User? get user => _user;
  bool get loading => _loading;
  String? get error => _error;
  bool get isAuthenticated => _user != null;
  bool get hasAcceptedTerms => _hasAcceptedTerms;
  bool get isPaperTrading => _isPaperTrading;

  String? get userId => _user?.id;
  String? get userEmail => _user?.email;
  String? get userName => _user?.fullName;

  // ============================================================================
  // PRIVATE HELPERS
  // ============================================================================

  void _setLoading(bool v) {
    _loading = v;
    notifyListeners();
  }

  void _setError(String? e) {
    _error = e;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
  }

  bool _isValidEmail(String email) {
    return InputValidator.isValidEmail(email);
  }

  // ============================================================================
  // AUTH ACTIONS
  // ============================================================================

  Future<bool> login(String email, String password) async {
    _setLoading(true);
    _clearError();

    try {
      // Validate inputs
      if (!_isValidEmail(email)) {
        throw Exception('Invalid email address');
      }
      if (password.isEmpty) {
        throw Exception('Password cannot be empty');
      }

      // Call backend login endpoint
      final res = await api.login(email, password);

      // Extract token (tries multiple possible server keys)
      final token = res['access_token'] ?? res['token'] ?? res['accessToken'];
      if (token == null || token.toString().isEmpty) {
        throw Exception('No authentication token returned');
      }

      // Extract user data
      final userId = res['id'] ?? res['user_id'] ?? res['userId'];
      final userEmail = res['email'] ?? email;
      final refreshToken = res['refresh_token'];

      // Save session to secure storage (uses your existing SecureStorage helpers)
      await SecureStorage.saveUserSession(
        accessToken: token.toString(),
        refreshToken: refreshToken?.toString(),
        userId: userId?.toString() ?? '',
        email: userEmail.toString(),
      );

      // Load full user profile
      await loadProfile();

      _setLoading(false);
      return true;
    } catch (e) {
      _setError('Login failed: ${e.toString()}');
      _setLoading(false);
      return false;
    }
  }

  /// Signup with email, password, and optional details
  Future<bool> signup({
    required String email,
    required String password,
    String? fullName,
    String? currency,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      if (!InputValidator.isValidEmail(email)) {
        throw Exception('Invalid email address');
      }
      if (!InputValidator.isStrongPassword(password)) {
        throw Exception('Password does not meet strength requirements');
      }

      final res = await api.signup(
        email: email,
        password: password,
        fullName: fullName,
        currency: currency,
      );

      final token = res['access_token'] ?? res['token'];
      final refreshToken = res['refresh_token'];
      final userId = res['id'] ?? res['user_id'] ?? res['userId'];

      if (token == null) {
        throw Exception('Signup succeeded but no token returned');
      }

      await SecureStorage.saveUserSession(
        accessToken: token.toString(),
        refreshToken: refreshToken?.toString(),
        userId: userId?.toString() ?? '',
        email: email,
      );

      await loadProfile();

      _setLoading(false);
      return true;
    } catch (e) {
      _setError('Signup failed: ${e.toString()}');
      _setLoading(false);
      return false;
    }
  }

  Future<void> loadProfile() async {
    try {
      final storedId = await SecureStorage.getUserId();
      if (storedId != null && storedId.isNotEmpty) {
        final res = await api.getUserProfile(storedId);
        _user = User.fromJson(res);
      } else {
        // Fallback: try /users/me endpoint (baseUrl already includes /api/v1)
        final res =
            await api.get('/users/me', params: {}, queryParams: {});
        _user = User.fromJson(res);

        // Save user ID if we got it
        if (_user?.id != null) {
          await SecureStorage.saveUserId(_user!.id);
        }
      }

      notifyListeners();
    } catch (e) {
      // ignore profile load errors quietly; user may still continue
    }
  }

  Future<void> logout() async {
    _setLoading(true);

    try {
      // Attempt to revoke refresh token server-side
      try {
        final refresh = await SecureStorage.getRefreshToken();
        if (refresh != null && refresh.isNotEmpty) {
          await api.post('/api/v1/auth/logout', {'refresh_token': refresh});
        }
      } catch (e) {
        // ignore backend errors - still clear local session
      }

      // Clear authentication data but keep app preferences
      await SecureStorage.clearUserData();

      _user = null;
      _error = null;

      _setLoading(false);
    } catch (e) {
      _setError('Logout failed: $e');
      _setLoading(false);
    }
  }

  // Password reset flow (delegates to backend)
  Future<void> requestPasswordReset(String email) async {
    if (!InputValidator.isValidEmail(email)) throw Exception('Invalid email');
    await api.post('/api/v1/auth/request-password-reset', {'email': email});
  }

  Future<void> confirmPasswordReset(String token, String newPassword) async {
    if (!InputValidator.isStrongPassword(newPassword)) {
      throw Exception('Weak password');
    }
    await api.post('/api/v1/auth/confirm-password-reset', {
      'token': token,
      'password': newPassword,
    });
  }

  // Optionally expose whether a PIN / lock is required (delegated to SecurityManager)
  Future<bool> isPinRequired() async {
    final sm = SecurityManager();
    return sm.isPinRequired();
  }
}
