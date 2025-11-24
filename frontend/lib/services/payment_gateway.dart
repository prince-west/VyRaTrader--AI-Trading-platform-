import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../core/config.dart';
import '../models/payment_models.dart';

/// Payment Gateway Service
/// Handles all payment operations: deposits, withdrawals, and webhook validations
/// Supports: MoMo (Hubtel), Cards (Stripe), PayPal, Crypto (Binance Pay)
class PaymentGatewayService {
  final http.Client _client;
  final FlutterSecureStorage _storage;
  final String _baseUrl;

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

  // Fee configuration (matches backend)
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

  PaymentGatewayService({
    http.Client? client,
    FlutterSecureStorage? storage,
    String? baseUrl,
  })  : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage(),
        _baseUrl = baseUrl ?? Config.apiBaseUrl;

  /// Get authentication headers
  Future<Map<String, String>> _getHeaders() async {
    final token = await _storage.read(key: 'access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ${token ?? ''}',
    };
  }

  /// Validate currency support
  bool isCurrencySupported(String currency) {
    return supportedCurrencies.contains(currency.toUpperCase());
  }

  /// Get minimum deposit for currency
  double getMinimumDeposit(String currency) {
    return minimumDeposits[currency.toUpperCase()] ?? 500.0;
  }

  /// Calculate deposit fees
  DepositFeeCalculation calculateDepositFees({
    required double amount,
    required String currency,
  }) {
    if (!isCurrencySupported(currency)) {
      throw PaymentException('Currency $currency is not supported');
    }

    final minDeposit = getMinimumDeposit(currency);
    if (amount < minDeposit) {
      throw PaymentException(
        'Minimum deposit for $currency is ${minDeposit.toStringAsFixed(2)}',
      );
    }

    final feeAmount = amount * (depositFeePercent / 100);
    final netTradingBalance = amount - feeAmount;

    return DepositFeeCalculation(
      grossAmount: amount,
      feePercent: depositFeePercent,
      feeAmount: feeAmount,
      netTradingBalance: netTradingBalance,
      currency: currency,
    );
  }

  /// Calculate withdrawal fees
  WithdrawalFeeCalculation calculateWithdrawalFees({
    required double amount,
    required String currency,
  }) {
    if (!isCurrencySupported(currency)) {
      throw PaymentException('Currency $currency is not supported');
    }

    final feeAmount = amount * (withdrawalFeePercent / 100);
    final netPayout = amount - feeAmount;

    return WithdrawalFeeCalculation(
      requestedAmount: amount,
      feePercent: withdrawalFeePercent,
      feeAmount: feeAmount,
      netPayout: netPayout,
      currency: currency,
    );
  }

