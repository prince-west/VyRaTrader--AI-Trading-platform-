// lib/core/security/biometric_auth.dart
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:local_auth/local_auth.dart';
import 'package:local_auth/error_codes.dart' as auth_error;

class BiometricAuth {
  static final BiometricAuth _instance = BiometricAuth._internal();
  factory BiometricAuth() => _instance;
  BiometricAuth._internal();

  final LocalAuthentication? _auth = kIsWeb ? null : LocalAuthentication();

  /// Check if biometric authentication is available on this device
  Future<bool> isAvailable() async {
    if (kIsWeb || _auth == null) return false;
    try {
      return await _auth!.canCheckBiometrics;
    } catch (_) {
      return false;
    }
  }

  /// Check if device is capable of biometric authentication
  Future<bool> isDeviceSupported() async {
    if (kIsWeb || _auth == null) return false;
    try {
      return await _auth!.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  /// Get list of available biometric types (fingerprint, face, iris, etc.)
  Future<List<BiometricType>> getAvailableBiometrics() async {
    if (kIsWeb || _auth == null) return [];
    try {
      return await _auth!.getAvailableBiometrics();
    } catch (_) {
      return [];
    }
  }

  /// Authenticate user with biometrics
  Future<bool> authenticate({
    required String reason,
  }) async {
    if (kIsWeb || _auth == null) return false;
    try {
      // Check if biometrics are available first
      final canCheck = await _auth!.canCheckBiometrics;
      if (!canCheck) {
        return false;
      }

      // Perform authentication
      return await _auth!.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
          useErrorDialogs: true,
          sensitiveTransaction: true,
        ),
      );
    } on Exception catch (e) {
      // Handle specific error cases
      if (e.toString().contains(auth_error.lockedOut)) {
        // Too many failed attempts
        return false;
      } else if (e.toString().contains(auth_error.notAvailable)) {
        // Biometrics not available
        return false;
      } else if (e.toString().contains(auth_error.notEnrolled)) {
        // No biometrics enrolled
        return false;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  /// Authenticate with fallback to device credentials (PIN/Pattern/Password)
  Future<bool> authenticateWithFallback({
    required String reason,
  }) async {
    if (kIsWeb || _auth == null) return false;
    try {
      final canCheck = await _auth!.canCheckBiometrics;
      if (!canCheck) {
        return false;
      }

      return await _auth!.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false, // Allow fallback to PIN/Pattern
          useErrorDialogs: true,
          sensitiveTransaction: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }

  /// Stop authentication (for cancellation)
  Future<void> stopAuthentication() async {
    if (kIsWeb || _auth == null) return;
    try {
      await _auth!.stopAuthentication();
    } catch (_) {
      // Ignore errors during stop
    }
  }

  /// Check if specific biometric type is available
  Future<bool> isBiometricTypeAvailable(BiometricType type) async {
    try {
      final available = await getAvailableBiometrics();
      return available.contains(type);
    } catch (_) {
      return false;
    }
  }

  /// Get user-friendly name for biometric type
  String getBiometricTypeName(BiometricType type) {
    switch (type) {
      case BiometricType.face:
        return 'Face ID';
      case BiometricType.fingerprint:
        return 'Fingerprint';
      case BiometricType.iris:
        return 'Iris Scan';
      case BiometricType.strong:
        return 'Strong Biometric';
      case BiometricType.weak:
        return 'Weak Biometric';
      default:
        return 'Biometric';
    }
  }

  /// Get all available biometric type names
  Future<List<String>> getAvailableBiometricNames() async {
    final types = await getAvailableBiometrics();
    return types.map((type) => getBiometricTypeName(type)).toList();
  }
}
