// lib/core/constants.dart

// ============================================================================
// PAYMENT CONSTANTS
// ============================================================================

/// Minimum deposit amount in GHS (enforced by backend)
const double kMinDepositGHS = 500.0;

/// Deposit fee percentage (2%)
const double kDepositFeePercent = 2.0;

/// Withdrawal fee percentage (5%)
const double kWithdrawalFeePercent = 5.0;

/// Supported currencies (expanded for global trading)
const List<String> kSupportedCurrencies = [
  'GHS', // Ghana Cedi
  'USD', // US Dollar
  'EUR', // Euro
  'GBP', // British Pound
  'JPY', // Japanese Yen
  'CAD', // Canadian Dollar
  'AUD', // Australian Dollar
  'CHF', // Swiss Franc
  'CNY', // Chinese Yuan
  'SEK', // Swedish Krona
  'NGN', // Nigerian Naira
  'ZAR', // South African Rand
  'INR', // Indian Rupee
];

/// Default currency
const String kDefaultCurrency = 'GHS';

/// Currency display names
const Map<String, String> kCurrencyNames = {
  'GHS': 'Ghana Cedi',
  'USD': 'US Dollar',
  'EUR': 'Euro',
  'GBP': 'British Pound',
  'JPY': 'Japanese Yen',
  'CAD': 'Canadian Dollar',
  'AUD': 'Australian Dollar',
  'CHF': 'Swiss Franc',
  'CNY': 'Chinese Yuan',
  'SEK': 'Swedish Krona',
  'NGN': 'Nigerian Naira',
  'ZAR': 'South African Rand',
  'INR': 'Indian Rupee',
};

/// Currency symbols
const Map<String, String> kCurrencySymbols = {
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

// ============================================================================
// PAYMENT METHODS
// ============================================================================

/// Available deposit/withdrawal methods
class PaymentMethods {
  static const String momo = 'momo';
  static const String card = 'card';
  static const String paypal = 'paypal';
  static const String crypto = 'crypto';

  static const List<String> all = [momo, card, paypal, crypto];

  static const Map<String, String> displayNames = {
    momo: 'Mobile Money',
    card: 'Bank Card',
    paypal: 'PayPal',
    crypto: 'Cryptocurrency',
  };
}

/// Mobile Money providers
class MoMoProviders {
  static const String mtn = 'MTN';
  static const String vodafone = 'Vodafone';
  static const String airtelTigo = 'AirtelTigo';

  static const List<String> all = [mtn, vodafone, airtelTigo];
}

/// Supported cryptocurrencies
class CryptoAssets {
  static const String usdt = 'USDT';
  static const String usdc = 'USDC';
  static const String btc = 'BTC';
  static const String eth = 'ETH';

  static const List<String> all = [usdt, usdc, btc, eth];

  static const Map<String, String> displayNames = {
    usdt: 'Tether (USDT)',
    usdc: 'USD Coin (USDC)',
    btc: 'Bitcoin (BTC)',
    eth: 'Ethereum (ETH)',
  };
}

// ============================================================================
// RISK LEVELS
// ============================================================================

/// Risk levels for trading
class RiskLevel {
  static const String low = 'low';
  static const String medium = 'medium';
  static const String high = 'high';

  static const List<String> all = [low, medium, high];
}

/// Risk profile configurations (matches backend)
class RiskProfiles {
  static const Map<String, Map<String, dynamic>> profiles = {
    RiskLevel.low: {
      'multiplier': 0.3,
      'expected_return_min': 0.5,
      'expected_return_max': 2.0,
      'max_volatile_allocation': 10,
      'stop_loss_percent': 2.5,
      'display_name': 'Low Risk',
      'description': 'Conservative strategy focused on capital preservation',
    },
    RiskLevel.medium: {
      'multiplier': 0.6,
      'expected_return_min': 2.0,
      'expected_return_max': 4.0,
      'max_volatile_allocation': 25,
      'stop_loss_percent': 6.5,
      'display_name': 'Medium Risk',
      'description': 'Balanced approach with moderate growth potential',
    },
    RiskLevel.high: {
      'multiplier': 1.0,
      'expected_return_min': 5.0,
      'expected_return_max': 15.0,
      'max_volatile_allocation': 60,
      'stop_loss_percent': 15.0,
      'display_name': 'High Risk',
      'description': 'Aggressive strategy targeting maximum returns',
    },
  };
}

// ============================================================================
// TRADING STRATEGIES
// ============================================================================

/// Available trading strategies (matches backend ai_ensemble.py)
// TRADING STRATEGIES
// lib/constants/constants.dart
// Matches backend/app/strategies/ imports — 1:1 alignment
class TradingStrategies {
  static const String trend = 'trend';
  static const String momentum = 'momentum';
  static const String meanReversion = 'mean_reversion';
  static const String arbitrage = 'arbitrage';
  static const String breakout = 'breakout';
  static const String volatilityBreakout = 'volatility_breakout';
  static const String sentimentFilter = 'sentiment_filter';
  static const String sentiment = 'sentiment';
  static const String socialCopy = 'social_copy'; // Permanent social copy strategy

  // Full list including internal strategies (for backend communication)
  static const List<String> all = [
    trend,
    momentum,
    meanReversion,
    arbitrage,
    breakout,
    volatilityBreakout,
    sentimentFilter,
    sentiment,
    socialCopy, // Internal strategy - aggregates external platform signals (hidden from users)
  ];
  
  // User-facing strategies (excludes internal strategies like social_copy)
  static const List<String> userVisible = [
    trend,
    momentum,
    meanReversion,
    arbitrage,
    breakout,
    volatilityBreakout,
    sentimentFilter,
    sentiment,
    // social_copy is excluded - internal strategy only
  ];

  static const Map<String, String> displayNames = {
    trend: 'Trend Following',
    momentum: 'Momentum',
    meanReversion: 'Mean Reversion',
    arbitrage: 'Arbitrage',
    breakout: 'Breakout',
    volatilityBreakout: 'Volatility Breakout',
    sentimentFilter: 'Sentiment Filter',
    sentiment: 'Sentiment',
    socialCopy: 'Social Copy', // Internal - not shown to users
  };

  static const Map<String, String> descriptions = {
    trend: 'Follows overall market direction using EMA/SMA crossovers.',
    momentum: 'Trades on RSI and price acceleration indicators.',
    meanReversion: 'Buys dips and sells rallies near Bollinger Bands.',
    arbitrage: 'Exploits cross-exchange or cross-asset price inefficiencies.',
    breakout: 'Enters when price breaks key resistance or support zones.',
    volatilityBreakout: 'Targets strong moves after volatility compression.',
    sentimentFilter: 'Analyzes news and social sentiment to confirm trades.',
    sentiment: 'Trades based on overall market sentiment analysis.',
    socialCopy: 'Internal strategy - aggregates external platform signals.', // Internal only
  };
}

// ============================================================================
// TRADE TYPES
// ============================================================================

class TradeType {
  static const String buy = 'buy';
  static const String sell = 'sell';
}

class TradeStatus {
  static const String pending = 'pending';
  static const String executed = 'executed';
  static const String cancelled = 'cancelled';
  static const String failed = 'failed';
}

// ============================================================================
// UI CONSTANTS
// ============================================================================

/// App theme colors (cyan blue neon theme from blueprint)
class AppColors {
  static const int primaryCyan = 0x00FFFF;
  static const int darkBgStart = 0x000C1F;
  static const int darkBgEnd = 0x001F3F;
  static const int neonBlue = 0x00D9FF;
  static const int electricBlue = 0x0099FF;
}

/// Animation durations
class AppDurations {
  static const int shortMs = 200;
  static const int mediumMs = 400;
  static const int longMs = 600;
}

/// Text sizes
class AppTextSizes {
  static const double small = 12.0;
  static const double medium = 14.0;
  static const double large = 16.0;
  static const double xlarge = 20.0;
  static const double xxlarge = 24.0;
}

/// Spacing
class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
}

