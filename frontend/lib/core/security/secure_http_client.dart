import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'security_manager.dart';

// Conditional imports
import 'dart:io' if (dart.library.html) 'dart:html' as io;
import 'package:http/io_client.dart' if (dart.library.html) 'package:http/http.dart' as io_client;

class SecureHttpClient extends http.BaseClient {
  final http.Client _inner;
  final SecurityManager _security = SecurityManager();

  SecureHttpClient() : _inner = _createSecureClient();

  static http.Client _createSecureClient() {
    if (kIsWeb) {
      // Use standard http client for web (browser handles it)
      return http.Client();
    } else {
      // Use IO client for mobile
      final httpClient = io.HttpClient();
      httpClient.connectionTimeout = const Duration(seconds: 10);
      httpClient.idleTimeout = const Duration(seconds: 15);
      return io_client.IOClient(httpClient);
    }
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Add security headers
    final token = await _security.getAccessToken();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    // Add standard headers
    request.headers['X-App-Version'] = '1.0.0';
    request.headers['X-Platform'] = 'flutter';

    return _inner.send(request);
  }
}
