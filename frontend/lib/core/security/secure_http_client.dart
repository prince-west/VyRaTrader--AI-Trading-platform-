import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'security_manager.dart';

class SecureHttpClient extends http.BaseClient {
  final http.Client _inner;
  final SecurityManager _security = SecurityManager();

  SecureHttpClient() : _inner = _createSecureClient();

  static http.Client _createSecureClient() {
    // Always use standard http client - works on both web and mobile
    // Mobile platforms can use http.Client() just fine
    return http.Client();
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
