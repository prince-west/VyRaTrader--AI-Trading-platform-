/// Payment Models for VyRaTrader
/// All data classes for payment operations

enum PaymentMethodType { momo, card, paypal, crypto }

enum MoMoNetwork { mtn, vodafone, airteltigo, airtel, vodacom }

enum CryptoCurrency { usdt, usdc, btc, eth }

enum TransactionType { deposit, withdrawal, fee, trade }

enum TransactionStatus { pending, processing, completed, failed, cancelled }

/// Payment Method
class PaymentMethod {
  final PaymentMethodType type;
  final String? provider;
  final Map<String, dynamic>? metadata;

  PaymentMethod({required this.type, this.provider, this.metadata});

  Map<String, dynamic> toJson() {
    return {
      'type': type.toString().split('.').last,
      'provider': provider,
      'metadata': metadata,
    };
  }

  factory PaymentMethod.fromJson(Map<String, dynamic> json) {
    return PaymentMethod(
      type: PaymentMethodType.values.firstWhere(
        (e) => e.toString().split('.').last == json['type'],
      ),
      provider: json['provider'],
      metadata: json['metadata'],
    );
  }

  // Convenience constructors
  factory PaymentMethod.momo(MoMoNetwork network, String phoneNumber) {
    return PaymentMethod(
      type: PaymentMethodType.momo,
      provider: 'hubtel',
      metadata: {
        'network': network.toString().split('.').last,
        'phone_number': phoneNumber,
      },
    );
  }

  factory PaymentMethod.card() {
    return PaymentMethod(type: PaymentMethodType.card, provider: 'stripe');
  }

  factory PaymentMethod.paypal() {
    return PaymentMethod(type: PaymentMethodType.paypal, provider: 'paypal');
  }

  factory PaymentMethod.crypto(CryptoCurrency currency, String network) {
    return PaymentMethod(
      type: PaymentMethodType.crypto,
      provider: 'binance_pay',
      metadata: {
        'crypto_currency': currency.toString().split('.').last,
        'network': network,
      },
    );
  }
}

/// Withdrawal Destination
class WithdrawalDestination {
  final PaymentMethodType type;
  final String? accountNumber;
  final String? phoneNumber;
  final String? email;
  final String? cryptoAddress;
  final String? cryptoNetwork;
  final Map<String, dynamic>? metadata;

  WithdrawalDestination({
    required this.type,
    this.accountNumber,
    this.phoneNumber,
    this.email,
    this.cryptoAddress,
    this.cryptoNetwork,
    this.metadata,
  });

  Map<String, dynamic> toJson() {
    return {
      'type': type.toString().split('.').last,
      'account_number': accountNumber,
      'phone_number': phoneNumber,
      'email': email,
      'crypto_address': cryptoAddress,
      'crypto_network': cryptoNetwork,
      'metadata': metadata,
    };
  }

  factory WithdrawalDestination.fromJson(Map<String, dynamic> json) {
    return WithdrawalDestination(
      type: PaymentMethodType.values.firstWhere(
        (e) => e.toString().split('.').last == json['type'],
      ),
      accountNumber: json['account_number'],
      phoneNumber: json['phone_number'],
      email: json['email'],
      cryptoAddress: json['crypto_address'],
      cryptoNetwork: json['crypto_network'],
      metadata: json['metadata'],
    );
  }
}

/// Deposit Fee Calculation
class DepositFeeCalculation {
  final double grossAmount;
  final double feePercent;
  final double feeAmount;
  final double netTradingBalance;
  final String currency;

  DepositFeeCalculation({
    required this.grossAmount,
    required this.feePercent,
    required this.feeAmount,
    required this.netTradingBalance,
    required this.currency,
  });

  Map<String, dynamic> toJson() {
    return {
      'gross_amount': grossAmount,
      'fee_percent': feePercent,
      'fee_amount': feeAmount,
      'net_trading_balance': netTradingBalance,
      'currency': currency,
    };
  }

  factory DepositFeeCalculation.fromJson(Map<String, dynamic> json) {
    return DepositFeeCalculation(
      grossAmount: (json['gross_amount'] as num).toDouble(),
      feePercent: (json['fee_percent'] as num).toDouble(),
      feeAmount: (json['fee_amount'] as num).toDouble(),
      netTradingBalance: (json['net_trading_balance'] as num).toDouble(),
      currency: json['currency'],
    );
  }
}

/// Withdrawal Fee Calculation
class WithdrawalFeeCalculation {
  final double requestedAmount;
  final double feePercent;
  final double feeAmount;
  final double netPayout;
  final String currency;

  WithdrawalFeeCalculation({
    required this.requestedAmount,
    required this.feePercent,
    required this.feeAmount,
    required this.netPayout,
    required this.currency,
  });

  Map<String, dynamic> toJson() {
    return {
      'requested_amount': requestedAmount,
      'fee_percent': feePercent,
      'fee_amount': feeAmount,
      'net_payout': netPayout,
      'currency': currency,
    };
  }

