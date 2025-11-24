// lib/models/portfolio.dart

/// Portfolio model representing user's trading portfolio
/// Matches backend /api/v1/portfolio/{user_id} response
class Portfolio {
  final String userId;
  final String currency;
  final double availableBalance;
  final double ledgerBalance;
  final double portfolioValue;
  final List<Position> positions;
  final double totalPnL;
  final double todayPnL;
  final double returnPercent;
  final DateTime lastUpdated;

  Portfolio({
    required this.userId,
    this.currency = 'GHS',
    required this.availableBalance,
    required this.ledgerBalance,
    required this.portfolioValue,
    required this.positions,
    required this.totalPnL,
    this.todayPnL = 0.0,
    this.returnPercent = 0.0,
    required this.lastUpdated,
  });

  /// Create Portfolio from backend JSON response
  factory Portfolio.fromJson(Map<String, dynamic> json) {
    return Portfolio(
      userId: json['user_id']?.toString() ?? '',
      currency: json['currency']?.toString() ?? 'GHS',
      availableBalance: _parseDouble(json['available_balance']),
      ledgerBalance: _parseDouble(json['ledger_balance']),
      portfolioValue: _parseDouble(json['portfolio_value']),
      positions:
          (json['positions'] as List<dynamic>?)
              ?.map((p) => Position.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      totalPnL: _parseDouble(json['total_pnl'] ?? json['pnl']),
      todayPnL: _parseDouble(json['today_pnl']),
      returnPercent: _parseDouble(json['return_percent']),
      lastUpdated: _parseDateTime(json['last_updated']),
    );
  }

  /// Convert Portfolio to JSON
  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'currency': currency,
      'available_balance': availableBalance,
      'ledger_balance': ledgerBalance,
      'portfolio_value': portfolioValue,
      'positions': positions.map((p) => p.toJson()).toList(),
      'total_pnl': totalPnL,
      'today_pnl': todayPnL,
      'return_percent': returnPercent,
      'last_updated': lastUpdated.toIso8601String(),
    };
  }

  /// Check if portfolio has any open positions
  bool get hasPositions => positions.isNotEmpty;

  /// Get number of open positions
  int get positionCount => positions.length;

  /// Check if portfolio is profitable
  bool get isProfitable => totalPnL > 0;

  /// Get total invested amount
  double get totalInvested => positions.fold(
    0.0,
    (sum, position) => sum + (position.size * position.entryPrice),
  );

  /// Create empty portfolio
  factory Portfolio.empty(String userId) {
    return Portfolio(
      userId: userId,
      availableBalance: 0.0,
      ledgerBalance: 0.0,
      portfolioValue: 0.0,
      positions: [],
      totalPnL: 0.0,
      lastUpdated: DateTime.now(),
    );
  }

  /// Copy with method for updates
  Portfolio copyWith({
    String? userId,
    String? currency,
    double? availableBalance,
    double? ledgerBalance,
    double? portfolioValue,
    List<Position>? positions,
    double? totalPnL,
    double? todayPnL,
    double? returnPercent,
    DateTime? lastUpdated,
  }) {
    return Portfolio(
      userId: userId ?? this.userId,
      currency: currency ?? this.currency,
      availableBalance: availableBalance ?? this.availableBalance,
      ledgerBalance: ledgerBalance ?? this.ledgerBalance,
      portfolioValue: portfolioValue ?? this.portfolioValue,
      positions: positions ?? this.positions,
      totalPnL: totalPnL ?? this.totalPnL,
      todayPnL: todayPnL ?? this.todayPnL,
      returnPercent: returnPercent ?? this.returnPercent,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }

  /// Helper to safely parse double from dynamic
  static double _parseDouble(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }

  /// Helper to safely parse DateTime
  static DateTime _parseDateTime(dynamic value) {
    if (value == null) return DateTime.now();
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value) ?? DateTime.now();
    return DateTime.now();
  }
}

// ============================================================================
// POSITION MODEL (for holdings/open trades)
// ============================================================================

/// Individual trading position within portfolio
class Position {
  final String id;
  final String symbol;
  final String strategy;
  final String side; // 'buy' or 'sell'
  final double size;
  final double entryPrice;
  final double currentPrice;
  final double unrealizedPnL;
  final double unrealizedPnLPercent;
  final DateTime openedAt;
  final String? stopLoss;
  final String? takeProfit;

  Position({
    required this.id,
    required this.symbol,
    required this.strategy,
    required this.side,
    required this.size,
    required this.entryPrice,
    required this.currentPrice,
    required this.unrealizedPnL,
    this.unrealizedPnLPercent = 0.0,
    required this.openedAt,
    this.stopLoss,
    this.takeProfit,
  });

