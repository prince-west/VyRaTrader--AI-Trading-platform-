/// Core Configuration for VyRaTrader
/// Handles environment variables and app-wide settings

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class Config {
  // Private constructor to prevent instantiation
  Config._();

  /// API Base URL
  /// Should be set via environment variable or defaults to localhost
  static String get apiBaseUrl {
    const envUrl = String.fromEnvironment('API_BASE_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }

    // Development defaults
    if (kDebugMode) {
      return 'http://localhost:8000';
    }

    // Production fallback (update when deployed)
    return dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
  }

  /// WebSocket URL for real-time updates
  static String get wsUrl {
    final base = apiBaseUrl
        .replaceFirst('http://', 'ws://')
        .replaceFirst('https://', 'wss://');
    return '$base/ws';
  }

  /// App Configuration
  static const String appName = 'VyRaTrader';
  static const String appVersion = '1.0.0';
  static const String aiAssistantName = 'Prince';

  /// Payment Configuration
  static const double depositFeePercent = 2.0;
  static const double withdrawalFeePercent = 5.0;

  static const Map<String, double> minimumDeposits = {
    'GHS': 500.0,
    'USD': 50.0,
    'EUR': 45.0,
    'GBP': 40.0,
    'JPY': 5000.0,
    'CAD': 65.0,
    'AUD': 70.0,
    'CHF': 45.0,
    'CNY': 320.0,
    'SEK': 450.0,
    'NGN': 20000.0,
    'ZAR': 750.0,
    'INR': 3500.0,
  };

  static const List<String> supportedCurrencies = [
    'GHS',
    'USD',
    'EUR',
    'GBP',
    'JPY',
    'CAD',
    'AUD',
    'CHF',
    'CNY',
    'SEK',
    'NGN',
    'ZAR',
    'INR',
  ];

  /// Currency Symbols
  static const Map<String, String> currencySymbols = {
    'GHS': '₵',
    'USD': '\$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CAD': 'C\$',
    'AUD': 'A\$',
    'CHF': 'CHF',
    'CNY': '¥',
    'SEK': 'kr',
    'NGN': '₦',
    'ZAR': 'R',
    'INR': '₹',
  };

  /// Risk Levels Configuration
  static const Map<String, Map<String, dynamic>> riskLevels = {
    'low': {
      'multiplier': 0.3,
      'expectedReturn': '0.5% - 2%',
      'maxVolatileAllocation': 0.10,
      'stopLoss': 0.03,
      'displayName': 'Low Risk',
      'description': 'Conservative trading with capital preservation focus',
    },
    'medium': {
      'multiplier': 0.6,
      'expectedReturn': '2% - 4%',
      'maxVolatileAllocation': 0.25,
      'stopLoss': 0.08,
      'displayName': 'Medium Risk',
      'description': 'Balanced approach with moderate growth potential',
    },
    'high': {
      'multiplier': 1.0,
      'expectedReturn': '5%+',
      'maxVolatileAllocation': 0.60,
      'stopLoss': 0.20,
      'displayName': 'High Risk',
      'description': 'Aggressive trading for maximum growth potential',
    },
  };

  /// Trading Markets
  static const List<String> supportedMarkets = [
    'crypto',
    'forex',
  ];

  /// Crypto Currencies
  static const List<String> supportedCryptos = [
    'BTC',
    'ETH',
    'USDT',
    'USDC',
    'BNB',
    'XRP',
    'ADA',
    'DOGE',
    'SOL',
    'DOT',
  ];

  /// Forex Pairs
  static const List<String> supportedForexPairs = [
    'EUR/USD',
    'GBP/USD',
    'USD/JPY',
    'USD/CHF',
    'AUD/USD',
    'USD/CAD',
    'NZD/USD',
    'EUR/GBP',
    'EUR/JPY',
    'GBP/JPY',
  ];

  /// Stock Indices
  static const List<String> supportedStockIndices = [
    'S&P 500',
    'NASDAQ',
    'FTSE 100',
    'DAX',
    'Nikkei 225',
    'Hang Seng',
  ];

  /// Payment Provider Configuration
  static const String hubtelProvider = 'hubtel';
  static const String stripeProvider = 'stripe';
  static const String paypalProvider = 'paypal';
  static const String binancePayProvider = 'binance_pay';

  /// MoMo Networks by Country
  static const Map<String, List<String>> momoNetworks = {
    'GHS': ['MTN', 'Vodafone', 'AirtelTigo'],
    'NGN': ['MTN', 'Airtel'],
    'ZAR': ['Vodacom', 'MTN'],
  };

  /// Timeout Configuration
  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration paymentTimeout = Duration(minutes: 5);
  static const Duration wsReconnectInterval = Duration(seconds: 5);

  /// Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  /// Cache Duration
  static const Duration portfolioCacheDuration = Duration(seconds: 30);
  static const Duration marketDataCacheDuration = Duration(minutes: 1);
  static const Duration transactionCacheDuration = Duration(minutes: 5);

  /// Session Configuration
  static const Duration sessionTimeout = Duration(hours: 24);
  static const Duration refreshTokenInterval = Duration(hours: 12);

  /// AI Configuration
  static const int maxChatHistory = 50;
  static const Duration aiResponseTimeout = Duration(seconds: 15);
  static const int maxRetries = 3;

  /// Notification Configuration
  static const bool enablePushNotifications = true;
  static const bool enableTradeNotifications = true;
  static const bool enablePaymentNotifications = true;
  static const bool enablePriceAlerts = true;

  /// Security Configuration
  static const int maxLoginAttempts = 5;
  static const Duration loginLockoutDuration = Duration(minutes: 15);
  static const int pinLength = 4;
  static const bool requireBiometrics = false; // Optional

  /// Terms & Conditions
  static const String termsVersion = '1.0';
  static const String privacyPolicyVersion = '1.0';

  /// Theme Configuration
  static const String primaryColorHex = '#00FFFF'; // Cyan blue
  static const String secondaryColorHex = '#001F3F'; // Dark blue
  static const String backgroundStartHex = '#000C1F'; // Very dark blue
  static const String backgroundEndHex = '#001F3F'; // Dark blue

  /// Feature Flags
  static const bool enablePaperTrading = true;
  static const bool enableAutonomousTrading = true;
  static const bool enableSocialTrading = false; // Future feature
  static const bool enableCopyTrading = false; // Future feature
  static const bool enableKYC = false; // Placeholder for now
  static const bool enable2FA = false; // Placeholder for now

  /// Legal & Compliance
  static const String companyName = 'VyRaTrader Ltd';
  static const String supportEmail = 'support@vyratrader.com';
  static const String complianceEmail = 'compliance@vyratrader.com';

  /// Social Links (optional)
  static const String websiteUrl = 'https://vyratrader.com';
  static const String twitterUrl = 'https://twitter.com/vyratrader';
  static const String discordUrl = 'https://discord.gg/vyratrader';

  /// Helper Methods

  /// Get currency symbol
  static String getCurrencySymbol(String currency) {
    return currencySymbols[currency.toUpperCase()] ?? currency;
  }

  /// Get minimum deposit for currency
  static double getMinimumDeposit(String currency) {
    return minimumDeposits[currency.toUpperCase()] ?? 500.0;
  }

  /// Check if currency is supported
  static bool isCurrencySupported(String currency) {
    return supportedCurrencies.contains(currency.toUpperCase());
  }

  /// Get risk level configuration
  static Map<String, dynamic>? getRiskLevelConfig(String level) {
    return riskLevels[level.toLowerCase()];
  }

  /// Format currency amount
  static String formatCurrency(double amount, String currency) {
    final symbol = getCurrencySymbol(currency);
    return '$symbol${amount.toStringAsFixed(2)}';
  }

  /// Get MoMo networks for currency
  static List<String> getMoMoNetworks(String currency) {
    return momoNetworks[currency.toUpperCase()] ?? [];
  }

  /// Check if MoMo is supported for currency
  static bool isMoMoSupported(String currency) {
    return momoNetworks.containsKey(currency.toUpperCase());
  }

  /// Get market display name
  static String getMarketDisplayName(String market) {
    switch (market.toLowerCase()) {
      case 'crypto':
        return 'Cryptocurrency';
      case 'forex':
        return 'Foreign Exchange';
      default:
        return market;
    }
  }

  /// Validate environment
  static bool validateEnvironment() {
    try {
      // Check if API URL is valid
      Uri.parse(apiBaseUrl);
      return true;
    } catch (e) {
      if (kDebugMode) {
        print('Invalid API URL: $apiBaseUrl');
      }
      return false;
    }
  }

  /// Get environment name
  static String get environmentName {
    if (kDebugMode) {
      return 'Development';
    } else if (kProfileMode) {
      return 'Profile';
    } else {
      return 'Production';
    }
  }

  /// Is production environment
  static bool get isProduction => !kDebugMode && !kProfileMode;

  /// Is development environment
  static bool get isDevelopment => kDebugMode;

  /// Print configuration (debug only)
  static void printConfig() {
    if (kDebugMode) {
      print('=== VyRaTrader Configuration ===');
      print('Environment: $environmentName');
      print('API Base URL: $apiBaseUrl');
      print('WebSocket URL: $wsUrl');
      print('App Version: $appVersion');
      print('Supported Currencies: ${supportedCurrencies.length}');
      print('Supported Markets: ${supportedMarkets.length}');
      print('Paper Trading: $enablePaperTrading');
      print('Autonomous Trading: $enableAutonomousTrading');
      print('===============================');
    }
  }
}
