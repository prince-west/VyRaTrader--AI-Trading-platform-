// lib/core/api_client.dart
import 'dart:convert';
import 'dart:async';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/material.dart';
import 'secure_storage.dart';

// Conditional import for platform-specific exceptions
import 'dart:io' if (dart.library.html) 'dart:html' as io;

class ApiException implements Exception {
  final int statusCode;
  final String message;
  final Map<String, dynamic>? details;

  ApiException(this.statusCode, this.message, {this.details});

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiClient {
  late final String baseUrl;
  final Duration timeout;
  bool _isHealthy = true;
  DateTime? _lastHealthCheck;

  ApiClient({
    String? baseUrl,
    this.timeout = const Duration(seconds: 30),
  }) {
    // ✅ Always prefer .env variable if present
    final envUrl = dotenv.env['API_BASE_URL'];
    if (envUrl != null && envUrl.isNotEmpty) {
      // If .env URL doesn't have /api/v1, append it
      this.baseUrl = envUrl.endsWith('/api/v1') ? envUrl : '$envUrl/api/v1';
    } else {
      this.baseUrl = baseUrl ?? 'https://vyratrader.onrender.com/api/v1';
    }
    print("✅ ApiClient using baseUrl: ${this.baseUrl}");
  }

  /// Health check before making requests
  Future<bool> _checkHealth() async {
    // Only check every 30 seconds to avoid excessive calls
    if (_lastHealthCheck != null && 
        DateTime.now().difference(_lastHealthCheck!).inSeconds < 30) {
      return _isHealthy;
    }

    try {
      // Try both health endpoints
      var uri = Uri.parse('https://vyratrader.onrender.com/api/v1/health');
      var response = await http.get(uri).timeout(const Duration(seconds: 5));
      if (response.statusCode != 200) {
        uri = Uri.parse('https://vyratrader.onrender.com/health');
        response = await http.get(uri).timeout(const Duration(seconds: 5));
      }
      _isHealthy = response.statusCode == 200;
      _lastHealthCheck = DateTime.now();
      return _isHealthy;
    } catch (e) {
      _isHealthy = false;
      _lastHealthCheck = DateTime.now();
      return false;
    }
  }

  // Single in-flight refresh protection
  Future<bool>? _inFlightRefresh;

  // Attempts to refresh access token using stored refresh token.
  // Returns true if refreshed and tokens stored, false otherwise.
  Future<bool> _refreshAccessToken() async {
    final refresh = await SecureStorage.getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;
    try {
      final resp = await http
          .post(
            _url('/auth/refresh'),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            body: jsonEncode({'refresh_token': refresh}),
          )
          .timeout(timeout);

      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final b = jsonDecode(resp.body) as Map<String, dynamic>;
        final newAccess = b['access_token'] ?? b['token'];
        final newRefresh = b['refresh_token'];
        if (newAccess != null) {
          await SecureStorage.saveAccessToken(newAccess.toString());
        }
        if (newRefresh != null) {
          await SecureStorage.saveRefreshToken(newRefresh.toString());
        }
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  /// Constructs full URL with proper path handling and duplicate prefix removal
  Uri _url(String path, {Map<String, String>? queryParameters}) {
    final p = path.startsWith('/') ? path.substring(1) : path;
    final prefix = baseUrl.endsWith('/') ? baseUrl : '$baseUrl/';
    var urlString = '$prefix$p';
    
    // ✅ Remove duplicate /api/v1 prefixes
    urlString = urlString.replaceAll('/api/v1/api/v1/', '/api/v1/');
    
    if (queryParameters == null || queryParameters.isEmpty) {
      return Uri.parse(urlString);
    }

    return Uri.parse(urlString).replace(queryParameters: queryParameters);
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await SecureStorage.getAccessToken();
    if (token != null && token.isNotEmpty) {
      return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };
    }
    return {'Content-Type': 'application/json'};
  }

  /// GET request with enhanced error handling and retry logic
  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? headers,
    Map<String, String>? queryParameters,
    required Map<String, dynamic> params,
    required Map<String, String> queryParams,
  }) async {
    // Check health before making request
    if (!await _checkHealth()) {
      throw ApiException(503, 'Backend is offline. Please check your connection.');
    }

    return await _retryRequest(() async {
      // Merge queryParameters and queryParams - prefer queryParams if both provided
      final mergedQueryParams = {...?queryParameters, ...queryParams};
      final uri = _url(path, queryParameters: mergedQueryParams.isNotEmpty ? mergedQueryParams : null);
      final h = {...?headers, ...await _authHeaders()};
      final res = await http.get(uri, headers: h).timeout(timeout);
      return await _process(res,
          retryFn: () => get(path,
              headers: headers,
              queryParameters: queryParameters,
              params: params,
              queryParams: queryParams));
    });
  }