  factory WithdrawalFeeCalculation.fromJson(Map<String, dynamic> json) {
    return WithdrawalFeeCalculation(
      requestedAmount: (json['requested_amount'] as num).toDouble(),
      feePercent: (json['fee_percent'] as num).toDouble(),
      feeAmount: (json['fee_amount'] as num).toDouble(),
      netPayout: (json['net_payout'] as num).toDouble(),
      currency: json['currency'],
    );
  }
}

/// Deposit Response
class DepositResponse {
  final String transactionId;
  final double grossAmount;
  final double feePercent;
  final double feeAmount;
  final double netTradingBalance;
  final String currency;
  final String? paymentToken;
  final String? paymentUrl;
  final String? qrCode;
  final Map<String, dynamic>? paymentInstructions;
  final TransactionStatus status;
  final DateTime createdAt;

  DepositResponse({
    required this.transactionId,
    required this.grossAmount,
    required this.feePercent,
    required this.feeAmount,
    required this.netTradingBalance,
    required this.currency,
    this.paymentToken,
    this.paymentUrl,
    this.qrCode,
    this.paymentInstructions,
    required this.status,
    required this.createdAt,
  });

  factory DepositResponse.fromJson(Map<String, dynamic> json) {
    return DepositResponse(
      transactionId: json['transaction_id'],
      grossAmount: (json['gross_amount'] as num).toDouble(),
      feePercent: (json['fee_percent'] as num).toDouble(),
      feeAmount: (json['fee_amount'] as num).toDouble(),
      netTradingBalance: (json['net_trading_balance'] as num).toDouble(),
      currency: json['currency'],
      paymentToken: json['payment_token'],
      paymentUrl: json['payment_url'],
      qrCode: json['qr_code'],
      paymentInstructions: json['payment_instructions'],
      status: TransactionStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['status'],
      ),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

/// Withdrawal Response
class WithdrawalResponse {
  final String transactionId;
  final double requestedAmount;
  final double feePercent;
  final double feeAmount;
  final double netPayout;
  final String currency;
  final TransactionStatus status;
  final String? externalReference;
  final DateTime createdAt;
  final DateTime? estimatedCompletionAt;

  WithdrawalResponse({
    required this.transactionId,
    required this.requestedAmount,
    required this.feePercent,
    required this.feeAmount,
    required this.netPayout,
    required this.currency,
    required this.status,
    this.externalReference,
    required this.createdAt,
    this.estimatedCompletionAt,
  });

  factory WithdrawalResponse.fromJson(Map<String, dynamic> json) {
    return WithdrawalResponse(
      transactionId: json['transaction_id'],
      requestedAmount: (json['requested_amount'] as num).toDouble(),
      feePercent: (json['fee_percent'] as num).toDouble(),
      feeAmount: (json['fee_amount'] as num).toDouble(),
      netPayout: (json['net_payout'] as num).toDouble(),
      currency: json['currency'],
      status: TransactionStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['status'],
      ),
      externalReference: json['external_reference'],
      createdAt: DateTime.parse(json['created_at']),
      estimatedCompletionAt: json['estimated_completion_at'] != null
          ? DateTime.parse(json['estimated_completion_at'])
          : null,
    );
  }
}

/// Transaction
class Transaction {
  final String id;
  final String userId;
  final String? accountId;
  final TransactionType type;
  final double amount;
  final String currency;
  final TransactionStatus status;
  final String? externalReference;
  final PaymentMethod? paymentMethod;
  final Map<String, dynamic>? metadata;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final DateTime? completedAt;

  Transaction({
    required this.id,
    required this.userId,
    this.accountId,
    required this.type,
    required this.amount,
    required this.currency,
    required this.status,
    this.externalReference,
    this.paymentMethod,
    this.metadata,
    required this.createdAt,
    this.updatedAt,
    this.completedAt,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id'],
      userId: json['user_id'],
      accountId: json['account_id'],
      type: TransactionType.values.firstWhere(
        (e) => e.toString().split('.').last == json['type'],
      ),
      amount: (json['amount'] as num).toDouble(),
      currency: json['currency'],
      status: TransactionStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['status'],
      ),
      externalReference: json['external_reference'],
      paymentMethod: json['payment_method'] != null
          ? PaymentMethod.fromJson(json['payment_method'])
          : null,
      metadata: json['metadata'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'])
          : null,
    );
  }

  String get statusDisplay {
    switch (status) {
      case TransactionStatus.pending:
        return 'Pending';
      case TransactionStatus.processing:
        return 'Processing';
      case TransactionStatus.completed:
        return 'Completed';
      case TransactionStatus.failed:
        return 'Failed';
      case TransactionStatus.cancelled:
        return 'Cancelled';
    }
  }

  String get typeDisplay {
    switch (type) {
      case TransactionType.deposit:
        return 'Deposit';
      case TransactionType.withdrawal:
        return 'Withdrawal';
      case TransactionType.fee:
        return 'Fee';
      case TransactionType.trade:
        return 'Trade';
    }
  }
}

/// MoMo Payment Response
class MoMoPaymentResponse {
  final String transactionId;
  final String clientReference;
  final String checkoutUrl;
  final String status;
  final DateTime expiresAt;

