// lib/models/trade.dart

/// Trade model representing a single trade execution
/// Matches backend trades table schema and /api/v1/trades endpoints
class Trade {
  final String id;
  final String userId;
  final String symbol;
  final String strategy;
  final String side; // 'buy' or 'sell'
  final double size;
  final double price;
  final String status; // 'pending', 'executed', 'cancelled', 'failed'
  final double profitLoss;
  final String currency;
  final DateTime openedAt;
  final DateTime? closedAt;
  final String? stopLoss;
  final String? takeProfit;
  final String? explanation; // AI explanation from Prince
  final Map<String, dynamic>? metadata;

  Trade({
    required this.id,
    required this.userId,
    required this.symbol,
    required this.strategy,
    required this.side,
    required this.size,
    required this.price,
    required this.status,
    this.profitLoss = 0.0,
    this.currency = 'GHS',
    required this.openedAt,
    this.closedAt,
    this.stopLoss,
    this.takeProfit,
    this.explanation,
    this.metadata,
  });

  /// Create Trade from backend JSON response
  factory Trade.fromJson(Map<String, dynamic> json) {
    return Trade(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      symbol: json['symbol']?.toString() ?? '',
      strategy: json['strategy']?.toString() ?? '',
      side: json['side']?.toString() ?? 'buy',
      size: _parseDouble(json['size']),
      price: _parseDouble(json['price']),
      status: json['status']?.toString() ?? 'pending',
      profitLoss: _parseDouble(json['profit_loss'] ?? json['pnl']),
      currency: json['currency']?.toString() ?? 'GHS',
      openedAt: _parseDateTime(
          json['opened_at'] ?? json['created_at'] ?? DateTime.now())!,
      closedAt: _parseDateTime(json['closed_at']),
      stopLoss: json['stop_loss']?.toString(),
      takeProfit: json['take_profit']?.toString(),
      explanation: json['explanation']?.toString(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  /// Convert Trade to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'symbol': symbol,
      'strategy': strategy,
      'side': side,
      'size': size,
      'price': price,
      'status': status,
      'profit_loss': profitLoss,
      'currency': currency,
      'opened_at': openedAt.toIso8601String(),
      if (closedAt != null) 'closed_at': closedAt!.toIso8601String(),
      if (stopLoss != null) 'stop_loss': stopLoss,
      if (takeProfit != null) 'take_profit': takeProfit,
      if (explanation != null) 'explanation': explanation,
      if (metadata != null) 'metadata': metadata,
    };
  }

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  /// Check if trade is open
  bool get isOpen => status == 'pending' || status == 'executed';

  /// Check if trade is closed
  bool get isClosed => status == 'closed' || closedAt != null;

  /// Check if trade is profitable
  bool get isProfitable => profitLoss > 0;

  /// Check if trade is a loss
  bool get isLoss => profitLoss < 0;

  /// Check if trade is long (buy)
  bool get isLong => side.toLowerCase() == 'buy';

  /// Check if trade is short (sell)
  bool get isShort => side.toLowerCase() == 'sell';

  /// Get trade duration
  Duration get duration {
    final end = closedAt ?? DateTime.now();
    return end.difference(openedAt);
  }

  /// Get trade value
  double get tradeValue => size * price;

  /// Get profit/loss percentage
  double get profitLossPercent {
    if (tradeValue == 0) return 0.0;
    return (profitLoss / tradeValue) * 100;
  }

  /// Get formatted duration string
  String get durationFormatted {
    final d = duration;
    if (d.inDays > 0) return '${d.inDays}d ${d.inHours % 24}h';
    if (d.inHours > 0) return '${d.inHours}h ${d.inMinutes % 60}m';
    if (d.inMinutes > 0) return '${d.inMinutes}m';
    return '${d.inSeconds}s';
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /// Copy with method for updates
  Trade copyWith({
    String? id,
    String? userId,
    String? symbol,
    String? strategy,
    String? side,
    double? size,
    double? price,
    String? status,
    double? profitLoss,
    String? currency,
    DateTime? openedAt,
    DateTime? closedAt,
    String? stopLoss,
    String? takeProfit,
    String? explanation,
    Map<String, dynamic>? metadata,
  }) {
    return Trade(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      symbol: symbol ?? this.symbol,
      strategy: strategy ?? this.strategy,
      side: side ?? this.side,
      size: size ?? this.size,
      price: price ?? this.price,
      status: status ?? this.status,
      profitLoss: profitLoss ?? this.profitLoss,
      currency: currency ?? this.currency,
      openedAt: openedAt ?? this.openedAt,
      closedAt: closedAt ?? this.closedAt,
      stopLoss: stopLoss ?? this.stopLoss,
      takeProfit: takeProfit ?? this.takeProfit,
      explanation: explanation ?? this.explanation,
      metadata: metadata ?? this.metadata,
    );
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  /// Helper to safely parse double from dynamic
  static double _parseDouble(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }

  /// Helper to safely parse DateTime
  static DateTime? _parseDateTime(dynamic value) {
    if (value == null) return null;
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value);
    return null;
  }
}

// ============================================================================
// TRADE REQUEST (for creating/simulating trades)
// ============================================================================

/// Trade request model for POST /api/v1/trades/simulate and /execute
class TradeRequest {
  final String userId;
  final String symbol;
  final String strategy;
  final String side;
  final double size;
  final String currency;
  final String? stopLoss;
  final String? takeProfit;
  final bool isPaperTrading;

  TradeRequest({
    required this.userId,
    required this.symbol,
    required this.strategy,
    required this.side,
    required this.size,
    this.currency = 'GHS',
    this.stopLoss,
    this.takeProfit,
    this.isPaperTrading = false,
  });

  Map<String, dynamic> toJson() {
    return {
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
  }
}

// ============================================================================
// TRADE SIMULATION RESULT
// ============================================================================

/// Result from POST /api/v1/trades/simulate
class TradeSimulation {
  final String symbol;
  final String strategy;
  final String side;
  final double size;
  final double estimatedPrice;
  final double expectedProfit;
  final double expectedLoss;
  final double riskRewardRatio;
  final String explanation;
  final double confidence; // 0-100

  TradeSimulation({
    required this.symbol,
    required this.strategy,
    required this.side,
    required this.size,
    required this.estimatedPrice,
    required this.expectedProfit,
    required this.expectedLoss,
    required this.riskRewardRatio,
    required this.explanation,
    required this.confidence,
  });

  factory TradeSimulation.fromJson(Map<String, dynamic> json) {
    return TradeSimulation(
      symbol: json['symbol']?.toString() ?? '',
      strategy: json['strategy']?.toString() ?? '',
      side: json['side']?.toString() ?? 'buy',
      size: Trade._parseDouble(json['size']),
      estimatedPrice: Trade._parseDouble(json['estimated_price']),
      expectedProfit: Trade._parseDouble(json['expected_profit']),
      expectedLoss: Trade._parseDouble(json['expected_loss']),
      riskRewardRatio: Trade._parseDouble(json['risk_reward_ratio']),
      explanation: json['explanation']?.toString() ?? '',
      confidence: Trade._parseDouble(json['confidence']),
    );
  }

  bool get isGoodTrade => riskRewardRatio >= 2.0 && confidence >= 60;
}

// ============================================================================
// TRADE HISTORY FILTER
// ============================================================================

/// Filter for querying trade history
class TradeHistoryFilter {
  final String? strategy;
  final String? status;
  final String? symbol;
  final DateTime? startDate;
  final DateTime? endDate;
  final int? limit;
  final int? offset;

  TradeHistoryFilter({
    this.strategy,
    this.status,
    this.symbol,
    this.startDate,
    this.endDate,
    this.limit = 50,
    this.offset = 0,
  });

  Map<String, String> toQueryParams() {
    final params = <String, String>{};
    if (strategy != null) params['strategy'] = strategy!;
    if (status != null) params['status'] = status!;
    if (symbol != null) params['symbol'] = symbol!;
    if (startDate != null) params['start_date'] = startDate!.toIso8601String();
    if (endDate != null) params['end_date'] = endDate!.toIso8601String();
    if (limit != null) params['limit'] = limit.toString();
    if (offset != null) params['offset'] = offset.toString();
    return params;
  }
}

// ============================================================================
// TRADE STATISTICS
// ============================================================================

/// Aggregate trade statistics
class TradeStats {
  final int totalTrades;
  final int winningTrades;
  final int losingTrades;
  final double winRate;
  final double totalProfit;
  final double totalLoss;
  final double netProfitLoss;
  final double averageWin;
  final double averageLoss;
  final double profitFactor;
  final double largestWin;
  final double largestLoss;

  TradeStats({
    required this.totalTrades,
    required this.winningTrades,
    required this.losingTrades,
    required this.winRate,
    required this.totalProfit,
    required this.totalLoss,
    required this.netProfitLoss,
    required this.averageWin,
    required this.averageLoss,
    required this.profitFactor,
    required this.largestWin,
    required this.largestLoss,
  });

  factory TradeStats.fromJson(Map<String, dynamic> json) {
    return TradeStats(
      totalTrades: json['total_trades'] as int? ?? 0,
      winningTrades: json['winning_trades'] as int? ?? 0,
      losingTrades: json['losing_trades'] as int? ?? 0,
      winRate: Trade._parseDouble(json['win_rate']),
      totalProfit: Trade._parseDouble(json['total_profit']),
      totalLoss: Trade._parseDouble(json['total_loss']),
      netProfitLoss: Trade._parseDouble(json['net_profit_loss']),
      averageWin: Trade._parseDouble(json['average_win']),
      averageLoss: Trade._parseDouble(json['average_loss']),
      profitFactor: Trade._parseDouble(json['profit_factor']),
      largestWin: Trade._parseDouble(json['largest_win']),
      largestLoss: Trade._parseDouble(json['largest_loss']),
    );
  }

  /// Calculate from list of trades
  factory TradeStats.fromTrades(List<Trade> trades) {
    if (trades.isEmpty) {
      return TradeStats(
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        winRate: 0.0,
        totalProfit: 0.0,
        totalLoss: 0.0,
        netProfitLoss: 0.0,
        averageWin: 0.0,
        averageLoss: 0.0,
        profitFactor: 0.0,
        largestWin: 0.0,
        largestLoss: 0.0,
      );
    }

    final winners = trades.where((t) {
      try {
        final pl = t.profitLoss;
        return !pl.isNaN && !pl.isInfinite && pl > 0;
      } catch (e) {
        return false;
      }
    }).toList();
    final losers = trades.where((t) {
      try {
        final pl = t.profitLoss;
        return !pl.isNaN && !pl.isInfinite && pl < 0;
      } catch (e) {
        return false;
      }
    }).toList();

    double totalProfit = 0.0;
    try {
      totalProfit = winners.fold<double>(0.0, (sum, t) {
        try {
          final pl = t.profitLoss;
          if (pl.isNaN || pl.isInfinite) return sum;
          return sum + pl;
        } catch (e) {
          return sum;
        }
      });
    } catch (e) {
      totalProfit = 0.0;
    }
    
    double totalLoss = 0.0;
    try {
      totalLoss = losers.fold<double>(0.0, (sum, t) {
        try {
          final pl = t.profitLoss;
          if (pl.isNaN || pl.isInfinite) return sum;
          return sum + pl.abs();
        } catch (e) {
          return sum;
        }
      });
    } catch (e) {
      totalLoss = 0.0;
    }

    final winRateValue = trades.isEmpty 
        ? 0.0 
        : (winners.length / trades.length) * 100;
    final winRate = (winRateValue.isNaN || winRateValue.isInfinite) ? 0.0 : winRateValue;
    
    final totalProfitD = (totalProfit.isNaN || totalProfit.isInfinite) ? 0.0 : totalProfit;
    final totalLossD = (totalLoss.isNaN || totalLoss.isInfinite) ? 0.0 : totalLoss;
    final netProfitLossD = ((totalProfitD - totalLossD).isNaN || (totalProfitD - totalLossD).isInfinite) ? 0.0 : (totalProfitD - totalLossD);
    
    return TradeStats(
      totalTrades: trades.length,
      winningTrades: winners.length,
      losingTrades: losers.length,
      winRate: winRate,
      totalProfit: totalProfitD,
      totalLoss: totalLossD,
      netProfitLoss: netProfitLossD,
      averageWin: winners.isEmpty 
          ? 0.0 
          : ((totalProfitD / winners.length).isNaN ? 0.0 : totalProfitD / winners.length),
      averageLoss: losers.isEmpty 
          ? 0.0 
          : ((totalLossD / losers.length).isNaN ? 0.0 : totalLossD / losers.length),
      profitFactor: totalLossD == 0 
          ? 0.0 
          : ((totalProfitD / totalLossD).isNaN ? 0.0 : totalProfitD / totalLossD),
      largestWin: winners.isEmpty
          ? 0.0
          : winners.map((t) => t.profitLoss).reduce((a, b) => a > b ? a : b),
      largestLoss: losers.isEmpty
          ? 0.0
          : losers
              .map((t) => t.profitLoss.abs())
              .reduce((a, b) => a > b ? a : b),
    );
  }
}

extension on Object? {
  // ignore: strict_top_level_inference
  operator +(double other) {}
}