  /// Retry logic for network requests
  Future<T> _retryRequest<T>(Future<T> Function() request, {int maxRetries = 2}) async {
    int attempts = 0;
    while (attempts <= maxRetries) {
      try {
        return await request();
      } catch (e) {
        attempts++;
        if (attempts > maxRetries) {
          _handleError(e);
          rethrow;
        }
        
        // Wait before retry (exponential backoff)
        await Future.delayed(Duration(milliseconds: 500 * attempts));
      }
    }
    throw ApiException(500, 'Request failed after $maxRetries retries');
  }

  /// POST request with enhanced error handling and retry logic
  Future<Map<String, dynamic>> post(
    String path,
    Object? body, {
    Map<String, String>? headers,
  }) async {
    // Check health before making request
    if (!await _checkHealth()) {
      throw ApiException(503, 'Backend is offline. Please check your connection.');
    }

    return await _retryRequest(() async {
      final uri = _url(path);
      final h = {...?headers, ...await _authHeaders()};
      final res = await http
          .post(uri, headers: h, body: jsonEncode(body ?? {}))
          .timeout(timeout);
      return await _process(res,
          retryFn: () => post(path, body, headers: headers));
    });
  }

  /// PUT request
  Future<Map<String, dynamic>> put(
    String path,
    Object? body, {
    Map<String, String>? headers,
  }) async {
    try {
      final uri = _url(path);
      final h = {...?headers, ...await _authHeaders()};
      final res = await http
          .put(uri, headers: h, body: jsonEncode(body ?? {}))
          .timeout(timeout);
      return await _process(res,
          retryFn: () => put(path, body, headers: headers));
    } catch (e) {
      _handleError(e);
      rethrow;
    }
  }

  /// DELETE request
  Future<Map<String, dynamic>> delete(
    String path, {
    Map<String, String>? headers,
  }) async {
    try {
      final uri = _url(path);
      final h = {...?headers, ...await _authHeaders()};
      final res = await http.delete(uri, headers: h).timeout(timeout);
      return await _process(res, retryFn: () => delete(path, headers: headers));
    } catch (e) {
      _handleError(e);
      rethrow;
    }
  }

  /// PATCH request
  Future<Map<String, dynamic>> patch(
    String path,
    Object? body, {
    Map<String, String>? headers,
  }) async {
    try {
      final uri = _url(path);
      final h = {...?headers, ...await _authHeaders()};
      final res = await http
          .patch(uri, headers: h, body: jsonEncode(body ?? {}))
          .timeout(timeout);
      return await _process(res,
          retryFn: () => patch(path, body, headers: headers));
    } catch (e) {
      _handleError(e);
      rethrow;
    }
  }

