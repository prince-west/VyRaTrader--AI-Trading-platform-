import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'security_manager.dart';

// Conditional imports for mobile platforms only
import 'dart:io' if (dart.library.html) 'dart:html' as io;
import 'package:http/io_client.dart' if (dart.library.html) 'dart:html' as io_client_stub;

class SecureHttpClient extends http.BaseClient {
  final http.Client _inner;
  final SecurityManager _security = SecurityManager();

  SecureHttpClient() : _inner = _createSecureClient();

  static http.Client _createSecureClient() {
    if (kIsWeb) {
      // Use standard http client for web (browser handles it)
      return http.Client();
    } else {
      // Use IO client for mobile - import only when needed
      // ignore: avoid_relative_lib_imports
      final httpClient = io.HttpClient();
      httpClient.connectionTimeout = const Duration(seconds: 10);
      httpClient.idleTimeout = const Duration(seconds: 15);
      // Import IOClient dynamically to avoid web compilation issues
      // ignore: avoid_relative_lib_imports
      return _createIOClient(httpClient);
    }
  }

  // Separate function to isolate IOClient usage  
  static http.Client _createIOClient(dynamic httpClient) {
    // This will only be called on mobile, so IOClient is available
    // IOClient is conditionally imported - available on mobile, stub on web
    // Since this code path is only reached when !kIsWeb, IOClient exists
    return IOClient(httpClient);
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