// ============================================================================
// API CONSTANTS
// ============================================================================

/// API endpoints base paths
class ApiPaths {
  static const String auth = '/api/v1/auth';
  static const String users = '/api/v1/users';
  static const String payments = '/api/v1/payments';
  static const String trades = '/api/v1/trades';
  static const String portfolio = '/api/v1/portfolio';
  static const String ai = '/api/v1/ai';
  static const String notifications = '/api/v1/notifications';
}

/// Request timeouts
class ApiTimeouts {
  static const int defaultSeconds = 30;
  static const int uploadSeconds = 60;
  static const int downloadSeconds = 90;
}

// ============================================================================
// STORAGE KEYS
// ============================================================================

/// Secure storage keys
class StorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
  static const String userId = 'user_id';
  static const String userEmail = 'user_email';
  static const String hasAcceptedTerms = 'has_accepted_terms';
  static const String isPaperTrading = 'is_paper_trading';
  static const String selectedRiskLevel = 'selected_risk_level';
  static const String themeMode = 'theme_mode';
}

// ============================================================================
// VALIDATION CONSTANTS
// ============================================================================

/// Password requirements
class PasswordRules {
  static const int minLength = 8;
  static const int maxLength = 128;
  static const String pattern =
      r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$';
  static const String description =
      'Password must be at least 8 characters with letters and numbers';
}

/// Email validation
class EmailRules {
  static const String pattern =
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$';
}

// ============================================================================
// NOTIFICATION TYPES
// ============================================================================

class NotificationType {
  static const String depositConfirmed = 'deposit_confirmed';
  static const String withdrawalProcessed = 'withdrawal_processed';
  static const String tradeExecuted = 'trade_executed';
  static const String tradeClosed = 'trade_closed';
  static const String riskAlert = 'risk_alert';
  static const String princeSuggestion = 'prince_suggestion';
  static const String systemUpdate = 'system_update';
}

// ============================================================================
// ERROR MESSAGES
// ============================================================================

class ErrorMessages {
  static const String networkError =
      'Network connection failed. Please check your internet.';
  static const String serverError = 'Server error. Please try again later.';
  static const String invalidCredentials = 'Invalid email or password.';
  static const String sessionExpired =
      'Your session has expired. Please login again.';
  static const String insufficientBalance =
      'Insufficient balance for this transaction.';
  static const String minDepositNotMet = 'Minimum deposit is GHS 500.';
  static const String invalidAmount = 'Please enter a valid amount.';
  static const String genericError = 'Something went wrong. Please try again.';
}

// ============================================================================
// SUCCESS MESSAGES
// ============================================================================

class SuccessMessages {
  static const String depositInitiated = 'Deposit initiated successfully!';
  static const String withdrawalInitiated = 'Withdrawal request submitted!';
  static const String tradeExecuted = 'Trade executed successfully!';
  static const String profileUpdated = 'Profile updated successfully!';
  static const String passwordChanged = 'Password changed successfully!';
}
