import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecurityManager {
  static final SecurityManager _instance = SecurityManager._internal();
  factory SecurityManager() => _instance;
  SecurityManager._internal();

  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      resetOnError: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  String? _encryptionKey;

  // ========================================================================
  // INITIALIZATION
  // ========================================================================

  Future<void> initialize() async {
    _encryptionKey = await _storage.read(key: 'device_encryption_key');
    if (_encryptionKey == null) {
      _encryptionKey = _generateSecureKey();
      await _storage.write(key: 'device_encryption_key', value: _encryptionKey);
    }
  }

  String _generateSecureKey() {
    final random = Random.secure();
    final values = List<int>.generate(32, (i) => random.nextInt(256));
    return base64Url.encode(values);
  }

  // ========================================================================
  // TOKEN MANAGEMENT
  // ========================================================================

  Future<void> storeAccessToken(String token) async {
    await _storage.write(key: 'access_token', value: token);
    final expiry = DateTime.now().add(Duration(minutes: 15));
    await _storage.write(key: 'token_expiry', value: expiry.toIso8601String());
  }

  Future<void> storeRefreshToken(String token) async {
    await _storage.write(key: 'refresh_token', value: token);
  }

  Future<String?> getAccessToken() async {
    final token = await _storage.read(key: 'access_token');
    if (token == null) return null;

    // Check expiry
    final expiryStr = await _storage.read(key: 'token_expiry');
    if (expiryStr != null) {
      final expiry = DateTime.parse(expiryStr);
      if (DateTime.now().isAfter(expiry)) {
        return null; // Token expired
      }
    }

    return token;
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: 'refresh_token');
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
    await _storage.delete(key: 'token_expiry');
  }

  // ========================================================================
  // PIN SECURITY
  // ========================================================================

  String hashPin(String pin) {
    final bytes = utf8.encode(pin);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  Future<void> storePin(String pin) async {
    final hashedPin = hashPin(pin);
    await _storage.write(key: 'pin_hash', value: hashedPin);
  }

  Future<bool> verifyPin(String inputPin) async {
    final storedHash = await _storage.read(key: 'pin_hash');
    if (storedHash == null) return false;

    final inputHash = hashPin(inputPin);
    return inputHash == storedHash;
  }

  // ========================================================================
  // ACTIVITY TRACKING
  // ========================================================================

  Future<void> updateLastActivity() async {
    await _storage.write(
      key: 'last_activity',
      value: DateTime.now().toIso8601String(),
    );
  }

  Future<bool> isPinRequired() async {
    final lastActivity = await _storage.read(key: 'last_activity');
    if (lastActivity == null) return true;

    final lastTime = DateTime.parse(lastActivity);
    final diff = DateTime.now().difference(lastTime);

    return diff.inMinutes > 5; // Require PIN after 5 min
  }

  // ========================================================================
  // RATE LIMITING
  // ========================================================================

  int _loginAttempts = 0;
  DateTime? _lastLoginAttempt;

  bool isRateLimited() {
    if (_lastLoginAttempt == null) return false;

    final diff = DateTime.now().difference(_lastLoginAttempt!);

    if (_loginAttempts >= 5 && diff.inMinutes < 15) {
      return true;
    }

    if (diff.inMinutes >= 15) {
      _loginAttempts = 0;
      return false;
    }

    return false;
  }

  void recordFailedLogin() {
    _loginAttempts++;
    _lastLoginAttempt = DateTime.now();
  }

  void resetLoginAttempts() {
    _loginAttempts = 0;
    _lastLoginAttempt = null;
  }

  // ========================================================================
  // CLEANUP
  // ========================================================================

  Future<void> clearAll() async {
    await _storage.deleteAll();
    _encryptionKey = null;
    _loginAttempts = 0;
    _lastLoginAttempt = null;
  }
}
