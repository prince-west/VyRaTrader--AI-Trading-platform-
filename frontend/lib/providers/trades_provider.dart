// lib/providers/trades_provider.dart
import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/constants.dart';
import '../models/trade.dart';

/// Trades provider handling trade execution, simulation, and history
/// Matches backend /api/v1/trades endpoints
class TradesProvider extends ChangeNotifier {
  final ApiClient api;

  bool _loading = false;
  String? _error;
  List<Trade> _trades = [];
  TradeSimulation? _lastSimulation;
  Trade? _lastExecutedTrade;
  TradeStats? _stats;

  TradesProvider({required this.api});

  // ============================================================================
  // GETTERS
  // ============================================================================

  bool get loading => _loading;
  String? get error => _error;
  List<Trade> get trades => _trades;
  TradeSimulation? get lastSimulation => _lastSimulation;
  Trade? get lastExecutedTrade => _lastExecutedTrade;
  TradeStats? get stats => _stats;

  /// Get open trades
  List<Trade> get openTrades {
    return _trades.where((t) => t.isOpen).toList();
  }

  /// Get closed trades
  List<Trade> get closedTrades {
    return _trades.where((t) => t.isClosed).toList();
  }

  /// Get profitable trades
  List<Trade> get profitableTrades {
    return _trades.where((t) => t.isProfitable).toList();
  }

  /// Get losing trades
  List<Trade> get losingTrades {
    return _trades.where((t) => t.isLoss).toList();
  }

  /// Get total P&L
  double get totalPnL {
    return _trades.fold(0.0, (sum, trade) => sum + trade.profitLoss);
  }

  /// Get win rate
  double get winRate {
    if (_trades.isEmpty) return 0.0;
    final winners = profitableTrades.length;
    return (winners / _trades.length) * 100;
  }

  // ============================================================================
  // TRADE HISTORY
  // ============================================================================

  /// Load trade history for user
  Future<void> loadHistory({
    required String userId,
    TradeHistoryFilter? filter,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      final queryParams = filter?.toQueryParams() ?? {'user_id': userId};
      if (!queryParams.containsKey('user_id')) {
        queryParams['user_id'] = userId;
      }

      final res = await api.get(
        '/api/v1/trades/history',
        queryParameters: queryParams,
        params: {},
        queryParams: {},
      );

      final list = (res['trades'] ?? res['history'] ?? res['data'] ?? [])
          as List<dynamic>;
      _trades =
          list.map((e) => Trade.fromJson(e as Map<String, dynamic>)).toList();

      // Calculate statistics
      _stats = TradeStats.fromTrades(_trades);

      _setLoading(false);
    } catch (e) {
      _setError('Failed to load trade history: ${e.toString()}');
      _setLoading(false);
    }
  }

  /// Refresh trade history
  Future<void> refreshHistory(String userId) async {
    await loadHistory(userId: userId);
  }