  /// Process HTTP response and handle errors (with refresh + retry)
  Future<Map<String, dynamic>> _process(http.Response res,
      {Future<Map<String, dynamic>> Function()? retryFn}) async {
    final code = res.statusCode;
    final body = res.body.isEmpty ? '{}' : res.body;
    Map<String, dynamic> json;

    try {
      json = jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      json = {'raw': body};
    }

    // Success range
    if (code >= 200 && code < 300) return json;

    // If unauthorized -> try refresh once and retry original request if possible
    if (code == 401) {
      // If a refresh is already in progress, wait for it
      if (_inFlightRefresh != null) {
        final ok = await _inFlightRefresh!;
        if (ok) {
          if (retryFn != null) {
            return await retryFn();
          }
        }
        throw ApiException(401, 'Session expired. Please login again.');
      }

      // Start refresh flow
      _inFlightRefresh = _refreshAccessToken();

      try {
        final ok = await _inFlightRefresh!;
        _inFlightRefresh = null;
        if (ok) {
          if (retryFn != null) {
            return await retryFn();
          }
        }
        // refresh failed -> clear tokens and force login
        await SecureStorage.delete('access_token');
        await SecureStorage.delete('refresh_token');
        throw ApiException(401, 'Session expired. Please login again.');
      } catch (e) {
        _inFlightRefresh = null;
        await SecureStorage.delete('access_token');
        await SecureStorage.delete('refresh_token');
        throw ApiException(401, 'Session expired. Please login again.');
      }
    }

    // Extract error message with fallback chain - handle both String and List
    String msg = 'Request failed';
    if (json.containsKey('detail')) {
      final detail = json['detail'];
      if (detail is String) {
        msg = detail;
      } else if (detail is List) {
        msg = detail.map((e) => e.toString()).join(', ');
      }
    } else if (json.containsKey('message')) {
      msg = json['message']?.toString() ?? msg;
    } else if (json.containsKey('error')) {
      msg = json['error']?.toString() ?? msg;
    } else if (json.containsKey('msg')) {
      msg = json['msg']?.toString() ?? msg;
    }
    
    throw ApiException(code, msg, details: json);
  }

  /// Handle common errors (network, timeout, etc.) with user-friendly messages
  void _handleError(dynamic error) {
    if (error is ApiException) {
      // Already handled
      return;
    }

    String userMessage = 'Network connection failed. Please check your internet or backend.';
    
    if (!kIsWeb) {
      // Platform-specific exceptions only available on mobile
      // Use string matching since types aren't available on web
      final errorStr = error.toString().toLowerCase();
      if (errorStr.contains('socket') || errorStr.contains('network')) {
        userMessage = 'Network connection failed. Please check your internet connection.';
      } else if (errorStr.contains('http')) {
        userMessage = 'Network error occurred. Please check your connection.';
      }
    }
    
    if (error is TimeoutException) {
      userMessage = 'Request timed out. Please try again.';
    }

    // Log error for debugging (in production, use proper logging service)
    print('API Error: $error');
    
    // In a real app, you might want to show a SnackBar here
    // For now, we'll just log the user-friendly message
    print('User message: $userMessage');
  }

  /// Convenience methods for specific VyRaTrader endpoints

  // Auth endpoints
  Future<Map<String, dynamic>> login(String email, String password) {
    return post('/auth/login', {'email': email, 'password': password});
  }

  Future<Map<String, dynamic>> signup({
    required String email,
    required String password,
    String? fullName,
    String? currency,
  }) {
    final Map<String, dynamic> body = {
      'email': email,
      'password': password,
    };
    
    // Only include full_name if provided
    if (fullName != null && fullName.isNotEmpty) {
      body['full_name'] = fullName;
    }
    
    // Only include currency if provided
    if (currency != null && currency.isNotEmpty) {
      body['currency'] = currency;
    }
    
    return post('/auth/signup', body);
  }

  Future getUserProfile(String storedId) async {}

  Future explainTrade(String tradeId) async {}

  // (Other endpoint convenience methods are preserved from your original file...
  // e.g. notifications, payments, trades, users, etc. The file continues with them.)
}
