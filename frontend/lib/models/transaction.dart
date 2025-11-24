// lib/models/transaction.dart

/// Transaction model representing payment transactions
/// Matches backend transactions table schema
class Transaction {
  final String id;
  final String userId;
  final String? accountId;
  final String type; // 'deposit', 'withdrawal', 'fee', 'trade'
  final double amount;
  final String currency;
  final String status; // 'pending', 'completed', 'failed', 'cancelled'
  final String? externalReference;
  final DateTime createdAt;
  final String? method; // 'momo', 'card', 'paypal', 'crypto'
  final Map<String, dynamic>? metadata;

  Transaction({
    required this.id,
    required this.userId,
    this.accountId,
    required this.type,
    required this.amount,
    this.currency = 'GHS',
    required this.status,
    this.externalReference,
    required this.createdAt,
    this.method,
    this.metadata,
  });

  /// Create Transaction from backend JSON response
  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      accountId: json['account_id']?.toString(),
      type: json['type']?.toString() ?? '',
      amount: _parseDouble(json['amount']),
      currency: json['currency']?.toString() ?? 'GHS',
      status: json['status']?.toString() ?? 'pending',
      externalReference: json['external_reference']?.toString(),
      createdAt: _parseDateTime(json['created_at']),
      method: json['method']?.toString(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  /// Convert Transaction to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      if (accountId != null) 'account_id': accountId,
      'type': type,
      'amount': amount,
      'currency': currency,
      'status': status,
      if (externalReference != null) 'external_reference': externalReference,
      'created_at': createdAt.toIso8601String(),
      if (method != null) 'method': method,
      if (metadata != null) 'metadata': metadata,
    };
  }

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  /// Check if transaction is pending
  bool get isPending => status == 'pending';

  /// Check if transaction is completed
  bool get isCompleted => status == 'completed';

  /// Check if transaction is failed
  bool get isFailed => status == 'failed';

  /// Check if transaction is cancelled
  bool get isCancelled => status == 'cancelled';

  /// Check if transaction is deposit
  bool get isDeposit => type == 'deposit';

  /// Check if transaction is withdrawal
  bool get isWithdrawal => type == 'withdrawal';

  /// Check if transaction is fee
  bool get isFee => type == 'fee';

  /// Check if transaction is trade-related
  bool get isTrade => type == 'trade';

  /// Get formatted date
  String get formattedDate {
    final now = DateTime.now();
    final difference = now.difference(createdAt);

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        if (difference.inMinutes == 0) {
          return 'Just now';
        }
        return '${difference.inMinutes}m ago';
      }
      return '${difference.inHours}h ago';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return '${createdAt.day}/${createdAt.month}/${createdAt.year}';
    }
  }

  /// Get display amount (with + or - prefix)
  String get displayAmount {
    final prefix = isDeposit ? '+' : '-';
    return '$prefix$amount';
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /// Copy with method
  Transaction copyWith({
    String? id,
    String? userId,
    String? accountId,
    String? type,
    double? amount,
    String? currency,
    String? status,
    String? externalReference,
    DateTime? createdAt,
    String? method,
    Map<String, dynamic>? metadata,
  }) {
    return Transaction(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      accountId: accountId ?? this.accountId,
      type: type ?? this.type,
      amount: amount ?? this.amount,
      currency: currency ?? this.currency,
      status: status ?? this.status,
      externalReference: externalReference ?? this.externalReference,
      createdAt: createdAt ?? this.createdAt,
      method: method ?? this.method,
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
  static DateTime _parseDateTime(dynamic value) {
    if (value == null) return DateTime.now();
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value) ?? DateTime.now();
    return DateTime.now();
  }
}

// ============================================================================
// TRANSACTION SUMMARY (for statistics)
// ============================================================================

/// Summary of transaction statistics
class TransactionSummary {
  final double totalDeposits;
  final double totalWithdrawals;
  final double totalFees;
  final int depositCount;
  final int withdrawalCount;
  final DateTime? lastDeposit;
  final DateTime? lastWithdrawal;

  TransactionSummary({
    required this.totalDeposits,
    required this.totalWithdrawals,
    required this.totalFees,
    required this.depositCount,
    required this.withdrawalCount,
    this.lastDeposit,
    this.lastWithdrawal,
  });

  /// Calculate from list of transactions
  factory TransactionSummary.fromTransactions(List<Transaction> transactions) {
    final deposits = transactions
        .where((t) => t.isDeposit && t.isCompleted)
        .toList();
    final withdrawals = transactions
        .where((t) => t.isWithdrawal && t.isCompleted)
        .toList();
    final fees = transactions.where((t) => t.isFee && t.isCompleted).toList();

    return TransactionSummary(
      totalDeposits: deposits.fold(0.0, (sum, t) => sum + t.amount),
      totalWithdrawals: withdrawals.fold(0.0, (sum, t) => sum + t.amount),
      totalFees: fees.fold(0.0, (sum, t) => sum + t.amount),
      depositCount: deposits.length,
      withdrawalCount: withdrawals.length,
      lastDeposit: deposits.isEmpty
          ? null
          : deposits
                .map((t) => t.createdAt)
                .reduce((a, b) => a.isAfter(b) ? a : b),
      lastWithdrawal: withdrawals.isEmpty
          ? null
          : withdrawals
                .map((t) => t.createdAt)
                .reduce((a, b) => a.isAfter(b) ? a : b),
    );
  }

  /// Get net flow (deposits - withdrawals)
  double get netFlow => totalDeposits - totalWithdrawals;

  /// Check if user has deposited
  bool get hasDeposited => depositCount > 0;

  /// Check if user has withdrawn
  bool get hasWithdrawn => withdrawalCount > 0;
}