  /// Load filtered history
  Future<void> loadFilteredHistory({
    required String userId,
    String? strategy,
    String? status,
    String? symbol,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final filter = TradeHistoryFilter(
      strategy: strategy,
      status: status,
      symbol: symbol,
      startDate: startDate,
      endDate: endDate,
    );

    await loadHistory(userId: userId, filter: filter);
  }

  // ============================================================================
  // TRADE SIMULATION
  // ============================================================================

  /// Simulate a trade before execution
  /// Returns expected profit, loss, and AI explanation
  Future<TradeSimulation?> simulateTrade(
    Map<String, Object?> map, {
    required String userId,
    required String symbol,
    required String strategy,
    required String side,
    required double size,
    String currency = 'GHS',
    String? stopLoss,
    String? takeProfit,
    bool isPaperTrading = false,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      // Validate strategy
      if (!TradingStrategies.all.contains(strategy)) {
        throw Exception('Invalid strategy: $strategy');
      }

      // Validate side
      if (side != 'buy' && side != 'sell') {
        throw Exception('Invalid side: $side. Must be "buy" or "sell"');
      }

      // Validate size
      if (size <= 0) {
        throw Exception('Size must be greater than 0');
      }

      // Validate currency
      if (!kSupportedCurrencies.contains(currency)) {
        throw Exception('Unsupported currency: $currency');
      }

      final payload = {
        'user_id': userId,
        'symbol': symbol,
        'strategy': strategy,
        'side': side,
        'size': size,
        'currency': currency,
        if (stopLoss != null) 'stop_loss': stopLoss,
        if (takeProfit != null) 'take_profit': takeProfit,
        'is_paper_trading': isPaperTrading,
      };

      final res = await api.post('/api/v1/trades/simulate', payload);

      _lastSimulation = TradeSimulation.fromJson(res);
      _setLoading(false);
      return _lastSimulation;
    } catch (e) {
      _setError('Trade simulation failed: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  /// Quick simulate using TradeRequest model
  Future<TradeSimulation?> simulateTradeRequest(TradeRequest request) async {
    return await simulateTrade(
      userId: request.userId,
      symbol: request.symbol,
      strategy: request.strategy,
      side: request.side,
      size: request.size,
      currency: request.currency,
      stopLoss: request.stopLoss,
      takeProfit: request.takeProfit,
      isPaperTrading: request.isPaperTrading,
      0.0 as Map<String, Object?>,
    );
  }

  // ============================================================================
  // TRADE EXECUTION
  // ============================================================================

  /// Execute a trade
  Future<Trade?> executeTrade(
    Map<String, Object?> map, {
    required String userId,
    required String symbol,
    required String strategy,
    required String side,
    required double size,
    String currency = 'GHS',
    String? stopLoss,
    String? takeProfit,
    bool isPaperTrading = false,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      // Validate inputs (same as simulation)
      if (!TradingStrategies.all.contains(strategy)) {
        throw Exception('Invalid strategy: $strategy');
      }

      if (side != 'buy' && side != 'sell') {
        throw Exception('Invalid side: $side');
      }

      if (size <= 0) {
        throw Exception('Size must be greater than 0');
      }

      if (!kSupportedCurrencies.contains(currency)) {
        throw Exception('Unsupported currency: $currency');
      }

      final payload = {
        'user_id': userId,
        'symbol': symbol,
        'strategy': strategy,
        'side': side,
        'size': size,
        'currency': currency,
        if (stopLoss != null) 'stop_loss': stopLoss,
        if (takeProfit != null) 'take_profit': takeProfit,
        'is_paper_trading': isPaperTrading,
      };

      final res = await api.post('/trades/execute', payload);

      _lastExecutedTrade = Trade.fromJson(res);

      // Add to local list
      _trades.insert(0, _lastExecutedTrade!);

      // Recalculate stats
      _stats = TradeStats.fromTrades(_trades);

      _setLoading(false);
      return _lastExecutedTrade;
    } catch (e) {
      _setError('Trade execution failed: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  /// Quick execute using TradeRequest model
  Future<Trade?> executeTradeRequest(TradeRequest request) async {
    return await executeTrade(
      userId: request.userId,
      symbol: request.symbol,
      strategy: request.strategy,
      side: request.side,
      size: request.size,
      currency: request.currency,
      stopLoss: request.stopLoss,
      takeProfit: request.takeProfit,
      isPaperTrading: request.isPaperTrading,
      0.0 as Map<String, Object?>,
    );
  }

  // ============================================================================
  // TRADE MANAGEMENT
  // ============================================================================

  /// Close a specific trade
  Future<Trade?> closeTrade(String tradeId) async {
    _setLoading(true);
    _clearError();

    try {
      final res = await api.post('/trades/$tradeId/close', {});

      final closedTrade = Trade.fromJson(res);

      // Update local list
      final index = _trades.indexWhere((t) => t.id == tradeId);
      if (index != -1) {
        _trades[index] = closedTrade;
      }

      _setLoading(false);
      return closedTrade;
    } catch (e) {
      _setError('Failed to close trade: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  /// Cancel a pending trade
  Future<bool> cancelTrade(String tradeId) async {
    _setLoading(true);
    _clearError();

    try {
      await api.post('/api/v1/trades/$tradeId/cancel', {});

      // Remove from local list or update status
      _trades.removeWhere((t) => t.id == tradeId);

      _setLoading(false);
      return true;
    } catch (e) {
      _setError('Failed to cancel trade: ${e.toString()}');
      _setLoading(false);
      return false;
    }
  }

  // ============================================================================
  // AI TRADE EXPLANATION
  // ============================================================================

  /// Get AI explanation for a trade
  Future<String?> getTradeExplanation(String tradeId) async {
    _setLoading(true);
    _clearError();

    try {
      final res = await api.explainTrade(tradeId);

      final explanation =
          res['explanation'] ?? res['rationale'] ?? 'No explanation available';

      _setLoading(false);
      return explanation.toString();
    } catch (e) {
      _setError('Failed to get explanation: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  // ============================================================================
  // STRATEGY-SPECIFIC QUERIES
  // ============================================================================

  /// Get trades by strategy
  List<Trade> getTradesByStrategy(String strategy) {
    return _trades.where((t) => t.strategy == strategy).toList();
  }

  /// Get trades by symbol
  List<Trade> getTradesBySymbol(String symbol) {
    return _trades.where((t) => t.symbol == symbol).toList();
  }

  /// Get trades by currency
  List<Trade> getTradesByCurrency(String currency) {
    return _trades.where((t) => t.currency == currency).toList();
  }

  /// Get performance by strategy
  Map<String, double> getPerformanceByStrategy() {
    final performanceMap = <String, double>{};

    for (final strategy in TradingStrategies.all) {
      final strategyTrades = getTradesByStrategy(strategy);
      if (strategyTrades.isNotEmpty) {
        final totalPnL = strategyTrades.fold(
          0.0,
          (sum, t) => sum + t.profitLoss,
        );
        performanceMap[strategy] = totalPnL;
      }
    }

    return performanceMap;
  }

  // ============================================================================
  // VALIDATION HELPERS
  // ============================================================================

  /// Validate trade parameters
  String? validateTradeParams({
    required String strategy,
    required String side,
    required double size,
    required String currency,
  }) {
    if (!TradingStrategies.all.contains(strategy)) {
      return 'Invalid strategy: $strategy';
    }

    if (side != 'buy' && side != 'sell') {
      return 'Side must be either "buy" or "sell"';
    }

    if (size <= 0) {
      return 'Size must be greater than 0';
    }

    if (!kSupportedCurrencies.contains(currency)) {
      return 'Unsupported currency: $currency';
    }

    return null;
  }

  // ============================================================================
  // CURRENCY HELPERS
  // ============================================================================

  /// Get supported currencies
  List<String> get supportedCurrencies => kSupportedCurrencies;

  /// Check if currency is supported
  bool isCurrencySupported(String currency) {
    return kSupportedCurrencies.contains(currency);
  }

  /// Get currency symbol
  String getCurrencySymbol(String currency) {
    return kCurrencySymbols[currency] ?? currency;
  }

  // ============================================================================
  // STATE MANAGEMENT HELPERS
  // ============================================================================

  void _setLoading(bool value) {
    _loading = value;
    notifyListeners();
  }

  void _setError(String message) {
    _error = message;
    notifyListeners();
  }

  void _clearError() {
    _error = null;
  }

  /// Clear cached data
  void clearCache() {
    _trades = [];
    _lastSimulation = null;
    _lastExecutedTrade = null;
    _stats = null;
    _error = null;
    notifyListeners();
  }

  /// Clear only simulation data
  void clearSimulation() {
    _lastSimulation = null;
    notifyListeners();
  }
}

extension on Object? {
  // ignore: strict_top_level_inference
  operator +(double other) {}
}
