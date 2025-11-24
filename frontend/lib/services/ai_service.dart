// lib/services/ai_service.dart
// AI Service for fetching signals with category support
// Production Ready - Complete implementation

import '../../core/api_client.dart';

enum MarketCategory {
  crypto,
  forex,
}

extension MarketCategoryExtension on MarketCategory {
  String get value {
    switch (this) {
      case MarketCategory.crypto:
        return 'crypto';
      case MarketCategory.forex:
        return 'forex';
    }
  }

  String get displayName {
    switch (this) {
      case MarketCategory.crypto:
        return 'Crypto';
      case MarketCategory.forex:
        return 'Forex';
    }
  }

  static MarketCategory fromString(String value) {
    switch (value.toLowerCase()) {
      case 'crypto':
        return MarketCategory.crypto;
      case 'forex':
        return MarketCategory.forex;
      default:
        return MarketCategory.crypto;
    }
  }
}

class AISignalResponse {
  final bool success;
  final String? signal;
  final String? action; // 'buy', 'sell', 'hold'
  final double? confidence;
  final String? rationale;
  final String? suggestedCategory; // If current category unavailable
  final String? message;
  final bool categoryUnavailable;
  final bool qualityBonus; // If this signal was allowed due to quality bonus

  AISignalResponse({
    required this.success,
    this.signal,
    this.action,
    this.confidence,
    this.rationale,
    this.suggestedCategory,
    this.message,
    this.categoryUnavailable = false,
    this.qualityBonus = false,
  });

  factory AISignalResponse.fromJson(Map<String, dynamic> json) {
    // Check if category is unavailable
    final categoryUnavailable = json['category_unavailable'] == true ||
        json['unavailable'] == true ||
        json['status'] == 'unavailable';

    return AISignalResponse(
      success: json['success'] == true || json['status'] == 'success',
      signal: json['signal'] ?? json['message'] ?? json['text'],
      action: json['action']?.toString().toLowerCase(),
      confidence: json['confidence']?.toDouble(),
      rationale: json['rationale'] ?? json['reason'] ?? json['explanation'],
      suggestedCategory: json['suggested_category'] ?? json['alternative_category'],
      message: json['message'] ?? json['error'],
      categoryUnavailable: categoryUnavailable,
      qualityBonus: json['quality_bonus'] == true,
    );
  }
}

class MarketStatus {
  final String category;
  final int baseLimit;
  final int effectiveLimit;
  final int maxLimit;
  final int used;
  final int remaining;
  final bool available;
  final bool qualityBased;

  MarketStatus({
    required this.category,
    required this.baseLimit,
    required this.effectiveLimit,
    required this.maxLimit,
    required this.used,
    required this.remaining,
    required this.available,
    required this.qualityBased,
  });

  factory MarketStatus.fromJson(String category, Map<String, dynamic> json) {
    return MarketStatus(
      category: category,
      baseLimit: json['base_limit'] ?? 2,
      effectiveLimit: json['effective_limit'] ?? json['limit'] ?? 2,
      maxLimit: json['max_limit'] ?? 4,
      used: json['used'] ?? 0,
      remaining: json['remaining'] ?? 2,
      available: json['available'] == true,
      qualityBased: json['quality_based'] == true,
    );
  }
  
  // Helper to check if quality bonus is active
  bool get hasQualityBonus => effectiveLimit > baseLimit;
  
  // Helper to check if max quality bonus is active
  bool get hasMaxQualityBonus => effectiveLimit >= maxLimit;
}

class AIStatusResponse {
  final bool available;
  final int remainingSignals;
  final int dailyLimit;
  final int usedSignals;
  final String? message;
  final Map<String, MarketStatus> markets;

  AIStatusResponse({
    required this.available,
    required this.remainingSignals,
    required this.dailyLimit,
    required this.usedSignals,
    this.message,
    required this.markets,
  });

  factory AIStatusResponse.fromJson(Map<String, dynamic> json) {
    final marketsJson = json['markets'] as Map<String, dynamic>? ?? {};
    final markets = <String, MarketStatus>{};
    
    marketsJson.forEach((category, data) {
      if (data is Map<String, dynamic>) {
        markets[category] = MarketStatus.fromJson(category, data);
      }
    });

    return AIStatusResponse(
      available: json['available'] == true && (json['remaining'] ?? 0) > 0,
      remainingSignals: json['remaining'] ?? json['remaining_signals'] ?? 0,
      dailyLimit: json['daily_limit'] ?? json['limit'] ?? 8,
      usedSignals: json['used'] ?? 0,
      message: json['message'],
      markets: markets,
    );
  }

  MarketStatus? getMarketStatus(MarketCategory category) {
    return markets[category.value];
  }
}

class AIService {
  final ApiClient apiClient;

  AIService(this.apiClient);

  /// Check daily quota status before showing ads
  Future<AIStatusResponse> checkDailyStatus() async {
    try {
      final response = await apiClient.get(
        '/ai/status',
        params: {},
        queryParams: {},
      );
      return AIStatusResponse.fromJson(response);
    } catch (e) {
      // On error, assume available to continue flow
      return AIStatusResponse(
        available: true,
        remainingSignals: 1,
        dailyLimit: 8,
        usedSignals: 0,
        message: 'Status check failed, proceeding anyway',
        markets: {}, // Empty markets map on error
      );
    }
  }

  /// Fetch AI signal for a specific category
  /// Set adWatched to true if user watched ad for bonus signal
  Future<AISignalResponse> getSignal(MarketCategory category, {bool adWatched = false}) async {
    try {
      final response = await apiClient.get(
        '/ai/signal',
        params: {},
        queryParams: {
          'category': category.value,
          'ad_watched': adWatched.toString(),
        },
      );

      return AISignalResponse.fromJson(response);
    } catch (e) {
      // Check if error indicates unavailable category
      final errorMessage = e.toString().toLowerCase();
      final isUnavailable = errorMessage.contains('unavailable') ||
          errorMessage.contains('no signal') ||
          errorMessage.contains('not found');

      if (isUnavailable) {
        return AISignalResponse(
          success: false,
          categoryUnavailable: true,
          message: 'No optimal setup found in ${category.displayName} now.',
        );
      }

      // Network or other error
      return AISignalResponse(
        success: false,
        message: 'Network connection failed. Please check your internet or backend.',
      );
    }
  }

  /// Get alternative category suggestions (exclude the failed one)
  static List<MarketCategory> getAlternativeCategories(MarketCategory exclude) {
    return MarketCategory.values.where((c) => c != exclude).toList();
  }
}