  /// Create Position from JSON
  factory Position.fromJson(Map<String, dynamic> json) {
    return Position(
      id: json['id']?.toString() ?? '',
      symbol: json['symbol']?.toString() ?? '',
      strategy: json['strategy']?.toString() ?? '',
      side: json['side']?.toString() ?? 'buy',
      size: Portfolio._parseDouble(json['size']),
      entryPrice: Portfolio._parseDouble(json['entry_price']),
      currentPrice: Portfolio._parseDouble(json['current_price']),
      unrealizedPnL: Portfolio._parseDouble(json['unrealized_pnl']),
      unrealizedPnLPercent: Portfolio._parseDouble(
        json['unrealized_pnl_percent'],
      ),
      openedAt: Portfolio._parseDateTime(json['opened_at']),
      stopLoss: json['stop_loss']?.toString(),
      takeProfit: json['take_profit']?.toString(),
    );
  }

  /// Convert Position to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'symbol': symbol,
      'strategy': strategy,
      'side': side,
      'size': size,
      'entry_price': entryPrice,
      'current_price': currentPrice,
      'unrealized_pnl': unrealizedPnL,
      'unrealized_pnl_percent': unrealizedPnLPercent,
      'opened_at': openedAt.toIso8601String(),
      if (stopLoss != null) 'stop_loss': stopLoss,
      if (takeProfit != null) 'take_profit': takeProfit,
    };
  }

  /// Check if position is profitable
  bool get isProfitable => unrealizedPnL > 0;

  /// Check if position is long (buy)
  bool get isLong => side.toLowerCase() == 'buy';

  /// Check if position is short (sell)
  bool get isShort => side.toLowerCase() == 'sell';

  /// Get position value at current price
  double get currentValue => size * currentPrice;

  /// Get position value at entry
  double get entryValue => size * entryPrice;

  /// Get duration position has been open
  Duration get duration => DateTime.now().difference(openedAt);

  /// Copy with method
  Position copyWith({
    String? id,
    String? symbol,
    String? strategy,
    String? side,
    double? size,
    double? entryPrice,
    double? currentPrice,
    double? unrealizedPnL,
    double? unrealizedPnLPercent,
    DateTime? openedAt,
    String? stopLoss,
    String? takeProfit,
  }) {
    return Position(
      id: id ?? this.id,
      symbol: symbol ?? this.symbol,
      strategy: strategy ?? this.strategy,
      side: side ?? this.side,
      size: size ?? this.size,
      entryPrice: entryPrice ?? this.entryPrice,
      currentPrice: currentPrice ?? this.currentPrice,
      unrealizedPnL: unrealizedPnL ?? this.unrealizedPnL,
      unrealizedPnLPercent: unrealizedPnLPercent ?? this.unrealizedPnLPercent,
      openedAt: openedAt ?? this.openedAt,
      stopLoss: stopLoss ?? this.stopLoss,
      takeProfit: takeProfit ?? this.takeProfit,
    );
  }
}

// ============================================================================
// PORTFOLIO SUMMARY (for dashboard quick view)
// ============================================================================

/// Simplified portfolio summary for dashboard display
class PortfolioSummary {
  final double totalValue;
  final double todayChange;
  final double todayChangePercent;
  final int openPositions;
  final double availableCash;

  PortfolioSummary({
    required this.totalValue,
    required this.todayChange,
    required this.todayChangePercent,
    required this.openPositions,
    required this.availableCash,
  });

  /// Create from full Portfolio
  factory PortfolioSummary.fromPortfolio(Portfolio portfolio) {
    return PortfolioSummary(
      totalValue: portfolio.portfolioValue,
      todayChange: portfolio.todayPnL,
      todayChangePercent: portfolio.returnPercent,
      openPositions: portfolio.positionCount,
      availableCash: portfolio.availableBalance,
    );
  }

  /// Create from JSON
  factory PortfolioSummary.fromJson(Map<String, dynamic> json) {
    return PortfolioSummary(
      totalValue: Portfolio._parseDouble(json['total_value']),
      todayChange: Portfolio._parseDouble(json['today_change']),
      todayChangePercent: Portfolio._parseDouble(json['today_change_percent']),
      openPositions: json['open_positions'] as int? ?? 0,
      availableCash: Portfolio._parseDouble(json['available_cash']),
    );
  }

  bool get isProfitableToday => todayChange > 0;
}

// ============================================================================
// PORTFOLIO PERFORMANCE (for charts/analytics)
// ============================================================================

/// Portfolio performance data point for charts
class PortfolioPerformance {
  final DateTime date;
  final double value;
  final double pnl;
  final double returnPercent;

  PortfolioPerformance({
    required this.date,
    required this.value,
    required this.pnl,
    required this.returnPercent,
  });

  factory PortfolioPerformance.fromJson(Map<String, dynamic> json) {
    return PortfolioPerformance(
      date: Portfolio._parseDateTime(json['date']),
      value: Portfolio._parseDouble(json['value']),
      pnl: Portfolio._parseDouble(json['pnl']),
      returnPercent: Portfolio._parseDouble(json['return_percent']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'date': date.toIso8601String(),
      'value': value,
      'pnl': pnl,
      'return_percent': returnPercent,
    };
  }
}
