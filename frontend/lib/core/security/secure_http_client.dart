import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'security_manager.dart';

class SecureHttpClient extends http.BaseClient {
  final http.Client _inner;
  final SecurityManager _security = SecurityManager();

  SecureHttpClient() : _inner = _createSecureClient();

  static http.Client _createSecureClient() {
    final httpClient = HttpClient();

    // Set timeouts
    httpClient.connectionTimeout = const Duration(seconds: 10);
    httpClient.idleTimeout = const Duration(seconds: 15);

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
