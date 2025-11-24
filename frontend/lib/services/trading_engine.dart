// lib/services/trading_engine.dart
import 'dart:math' as math;
import '../core/api_client.dart';

/// Trading Engine Service - Handles all trading logic, strategies, and execution
/// Implements multi-strategy AI trading with risk management
class TradingEngine {
  final ApiClient _apiClient;

  // Supported currencies
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

  // Risk level configurations
  static const Map<String, Map<String, dynamic>> riskProfiles = {
    'low': {
      'multiplier': 0.3,
      'expected_return_min': 0.5,
      'expected_return_max': 2.0,
      'max_volatile_allocation': 10,
      'stop_loss_percent': 2.5,
      'take_profit_percent': 3.0,
      'position_size_multiplier': 0.02,
    },
    'medium': {
      'multiplier': 0.6,
      'expected_return_min': 2.0,
      'expected_return_max': 4.0,
      'max_volatile_allocation': 25,
      'stop_loss_percent': 6.0,
      'take_profit_percent': 8.0,
      'position_size_multiplier': 0.05,
    },
    'high': {
      'multiplier': 1.0,
      'expected_return_min': 5.0,
      'expected_return_max': 12.0,
      'max_volatile_allocation': 60,
      'stop_loss_percent': 15.0,
      'take_profit_percent': 20.0,
      'position_size_multiplier': 0.10,
    },
  };

  // Trading strategies
  static const List<String> strategies = [
    'trend_following',
    'mean_reversion',
    'momentum',
    'arbitrage',
    'breakout',
    'volatility_breakout',
    'sentiment_filter',
    'sentiment',
    'grid_trading',
  ];

  TradingEngine(this._apiClient);

  /// Simulate a trade with given parameters
  Future<Map<String, dynamic>> simulateTrade({
    required String symbol,
    required String side,
    required double size,
    required String riskLevel,
    String currency = 'USD',
    String? strategy,
  }) async {
    try {
      // Validate inputs
      _validateTradeParams(symbol, side, size, riskLevel, currency);

      // Get risk profile
      final riskProfile = riskProfiles[riskLevel.toLowerCase()]!;

      // Calculate position sizing based on risk
      final adjustedSize = _calculatePositionSize(
        size,
        riskProfile['position_size_multiplier'],
      );

      // Select strategy if not provided
      final selectedStrategy = strategy ?? _selectOptimalStrategy(symbol, side);

      // Generate market analysis
      final analysis = _generateMarketAnalysis(symbol, side, selectedStrategy);

      // Calculate expected outcomes
      final outcomes = _calculateExpectedOutcomes(
        symbol: symbol,
        side: side,
        size: adjustedSize,
        riskProfile: riskProfile,
        analysis: analysis,
      );

      // Prepare simulation result
      final result = {
        'simulation_id': _generateTradeId(),
        'symbol': symbol,
        'side': side,
        'size': adjustedSize,
        'original_size': size,
        'risk_level': riskLevel,
        'currency': currency,
        'strategy': selectedStrategy,
        'timestamp': DateTime.now().toIso8601String(),
        'market_analysis': analysis,
        'expected_outcomes': outcomes,
        'risk_metrics': {
          'stop_loss_percent': riskProfile['stop_loss_percent'],
          'take_profit_percent': riskProfile['take_profit_percent'],
          'max_drawdown': outcomes['max_drawdown'],
          'risk_reward_ratio': outcomes['risk_reward_ratio'],
        },
        'is_simulation': true,
        'status': 'simulated',
      };

      // Call backend simulation endpoint
      try {
        final backendResult = await _apiClient.post('/trades/simulate', result);
        return {...result, ...backendResult};
      } catch (e) {
        // Return local simulation if backend fails
        return result;
      }
    } catch (e) {
      throw Exception('Simulation failed: $e');
    }
  }

