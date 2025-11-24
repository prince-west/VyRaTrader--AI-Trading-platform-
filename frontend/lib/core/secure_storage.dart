// lib/core/secure_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'constants.dart';

class SecureStorage {
  static const FlutterSecureStorage _store = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  // ============================================================================
  // CORE METHODS
  // ============================================================================

  /// Write a value to secure storage
  static Future<void> write(String key, String value) async {
    try {
      await _store.write(key: key, value: value);
    } catch (e) {
      throw StorageException('Failed to write $key: $e');
    }
  }

  /// Read a value from secure storage
  static Future<String?> read(String key) async {
    try {
      return await _store.read(key: key);
    } catch (e) {
      throw StorageException('Failed to read $key: $e');
    }
  }

  /// Delete a specific key from secure storage
  static Future<void> delete(String key) async {
    try {
      await _store.delete(key: key);
    } catch (e) {
      throw StorageException('Failed to delete $key: $e');
    }
  }

  /// Clear all data from secure storage
  static Future<void> clear() async {
    try {
      await _store.deleteAll();
    } catch (e) {
      throw StorageException('Failed to clear storage: $e');
    }
  }

  /// Check if a key exists
  static Future<bool> containsKey(String key) async {
    try {
      return await _store.containsKey(key: key);
    } catch (e) {
      throw StorageException('Failed to check key $key: $e');
    }
  }

  /// Read all stored data (for debugging only - use carefully)
  static Future<Map<String, String>> readAll() async {
    try {
      return await _store.readAll();
    } catch (e) {
      throw StorageException('Failed to read all: $e');
    }
  }

  // ============================================================================
  // AUTHENTICATION HELPERS
  // ============================================================================

  /// Save access token
  static Future<void> saveAccessToken(String token) async {
    await write(StorageKeys.accessToken, token);
  }

  /// Get access token
  static Future<String?> getAccessToken() async {
    return await read(StorageKeys.accessToken);
  }

  /// Save refresh token
  static Future<void> saveRefreshToken(String token) async {
    await write(StorageKeys.refreshToken, token);
  }

  /// Get refresh token
  static Future<String?> getRefreshToken() async {
    return await read(StorageKeys.refreshToken);
  }

  /// Check if user is logged in (has valid token)
  static Future<bool> isLoggedIn() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  /// Clear authentication tokens (logout)
  static Future<void> clearAuth() async {
    await delete(StorageKeys.accessToken);
    await delete(StorageKeys.refreshToken);
    await delete(StorageKeys.userId);
    await delete(StorageKeys.userEmail);
  }

  // ============================================================================
  // USER DATA HELPERS
  // ============================================================================

  /// Save user ID
  static Future<void> saveUserId(String userId) async {
    await write(StorageKeys.userId, userId);
  }

  /// Get user ID
  static Future<String?> getUserId() async {
    return await read(StorageKeys.userId);
  }

  /// Save user email
  static Future<void> saveUserEmail(String email) async {
    await write(StorageKeys.userEmail, email);
  }

  /// Get user email
  static Future<String?> getUserEmail() async {
    return await read(StorageKeys.userEmail);
  }

  // ============================================================================
  // ONBOARDING & TERMS HELPERS
  // ============================================================================

  /// Mark Terms & Conditions as accepted
  static Future<void> setTermsAccepted(bool accepted) async {
    await write(StorageKeys.hasAcceptedTerms, accepted.toString());
  }

  /// Check if Terms & Conditions have been accepted
  static Future<bool> hasAcceptedTerms() async {
    final value = await read(StorageKeys.hasAcceptedTerms);
    return value == 'true';
  }

  // ============================================================================
  // TRADING MODE HELPERS
  // ============================================================================

  /// Set paper trading mode
  static Future<void> setPaperTradingMode(bool isPaperTrading) async {
    await write(StorageKeys.isPaperTrading, isPaperTrading.toString());
  }

  /// Check if in paper trading mode
  static Future<bool> isPaperTradingMode() async {
    final value = await read(StorageKeys.isPaperTrading);
    return value == 'true';
  }

  // ============================================================================
  // RISK LEVEL HELPERS
  // ============================================================================

  /// Save selected risk level
  static Future<void> saveRiskLevel(String riskLevel) async {
    // Validate risk level
    if (!RiskLevel.all.contains(riskLevel)) {
      throw StorageException('Invalid risk level: $riskLevel');
    }
    await write(StorageKeys.selectedRiskLevel, riskLevel);
  }

  /// Get selected risk level (defaults to medium if not set)
  static Future<String> getRiskLevel() async {
    final value = await read(StorageKeys.selectedRiskLevel);
    return value ?? RiskLevel.medium;
  }

  // ============================================================================
  // THEME HELPERS
  // ============================================================================

  /// Save theme mode (light/dark/system)
  static Future<void> saveThemeMode(String themeMode) async {
    await write(StorageKeys.themeMode, themeMode);
  }

  /// Get theme mode (defaults to 'dark' for VyRaTrader)
  static Future<String> getThemeMode() async {
    final value = await read(StorageKeys.themeMode);
    return value ?? 'dark';
  }

  // ============================================================================
  // BATCH OPERATIONS (for performance)
  // ============================================================================

  /// Save complete user session data (after login/signup)
  static Future<void> saveUserSession({
    required String accessToken,
    String? refreshToken,
    required String userId,
    required String email,
  }) async {
    await Future.wait([
      saveAccessToken(accessToken),
      if (refreshToken != null) saveRefreshToken(refreshToken),
      saveUserId(userId),
      saveUserEmail(email),
    ]);
  }

  /// Get complete user session data
  static Future<Map<String, String?>> getUserSession() async {
    final results = await Future.wait([
      getAccessToken(),
      getRefreshToken(),
      getUserId(),
      getUserEmail(),
    ]);

    return {
      'accessToken': results[0],
      'refreshToken': results[1],
      'userId': results[2],
      'email': results[3],
    };
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /// Clear all user data but keep app preferences (theme, etc.)
  static Future<void> clearUserData() async {
    await Future.wait([
      delete(StorageKeys.accessToken),
      delete(StorageKeys.refreshToken),
      delete(StorageKeys.userId),
      delete(StorageKeys.userEmail),
      delete(StorageKeys.selectedRiskLevel),
      delete(StorageKeys.isPaperTrading),
      // Keep hasAcceptedTerms and themeMode
    ]);
  }

  /// Reset app to factory state (clear everything including preferences)
  static Future<void> resetApp() async {
    await clear();
  }

  /// Check if this is first app launch
  static Future<bool> isFirstLaunch() async {
    final hasAccepted = await hasAcceptedTerms();
    final isLoggedIn = await SecureStorage.isLoggedIn();
    return !hasAccepted && !isLoggedIn;
  }

  Future<void> deleteAll() async {}
}

// ============================================================================
// CUSTOM EXCEPTION
// ============================================================================

class StorageException implements Exception {
  final String message;
  StorageException(this.message);

  @override
  String toString() => 'StorageException: $message';
}
