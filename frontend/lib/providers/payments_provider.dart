// lib/providers/payments_provider.dart
import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/constants.dart';
import '../models/transaction.dart';

/// Payments provider handling deposits, withdrawals, and transactions
/// Matches backend /api/v1/payments endpoints
class PaymentsProvider extends ChangeNotifier {
  final ApiClient api;

  bool _loading = false;
  String? _error;
  List<Transaction> _transactions = [];
  Map<String, dynamic>? _lastDepositResult;
  Map<String, dynamic>? _lastWithdrawalResult;

  PaymentsProvider({required this.api});

  // ============================================================================
  // GETTERS
  // ============================================================================

  bool get loading => _loading;
  String? get error => _error;
  List<Transaction> get transactions => _transactions;
  Map<String, dynamic>? get lastDepositResult => _lastDepositResult;
  Map<String, dynamic>? get lastWithdrawalResult => _lastWithdrawalResult;

  // ============================================================================
  // DEPOSIT METHODS
  // ============================================================================

  /// Create deposit with fee calculation
  /// Returns: {gross_amount, fee_percent, fee_amount, net_trading_balance, transaction_id, payment_token}
  Future<Map<String, dynamic>?> createDeposit({
    required String userId,
    required double amount,
    String currency = 'GHS',
    String method = 'momo',
    Map<String, dynamic>? extra,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      // Validate currency
      if (!kSupportedCurrencies.contains(currency)) {
        throw Exception(
          'Unsupported currency: $currency. Supported: ${kSupportedCurrencies.join(", ")}',
        );
      }

      // Validate method
      if (!PaymentMethods.all.contains(method)) {
        throw Exception('Unsupported payment method: $method');
      }

      // Validate minimum deposit for GHS
      if (currency == 'GHS' && amount < kMinDepositGHS) {
        throw Exception(ErrorMessages.minDepositNotMet);
      }

      // Calculate fees (2% deposit fee)
      final feeAmount = amount * (kDepositFeePercent / 100);
      final netTradingBalance = amount - feeAmount;

      // Prepare request body
      final body = {
        'user_id': userId,
        'amount': amount,
        'currency': currency,
        'method': method,
        'net_trading_balance': netTradingBalance,
        if (extra != null) ...extra,
      };

      // Call backend
      final res = await api.post('/api/v1/payments/deposit', body);

      // Store result
      _lastDepositResult = res;

      // Refresh transactions
      await loadTransactions(userId);

      _setLoading(false);
      return res;
    } catch (e) {
      _setError('Deposit failed: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  /// Deposit via Mobile Money (Ghana)
  Future<Map<String, dynamic>?> depositViaMomo({
    required String userId,
    required double amount,
    required String provider, // MTN, Vodafone, AirtelTigo
    required String phoneNumber,
    String currency = 'GHS',
  }) async {
    // Validate MoMo provider
    if (!MoMoProviders.all.contains(provider)) {
      _setError('Invalid MoMo provider: $provider');
      return null;
    }

    return await createDeposit(
      userId: userId,
      amount: amount,
      currency: currency,
      method: PaymentMethods.momo,
      extra: {'provider': provider, 'phone_number': phoneNumber},
    );
  }

  /// Deposit via Card (Visa/Mastercard)
  Future<Map<String, dynamic>?> depositViaCard({
    required String userId,
    required double amount,
    String currency = 'GHS',
  }) async {
    return await createDeposit(
      userId: userId,
      amount: amount,
      currency: currency,
      method: PaymentMethods.card,
    );
  }

  /// Deposit via PayPal
  Future<Map<String, dynamic>?> depositViaPayPal({
    required String userId,
    required double amount,
    required String email,
    String currency = 'USD',
  }) async {
    return await createDeposit(
      userId: userId,
      amount: amount,
      currency: currency,
      method: PaymentMethods.paypal,
      extra: {'paypal_email': email},
    );
  }

  /// Deposit via Cryptocurrency
  Future<Map<String, dynamic>?> depositViaCrypto({
    required String userId,
    required double amount,
    required String cryptoAsset, // USDT, USDC, BTC, ETH
    String currency = 'USD',
  }) async {
    // Validate crypto asset
    if (!CryptoAssets.all.contains(cryptoAsset)) {
      _setError('Unsupported crypto asset: $cryptoAsset');
      return null;
    }

    return await createDeposit(
      userId: userId,
      amount: amount,
      currency: currency,
      method: PaymentMethods.crypto,
      extra: {'crypto_asset': cryptoAsset},
    );
  }

  // ============================================================================
  // WITHDRAWAL METHODS
  // ============================================================================

  /// Request withdrawal with fee calculation
  /// Returns: {gross_amount, fee_percent, fee_amount, net_payout, transaction_id}
  Future<Map<String, dynamic>?> requestWithdraw({
    required String userId,
    required double amount,
    required String destination,
    String currency = 'GHS',
    String method = 'momo',
    Map<String, dynamic>? extra,
  }) async {
    _setLoading(true);
    _clearError();

    try {
      // Validate currency
      if (!kSupportedCurrencies.contains(currency)) {
        throw Exception('Unsupported currency: $currency');
      }

      // Validate method
      if (!PaymentMethods.all.contains(method)) {
        throw Exception('Unsupported withdrawal method: $method');
      }

      // Calculate fees (5% withdrawal fee)
      final feeAmount = amount * (kWithdrawalFeePercent / 100);
      final netPayout = amount - feeAmount;

      // Prepare request body
      final body = {
        'user_id': userId,
        'amount': amount,
        'currency': currency,
        'destination': destination,
        'method': method,
        'net_payout': netPayout,
        if (extra != null) ...extra,
      };

      // Call backend
      final res = await api.post('/api/v1/payments/withdraw', body);

      // Store result
      _lastWithdrawalResult = res;

      // Refresh transactions
      await loadTransactions(userId);

      _setLoading(false);
      return res;
    } catch (e) {
      _setError('Withdrawal failed: ${e.toString()}');
      _setLoading(false);
      return null;
    }
  }

  /// Withdraw to Mobile Money
  Future<Map<String, dynamic>?> withdrawToMomo({
    required String userId,
    required double amount,
    required String provider,
    required String phoneNumber,
    String currency = 'GHS',
  }) async {
    if (!MoMoProviders.all.contains(provider)) {
      _setError('Invalid MoMo provider: $provider');
      return null;
    }

    return await requestWithdraw(
      userId: userId,
      amount: amount,
      destination: phoneNumber,
      currency: currency,
      method: PaymentMethods.momo,
      extra: {'provider': provider},
    );
  }

  /// Withdraw to Bank Card
  Future<Map<String, dynamic>?> withdrawToCard({
    required String userId,
    required double amount,
    required String cardLast4,
    String currency = 'GHS',
  }) async {
    return await requestWithdraw(
      userId: userId,
      amount: amount,
      destination: cardLast4,
      currency: currency,
      method: PaymentMethods.card,
    );
  }

  /// Withdraw to PayPal
  Future<Map<String, dynamic>?> withdrawToPayPal({
    required String userId,
    required double amount,
    required String email,
    String currency = 'USD',
  }) async {
    return await requestWithdraw(
      userId: userId,
      amount: amount,
      destination: email,
      currency: currency,
      method: PaymentMethods.paypal,
    );
  }

  /// Withdraw to Crypto
  Future<Map<String, dynamic>?> withdrawToCrypto({
    required String userId,
    required double amount,
    required String cryptoAsset,
    required String walletAddress,
    String currency = 'USD',
  }) async {
    if (!CryptoAssets.all.contains(cryptoAsset)) {
      _setError('Unsupported crypto asset: $cryptoAsset');
      return null;
    }

    return await requestWithdraw(
      userId: userId,
      amount: amount,
      destination: walletAddress,
      currency: currency,
      method: PaymentMethods.crypto,
      extra: {'crypto_asset': cryptoAsset},
    );
  }

  // ============================================================================
  // TRANSACTION HISTORY
  // ============================================================================

  /// Load transaction history for user
  Future<void> loadTransactions(
    String userId, {
    int? limit,
    int? offset,
    String? type, // 'deposit', 'withdrawal', 'fee', 'trade'
    String? status, // 'pending', 'completed', 'failed'
  }) async {
    _setLoading(true);
    _clearError();

    try {
      final queryParams = <String, String>{
        'user_id': userId,
        if (limit != null) 'limit': limit.toString(),
        if (offset != null) 'offset': offset.toString(),
        if (type != null) 'type': type,
        if (status != null) 'status': status,
      };

      final res = await api.get(
        '/api/v1/transactions',
        queryParameters: queryParams,
        params: {},
        queryParams: {},
      );

      // Parse transactions
      final transactionsList = (res['transactions'] ??
          res['data'] ??
          res['items'] ??
          []) as List<dynamic>;

      _transactions = transactionsList
          .map((t) => Transaction.fromJson(t as Map<String, dynamic>))
          .toList();

      _setLoading(false);
    } catch (e) {
      _setError('Failed to load transactions: ${e.toString()}');
      _setLoading(false);
    }
  }

  /// Get pending transactions
  List<Transaction> get pendingTransactions {
    return _transactions.where((t) => t.status == 'pending').toList();
  }

  /// Get completed transactions
  List<Transaction> get completedTransactions {
    return _transactions.where((t) => t.status == 'completed').toList();
  }

  /// Get failed transactions
  List<Transaction> get failedTransactions {
    return _transactions.where((t) => t.status == 'failed').toList();
  }

  /// Get deposits only
  List<Transaction> get deposits {
    return _transactions.where((t) => t.type == 'deposit').toList();
  }

  /// Get withdrawals only
  List<Transaction> get withdrawals {
    return _transactions.where((t) => t.type == 'withdrawal').toList();
  }

  // ============================================================================
  // FEE CALCULATIONS (Client-side preview)
  // ============================================================================

  /// Calculate deposit fees (2%)
  Map<String, double> calculateDepositFees(double amount) {
    final feeAmount = amount * (kDepositFeePercent / 100);
    final netTradingBalance = amount - feeAmount;

    return {
      'gross_amount': amount,
      'fee_percent': kDepositFeePercent,
      'fee_amount': feeAmount,
      'net_trading_balance': netTradingBalance,
    };
  }

  /// Calculate withdrawal fees (5%)
  Map<String, double> calculateWithdrawalFees(double amount) {
    final feeAmount = amount * (kWithdrawalFeePercent / 100);
    final netPayout = amount - feeAmount;

    return {
      'gross_amount': amount,
      'fee_percent': kWithdrawalFeePercent,
      'fee_amount': feeAmount,
      'net_payout': netPayout,
    };
  }

  // ============================================================================
  // CURRENCY CONVERSION (Placeholder for future)
  // ============================================================================

  /// Get supported currencies list
  List<String> get supportedCurrencies => kSupportedCurrencies;

  /// Check if currency is supported
  bool isCurrencySupported(String currency) {
    return kSupportedCurrencies.contains(currency);
  }

  /// Get currency symbol
  String getCurrencySymbol(String currency) {
    return kCurrencySymbols[currency] ?? currency;
  }

  /// Get currency display name
  String getCurrencyName(String currency) {
    return kCurrencyNames[currency] ?? currency;
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

  /// Clear cached results
  void clearCache() {
    _lastDepositResult = null;
    _lastWithdrawalResult = null;
    _transactions = [];
    notifyListeners();
  }

  // ============================================================================
  // VALIDATION HELPERS
  // ============================================================================

  /// Validate deposit amount
  String? validateDepositAmount(double amount, String currency) {
    if (amount <= 0) {
      return ErrorMessages.invalidAmount;
    }
    if (currency == 'GHS' && amount < kMinDepositGHS) {
      return ErrorMessages.minDepositNotMet;
    }
    return null;
  }

  /// Validate withdrawal amount
  String? validateWithdrawalAmount(double amount, double availableBalance) {
    if (amount <= 0) {
      return ErrorMessages.invalidAmount;
    }
    if (amount > availableBalance) {
      return ErrorMessages.insufficientBalance;
    }
    return null;
  }
}