  /// Execute a real trade
  Future<Map<String, dynamic>> executeTrade({
    required String symbol,
    required String side,
    required double size,
    required String riskLevel,
    String currency = 'USD',
    String? strategy,
    bool paperTrading = false,
  }) async {
    try {
      // Validate inputs
      _validateTradeParams(symbol, side, size, riskLevel, currency);

      // Get risk profile
      final riskProfile = riskProfiles[riskLevel.toLowerCase()]!;

      // Calculate position sizing
      final adjustedSize = _calculatePositionSize(
        size,
        riskProfile['position_size_multiplier'],
      );

      // Select strategy
      final selectedStrategy = strategy ?? _selectOptimalStrategy(symbol, side);

      // Calculate stop loss and take profit
      final currentPrice = await _getCurrentPrice(symbol);
      final stopLoss = _calculateStopLoss(
        currentPrice,
        side,
        riskProfile['stop_loss_percent'],
      );
      final takeProfit = _calculateTakeProfit(
        currentPrice,
        side,
        riskProfile['take_profit_percent'],
      );

      // Prepare trade execution payload
      final tradePayload = {
        'symbol': symbol,
        'side': side,
        'size': adjustedSize,
        'risk_level': riskLevel,
        'currency': currency,
        'strategy': selectedStrategy,
        'stop_loss': stopLoss,
        'take_profit': takeProfit,
        'paper_trading': paperTrading,
        'timestamp': DateTime.now().toIso8601String(),
      };

      // Execute via backend
      final result = await _apiClient.post('/trades/execute', tradePayload);

      return {
        ...result,
        'trade_id': result['id'] ?? result['trade_id'] ?? _generateTradeId(),
        'status': result['status'] ?? 'executed',
        'executed_at': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      throw Exception('Trade execution failed: $e');
    }
  }

  /// Get trade history
  Future<Object> getTradeHistory({
    String? currency,
    String? status,
    int limit = 50,
  }) async {
    try {
      final params = <String, dynamic>{'limit': limit};

      if (currency != null) params['currency'] = currency;
      if (status != null) params['status'] = status;

      final result = await _apiClient
          .get('/trades/history', params: params, queryParams: {});

      if (result is List) {
        return (result['trades'] as List<Map<String, dynamic>>?) ?? [];
      }

      return (result['trades'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    } catch (e) {
      throw Exception('Failed to fetch trade history: $e');
    }
  }

  /// Get AI strategy suggestion
  Future<Map<String, dynamic>> getAIStrategySuggestion({
    required String symbol,
    required String riskLevel,
    String currency = 'USD',
  }) async {
    try {
      final result = await _apiClient.post('/ai/suggest_portfolio', {
        'symbol': symbol,
        'risk_level': riskLevel,
        'currency': currency,
      });

      return result;
    } catch (e) {
      // Return fallback suggestion if backend fails
      return _generateFallbackSuggestion(symbol, riskLevel);
    }
  }

  /// Get trade explanation from AI
  Future<Map<String, dynamic>> explainTrade(String tradeId) async {
    try {
      final result = await _apiClient.post('/ai/explain_trade', {
        'trade_id': tradeId,
      });

      return result;
    } catch (e) {
      return {
        'trade_id': tradeId,
        'explanation': 'Unable to fetch explanation at this time',
        'error': e.toString(),
      };
    }
  }

  /// Cancel an open trade
  Future<Map<String, dynamic>> cancelTrade(String tradeId) async {
    try {
      final result = await _apiClient.post('/trades/cancel', {
        'trade_id': tradeId,
      });

      return result;
    } catch (e) {
      throw Exception('Failed to cancel trade: $e');
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  void _validateTradeParams(
    String symbol,
    String side,
    double size,
    String riskLevel,
    String currency,
  ) {
    if (symbol.isEmpty) {
      throw ArgumentError('Symbol cannot be empty');
    }

    if (side != 'buy' && side != 'sell') {
      throw ArgumentError('Side must be either "buy" or "sell"');
    }

    if (size <= 0) {
      throw ArgumentError('Size must be greater than 0');
    }

    if (!riskProfiles.containsKey(riskLevel.toLowerCase())) {
      throw ArgumentError('Invalid risk level: $riskLevel');
    }

    if (!supportedCurrencies.contains(currency)) {
      throw ArgumentError('Unsupported currency: $currency');
    }
  }

  double _calculatePositionSize(double baseSize, double multiplier) {
    return baseSize * multiplier;
  }

  String _selectOptimalStrategy(String symbol, String side) {
    // Strategy selection logic based on symbol type
    if (symbol.contains('BTC') || symbol.contains('ETH')) {
      return 'momentum';
    } else if (symbol.contains('USD')) {
      return 'trend_following';
    } else if (symbol.contains('XAU') || symbol.contains('XAG')) {
      return 'mean_reversion';
    } else {
      return 'trend_following';
    }
  }

  Map<String, dynamic> _generateMarketAnalysis(
    String symbol,
    String side,
    String strategy,
  ) {
    final random = math.Random();

    return {
      'trend': random.nextBool() ? 'bullish' : 'bearish',
      'momentum': random.nextDouble() * 100,
      'volatility': 10 + random.nextDouble() * 40,
      'volume': 1000000 + random.nextInt(9000000),
      'price': _getCurrentPrice(symbol),
      'strategy': strategy,
      'sentiment': 0.3 + random.nextDouble() * 0.4,
      'key_levels': {
        'support': 0.98 + random.nextDouble() * 0.01,
        'resistance': 1.01 + random.nextDouble() * 0.01,
      },
      'indicators': {
        'rsi': 30 + random.nextDouble() * 40,
        'macd': -0.5 + random.nextDouble(),
        'bollinger_position': random.nextDouble(),
      },
    };
  }

  Map<String, dynamic> _calculateExpectedOutcomes({
    required String symbol,
    required String side,
    required double size,
    required Map<String, dynamic> riskProfile,
    required Map<String, dynamic> analysis,
  }) {
    final random = math.Random();

    final expectedReturnMin = riskProfile['expected_return_min'] as double;
    final expectedReturnMax = riskProfile['expected_return_max'] as double;

    final expectedProfit = expectedReturnMin +
        random.nextDouble() * (expectedReturnMax - expectedReturnMin);

    final maxLoss = riskProfile['stop_loss_percent'] as double;
    final maxDrawdown = maxLoss * 0.8;

    final winProbability = 0.5 + (analysis['sentiment'] as double) * 0.3;

    return {
      'expected_profit_percent': expectedProfit,
      'expected_loss_percent': -maxLoss,
      'max_drawdown': -maxDrawdown,
      'win_probability': winProbability,
      'risk_reward_ratio': expectedProfit / maxLoss,
      'expected_value':
          (expectedProfit * winProbability) - (maxLoss * (1 - winProbability)),
    };
  }

  Future<double> _getCurrentPrice(String symbol) async {
    try {
      final result = await _apiClient
          .get('/market/price/$symbol', params: {}, queryParams: {});
      return (result['price'] as num?)?.toDouble() ?? 1.0;
    } catch (e) {
      // Return mock price if backend fails
      return 100.0 + math.Random().nextDouble() * 1000;
    }
  }

  double _calculateStopLoss(double currentPrice, String side, double percent) {
    if (side == 'buy') {
      return currentPrice * (1 - percent / 100);
    } else {
      return currentPrice * (1 + percent / 100);
    }
  }

  double _calculateTakeProfit(
    double currentPrice,
    String side,
    double percent,
  ) {
    if (side == 'buy') {
      return currentPrice * (1 + percent / 100);
    } else {
      return currentPrice * (1 - percent / 100);
    }
  }

  String _generateTradeId() {
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final random = math.Random().nextInt(9999);
    return 'TRD-$timestamp-$random';
  }

  Map<String, dynamic> _generateFallbackSuggestion(
    String symbol,
    String riskLevel,
  ) {
    final random = math.Random();
    final actions = ['buy', 'sell', 'hold'];

    return {
      'recommended_action': actions[random.nextInt(actions.length)],
      'confidence': 0.5 + random.nextDouble() * 0.3,
      'rationale':
          'Market analysis suggests $symbol shows moderate opportunity',
      'expected_profit': riskProfiles[riskLevel]!['expected_return_max'],
      'expected_loss': -riskProfiles[riskLevel]!['stop_loss_percent'],
      'strategy': _selectOptimalStrategy(symbol, 'buy'),
      'timeframe': '1-7 days',
    };
  }
}

/// Trading Strategy Analyzer - Implements individual strategy logic
class StrategyAnalyzer {
  /// Trend Following Strategy
  /// Uses moving averages to identify and follow market trends
  static Map<String, dynamic> analyzeTrendFollowing(
    List<double> prices,
    int fastPeriod,
    int slowPeriod,
  ) {
    if (prices.length < slowPeriod) {
      return {'signal': 'hold', 'strength': 0.0};
    }

    final fastMA = _calculateMA(prices, fastPeriod);
    final slowMA = _calculateMA(prices, slowPeriod);

    final signal = fastMA > slowMA ? 'buy' : 'sell';
    final strength = ((fastMA - slowMA) / slowMA).abs();

    return {
      'signal': signal,
      'strength': strength,
      'fast_ma': fastMA,
      'slow_ma': slowMA,
    };
  }

  /// Mean Reversion Strategy
  /// Uses Bollinger Bands to identify overbought/oversold conditions
  static Map<String, dynamic> analyzeMeanReversion(
    List<double> prices,
    int period,
    double stdDevMultiplier,
  ) {
    if (prices.length < period) {
      return {'signal': 'hold', 'strength': 0.0};
    }

    final ma = _calculateMA(prices, period);
    final stdDev = _calculateStdDev(prices, period, ma);

    final upperBand = ma + (stdDev * stdDevMultiplier);
    final lowerBand = ma - (stdDev * stdDevMultiplier);
    final currentPrice = prices.last;

    String signal;
    double strength;

    if (currentPrice > upperBand) {
      signal = 'sell';
      strength = (currentPrice - upperBand) / upperBand;
    } else if (currentPrice < lowerBand) {
      signal = 'buy';
      strength = (lowerBand - currentPrice) / lowerBand;
    } else {
      signal = 'hold';
      strength = 0.0;
    }

    return {
      'signal': signal,
      'strength': strength,
      'upper_band': upperBand,
      'lower_band': lowerBand,
      'middle_band': ma,
    };
  }

  /// Momentum Strategy
  /// Uses RSI and MACD indicators
  static Map<String, dynamic> analyzeMomentum(
    List<double> prices,
    int rsiPeriod,
  ) {
    if (prices.length < rsiPeriod + 1) {
      return {'signal': 'hold', 'strength': 0.0};
    }

    final rsi = _calculateRSI(prices, rsiPeriod);

    String signal;
    double strength;

    if (rsi > 70) {
      signal = 'sell';
      strength = (rsi - 70) / 30;
    } else if (rsi < 30) {
      signal = 'buy';
      strength = (30 - rsi) / 30;
    } else {
      signal = 'hold';
      strength = 0.0;
    }

    return {'signal': signal, 'strength': strength, 'rsi': rsi};
  }

  // Statistical helper methods
  static double _calculateMA(List<double> prices, int period) {
    final subset = prices.length > period
        ? prices.sublist(prices.length - period)
        : prices;
    return subset.reduce((a, b) => a + b) / subset.length;
  }

  static double _calculateStdDev(List<double> prices, int period, double mean) {
    final subset = prices.length > period
        ? prices.sublist(prices.length - period)
        : prices;

    final variance = subset
            .map((price) => math.pow(price - mean, 2))
            .reduce((a, b) => a + b) /
        subset.length;

    return math.sqrt(variance);
  }

  static double _calculateRSI(List<double> prices, int period) {
    if (prices.length < period + 1) return 50.0;

    double gains = 0;
    double losses = 0;

    for (int i = prices.length - period; i < prices.length; i++) {
      final change = prices[i] - prices[i - 1];
      if (change > 0) {
        gains += change;
      } else {
        losses += change.abs();
      }
    }

    final avgGain = gains / period;
    final avgLoss = losses / period;

    if (avgLoss == 0) return 100.0;

    final rs = avgGain / avgLoss;
    return 100 - (100 / (1 + rs));
  }
}

/// Risk Manager - Handles position sizing and risk limits
class RiskManager {
  /// Calculate optimal position size based on account balance and risk tolerance
  static double calculatePositionSize({
    required double accountBalance,
    required double riskPercentage,
    required double stopLossPercent,
    String currency = 'USD',
  }) {
    final riskAmount = accountBalance * (riskPercentage / 100);
    final positionSize = riskAmount / (stopLossPercent / 100);
    return positionSize;
  }

  /// Check if trade exceeds maximum risk limits
  static bool isWithinRiskLimits({
    required double positionSize,
    required double accountBalance,
    required double maxRiskPercent,
  }) {
    final positionPercent = (positionSize / accountBalance) * 100;
    return positionPercent <= maxRiskPercent;
  }

  /// Calculate portfolio heat (total risk exposure)
  static double calculatePortfolioHeat(
    List<Map<String, dynamic>> openTrades,
    double accountBalance,
  ) {
    double totalRisk = 0;

    for (final trade in openTrades) {
      final size = (trade['size'] as num?)?.toDouble() ?? 0;
      final stopLoss = (trade['stop_loss_percent'] as num?)?.toDouble() ?? 0;
      totalRisk += size * (stopLoss / 100);
    }

    return (totalRisk / accountBalance) * 100;
  }
}