  MoMoPaymentResponse({
    required this.transactionId,
    required this.clientReference,
    required this.checkoutUrl,
    required this.status,
    required this.expiresAt,
  });

  factory MoMoPaymentResponse.fromJson(Map<String, dynamic> json) {
    return MoMoPaymentResponse(
      transactionId: json['transaction_id'],
      clientReference: json['client_reference'],
      checkoutUrl: json['checkout_url'],
      status: json['status'],
      expiresAt: DateTime.parse(json['expires_at']),
    );
  }
}

/// Card Payment Response
class CardPaymentResponse {
  final String transactionId;
  final String paymentIntentId;
  final String clientSecret;
  final String status;
  final bool requiresAction;
  final String? nextActionUrl;

  CardPaymentResponse({
    required this.transactionId,
    required this.paymentIntentId,
    required this.clientSecret,
    required this.status,
    required this.requiresAction,
    this.nextActionUrl,
  });

  factory CardPaymentResponse.fromJson(Map<String, dynamic> json) {
    return CardPaymentResponse(
      transactionId: json['transaction_id'],
      paymentIntentId: json['payment_intent_id'],
      clientSecret: json['client_secret'],
      status: json['status'],
      requiresAction: json['requires_action'] ?? false,
      nextActionUrl: json['next_action_url'],
    );
  }
}

/// PayPal Payment Response
class PayPalPaymentResponse {
  final String transactionId;
  final String orderId;
  final String approvalUrl;
  final String status;

  PayPalPaymentResponse({
    required this.transactionId,
    required this.orderId,
    required this.approvalUrl,
    required this.status,
  });

  factory PayPalPaymentResponse.fromJson(Map<String, dynamic> json) {
    return PayPalPaymentResponse(
      transactionId: json['transaction_id'],
      orderId: json['order_id'],
      approvalUrl: json['approval_url'],
      status: json['status'],
    );
  }
}

/// Crypto Payment Response
class CryptoPaymentResponse {
  final String transactionId;
  final String depositAddress;
  final String cryptoCurrency;
  final String network;
  final double amount;
  final String qrCode;
  final String status;
  final DateTime expiresAt;
  final Map<String, dynamic>? instructions;

  CryptoPaymentResponse({
    required this.transactionId,
    required this.depositAddress,
    required this.cryptoCurrency,
    required this.network,
    required this.amount,
    required this.qrCode,
    required this.status,
    required this.expiresAt,
    this.instructions,
  });

  factory CryptoPaymentResponse.fromJson(Map<String, dynamic> json) {
    return CryptoPaymentResponse(
      transactionId: json['transaction_id'],
      depositAddress: json['deposit_address'],
      cryptoCurrency: json['crypto_currency'],
      network: json['network'],
      amount: (json['amount'] as num).toDouble(),
      qrCode: json['qr_code'],
      status: json['status'],
      expiresAt: DateTime.parse(json['expires_at']),
      instructions: json['instructions'],
    );
  }
}

/// Payment Verification
class PaymentVerification {
  final String transactionId;
  final TransactionStatus status;
  final bool isVerified;
  final String? externalReference;
  final DateTime? verifiedAt;
  final Map<String, dynamic>? details;

  PaymentVerification({
    required this.transactionId,
    required this.status,
    required this.isVerified,
    this.externalReference,
    this.verifiedAt,
    this.details,
  });

  factory PaymentVerification.fromJson(Map<String, dynamic> json) {
    return PaymentVerification(
      transactionId: json['transaction_id'],
      status: TransactionStatus.values.firstWhere(
        (e) => e.toString().split('.').last == json['status'],
      ),
      isVerified: json['is_verified'],
      externalReference: json['external_reference'],
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'])
          : null,
      details: json['details'],
    );
  }
}

/// Payment Summary (for dashboard)
class PaymentSummary {
  final double totalDeposits;
  final double totalWithdrawals;
  final double totalFees;
  final double currentBalance;
  final int depositCount;
  final int withdrawalCount;
  final String currency;
  final DateTime? lastDepositAt;
  final DateTime? lastWithdrawalAt;

  PaymentSummary({
    required this.totalDeposits,
    required this.totalWithdrawals,
    required this.totalFees,
    required this.currentBalance,
    required this.depositCount,
    required this.withdrawalCount,
    required this.currency,
    this.lastDepositAt,
    this.lastWithdrawalAt,
  });

  factory PaymentSummary.fromJson(Map<String, dynamic> json) {
    return PaymentSummary(
      totalDeposits: (json['total_deposits'] as num).toDouble(),
      totalWithdrawals: (json['total_withdrawals'] as num).toDouble(),
      totalFees: (json['total_fees'] as num).toDouble(),
      currentBalance: (json['current_balance'] as num).toDouble(),
      depositCount: json['deposit_count'],
      withdrawalCount: json['withdrawal_count'],
      currency: json['currency'],
      lastDepositAt: json['last_deposit_at'] != null
          ? DateTime.parse(json['last_deposit_at'])
          : null,
      lastWithdrawalAt: json['last_withdrawal_at'] != null
          ? DateTime.parse(json['last_withdrawal_at'])
          : null,
    );
  }

  double get netFlow => totalDeposits - totalWithdrawals;
}
