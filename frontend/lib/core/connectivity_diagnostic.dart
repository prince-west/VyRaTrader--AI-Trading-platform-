// lib/core/connectivity_diagnostic.dart
import 'package:http/http.dart' as http;
import 'api_client.dart';

class ConnectivityDiagnostic {
  static Future<Map<String, bool>> testAllEndpoints(ApiClient apiClient) async {
    final results = <String, bool>{};
    
    // Test endpoints (baseUrl already includes /api/v1, so use relative paths)
    final endpoints = [
      '/health',
      '/portfolio/portfolio',
      '/portfolio/stats', 
      '/trades/recent',
      '/payments/transactions/recent',
      '/notifications/count',
      '/ai/chat',
    ];
    
    for (final endpoint in endpoints) {
      try {
        // baseUrl already includes /api/v1, just append endpoint
        final base = apiClient.baseUrl.endsWith('/') 
            ? apiClient.baseUrl.substring(0, apiClient.baseUrl.length - 1)
            : apiClient.baseUrl;
        final uri = Uri.parse('$base$endpoint');
        http.Response response;
        
        // AI chat endpoint requires POST
        if (endpoint == '/ai/chat') {
          response = await http.post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: '{"message": "test"}',
          ).timeout(const Duration(seconds: 5));
        } else {
          response = await http.get(uri).timeout(const Duration(seconds: 5));
        }
        
        results[endpoint] = response.statusCode == 200;
        print('${results[endpoint]! ? "✅" : "❌"} $endpoint (${response.statusCode})');
      } catch (e) {
        results[endpoint] = false;
        print('❌ $endpoint - Error: $e');
      }
    }
    
    return results;
  }
  
  static void printDiagnosticResults(Map<String, bool> results) {
    print('\n🔍 Connectivity Diagnostic Results:');
    print('=' * 50);
    
    int successCount = 0;
    for (final entry in results.entries) {
      final status = entry.value ? '✅' : '❌';
      print('$status ${entry.key}');
      if (entry.value) successCount++;
    }
    
    print('=' * 50);
    print('📊 Success Rate: $successCount/${results.length} (${(successCount/results.length*100).toStringAsFixed(1)}%)');
    
    if (successCount == results.length) {
      print('🎉 All endpoints are reachable!');
    } else {
      print('⚠️  Some endpoints are unreachable. Check backend status.');
    }
  }
}