  /// Initiate deposit
  Future<DepositResponse> initiateDeposit({
    required String userId,
    required double amount,
    required String currency,
    required PaymentMethod method,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      // Validate currency and amount
      if (!isCurrencySupported(currency)) {
        throw PaymentException('Currency $currency is not supported');
      }

      final minDeposit = getMinimumDeposit(currency);
      if (amount < minDeposit) {
        throw PaymentException(
          'Minimum deposit for $currency is ${minDeposit.toStringAsFixed(2)}',
        );
      }

      // Calculate fees
      final feeCalc = calculateDepositFees(amount: amount, currency: currency);

      // Prepare request body
      final requestBody = {
        'user_id': userId,
        'amount': amount,
        'currency': currency,
        'method': method.toJson(),
        'fee_amount': feeCalc.feeAmount,
        'metadata': metadata ?? {},
      };

      // Make API request
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/deposit'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return DepositResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(error['detail'] ?? 'Failed to initiate deposit');
      }
    } on PaymentException {
      rethrow;
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Initiate withdrawal
  Future<WithdrawalResponse> initiateWithdrawal({
    required String userId,
    required double amount,
    required String currency,
    required PaymentMethod method,
    required WithdrawalDestination destination,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      // Validate currency
      if (!isCurrencySupported(currency)) {
        throw PaymentException('Currency $currency is not supported');
      }

      // Calculate fees
      final feeCalc = calculateWithdrawalFees(
        amount: amount,
        currency: currency,
      );

      // Prepare request body
      final requestBody = {
        'user_id': userId,
        'amount': amount,
        'currency': currency,
        'method': method.toJson(),
        'destination': destination.toJson(),
        'fee_amount': feeCalc.feeAmount,
        'metadata': metadata ?? {},
      };

      // Make API request
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/withdraw'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return WithdrawalResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to initiate withdrawal',
        );
      }
    } on PaymentException {
      rethrow;
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Get transaction history
  Future<List<Transaction>> getTransactionHistory({
    required String userId,
    TransactionType? type,
    TransactionStatus? status,
    int? limit,
    int? offset,
  }) async {
    try {
      final queryParams = <String, String>{
        'user_id': userId,
        if (type != null) 'type': type.toString().split('.').last,
        if (status != null) 'status': status.toString().split('.').last,
        if (limit != null) 'limit': limit.toString(),
        if (offset != null) 'offset': offset.toString(),
      };

      final uri = Uri.parse(
        '$_baseUrl/api/v1/payments/transactions',
      ).replace(queryParameters: queryParams);

      final response = await _client.get(uri, headers: await _getHeaders());

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        return data.map((json) => Transaction.fromJson(json)).toList();
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to fetch transaction history',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Get transaction by ID
  Future<Transaction> getTransaction(String transactionId) async {
    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/payments/transactions/$transactionId'),
        headers: await _getHeaders(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return Transaction.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to fetch transaction',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Process MoMo payment (Hubtel)
  Future<MoMoPaymentResponse> processMoMoPayment({
    required String transactionId,
    required String phoneNumber,
    required String network,
    required double amount,
  }) async {
    try {
      final requestBody = {
        'transaction_id': transactionId,
        'phone_number': phoneNumber,
        'network': network,
        'amount': amount,
      };

      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/momo/process'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return MoMoPaymentResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to process MoMo payment',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Process card payment (Stripe)
  Future<CardPaymentResponse> processCardPayment({
    required String transactionId,
    required String paymentMethodId,
  }) async {
    try {
      final requestBody = {
        'transaction_id': transactionId,
        'payment_method_id': paymentMethodId,
      };

      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/card/process'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return CardPaymentResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to process card payment',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Process PayPal payment
  Future<PayPalPaymentResponse> processPayPalPayment({
    required String transactionId,
  }) async {
    try {
      final requestBody = {'transaction_id': transactionId};

      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/paypal/process'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return PayPalPaymentResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to process PayPal payment',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Process crypto payment (Binance Pay)
  Future<CryptoPaymentResponse> processCryptoPayment({
    required String transactionId,
    required String cryptoCurrency,
    required String network,
  }) async {
    try {
      final requestBody = {
        'transaction_id': transactionId,
        'crypto_currency': cryptoCurrency,
        'network': network,
      };

      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/crypto/process'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return CryptoPaymentResponse.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to process crypto payment',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Verify payment status
  Future<PaymentVerification> verifyPayment({
    required String transactionId,
  }) async {
    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/payments/verify/$transactionId'),
        headers: await _getHeaders(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return PaymentVerification.fromJson(data);
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(error['detail'] ?? 'Failed to verify payment');
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Get supported payment methods for currency
  List<PaymentMethodType> getSupportedMethods(String currency) {
    final currencyUpper = currency.toUpperCase();

    // All currencies support these methods
    final methods = <PaymentMethodType>[
      PaymentMethodType.card,
      PaymentMethodType.paypal,
      PaymentMethodType.crypto,
    ];

    // MoMo only for African currencies
    if (['GHS', 'NGN', 'ZAR'].contains(currencyUpper)) {
      methods.insert(0, PaymentMethodType.momo);
    }

    return methods;
  }

  /// Get MoMo networks for country
  List<MoMoNetwork> getMoMoNetworks(String currency) {
    switch (currency.toUpperCase()) {
      case 'GHS':
        return [MoMoNetwork.mtn, MoMoNetwork.vodafone, MoMoNetwork.airteltigo];
      case 'NGN':
        return [MoMoNetwork.mtn, MoMoNetwork.airtel];
      case 'ZAR':
        return [MoMoNetwork.vodacom, MoMoNetwork.mtn];
      default:
        return [];
    }
  }

  /// Get crypto currencies supported
  List<CryptoCurrency> getSupportedCrypto() {
    return [
      CryptoCurrency.usdt,
      CryptoCurrency.usdc,
      CryptoCurrency.btc,
      CryptoCurrency.eth,
    ];
  }

  /// Get crypto networks for currency
  List<String> getCryptoNetworks(CryptoCurrency crypto) {
    switch (crypto) {
      case CryptoCurrency.usdt:
      case CryptoCurrency.usdc:
        return ['TRC20', 'ERC20', 'BEP20'];
      case CryptoCurrency.btc:
        return ['Bitcoin'];
      case CryptoCurrency.eth:
        return ['Ethereum'];
    }
  }

  /// Cancel pending transaction
  Future<bool> cancelTransaction(String transactionId) async {
    try {
      final response = await _client.post(
        Uri.parse(
          '$_baseUrl/api/v1/payments/transactions/$transactionId/cancel',
        ),
        headers: await _getHeaders(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['success'] ?? false;
      } else {
        final error = jsonDecode(response.body);
        throw PaymentException(
          error['detail'] ?? 'Failed to cancel transaction',
        );
      }
    } catch (e) {
      throw PaymentException('Network error: ${e.toString()}');
    }
  }

  /// Dispose resources
  void dispose() {
    _client.close();
  }
}

/// Custom exception for payment errors
class PaymentException implements Exception {
  final String message;
  final String? code;
  final dynamic details;

  PaymentException(this.message, {this.code, this.details});

  @override
  String toString() => 'PaymentException: $message';
}
