import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/api_client.dart';
import '../../routes/app_routes.dart';

class PaymentsScreen extends StatefulWidget {
  const PaymentsScreen({super.key});

  @override
  State<PaymentsScreen> createState() => _PaymentsScreenState();
}

class _PaymentsScreenState extends State<PaymentsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _selectedCurrency = 'GHS';
  String _selectedMethod = '';
  final TextEditingController _amountController = TextEditingController();
  bool _loading = false; // FIXED: Added missing state variable

  final List<String> _currencies = [
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

  final List<Map<String, dynamic>> _paymentMethods = [
    {
      'id': 'momo',
      'name': 'Mobile Money',
      'icon': Icons.smartphone,
      'providers': ['MTN', 'Vodafone', 'AirtelTigo'],
      'gradient': [Color(0xFFFBBF24), Color(0xFFF59E0B)],
    },
    {
      'id': 'card',
      'name': 'Bank Card',
      'icon': Icons.credit_card,
      'providers': ['Visa', 'Mastercard'],
      'gradient': [Color(0xFF3B82F6), Color(0xFF06B6D4)],
    },
    {
      'id': 'paypal',
      'name': 'PayPal',
      'icon': Icons.paypal,
      'providers': ['PayPal'],
      'gradient': [Color(0xFF6366F1), Color(0xFF3B82F6)],
    },
    {
      'id': 'crypto',
      'name': 'Cryptocurrency',
      'icon': Icons.currency_bitcoin,
      'providers': ['USDT', 'USDC', 'BTC', 'ETH'],
      'gradient': [Color(0xFFA855F7), Color(0xFFEC4899)],
    },
  ];

  List<Map<String, dynamic>> _transactions = [];
  bool _loadingTransactions = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadTransactions();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _loadTransactions() async {
    setState(() => _loadingTransactions = true);

    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final response =
          await api.get('/payments/history', params: {}, queryParams: {});

      setState(() {
        _transactions =
            List<Map<String, dynamic>>.from(response['transactions'] ?? []);
      });
    } catch (e) {
      // Use empty list if API fails
      setState(() => _transactions = []);
    } finally {
      setState(() => _loadingTransactions = false);
    }
  }

  double _calculateFee(double amount, bool isDeposit) {
    return amount * (isDeposit ? 0.02 : 0.05);
  }

  double _calculateNet(double amount, bool isDeposit) {
    return amount - _calculateFee(amount, isDeposit);
  }

  bool _isMinimumMet(double amount) {
    if (_selectedCurrency == 'GHS') {
      return amount >= 500;
    }
    return amount >= 50;
  }

  Widget _buildBalanceCard(
    String title,
    double amount,
    Color gradientStart,
    Color gradientEnd,
    IconData icon,
  ) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            gradientStart.withOpacity(0.1),
            gradientEnd.withOpacity(0.1),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: gradientStart.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: gradientStart.withOpacity(0.1),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      padding: EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: gradientStart,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Icon(icon, color: gradientStart, size: 20),
            ],
          ),
          SizedBox(height: 12),
          Text(
            '$_selectedCurrency ${amount.toStringAsFixed(2)}',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.5,
            ),
          ),
          SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.trending_up, color: Colors.green, size: 16),
              SizedBox(width: 4),
              Text(
                '+12.5% this month',
                style: TextStyle(color: Colors.green, fontSize: 10),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPaymentMethodCard(Map<String, dynamic> method) {
    final bool isSelected = _selectedMethod == method['id'];
    final themeColor = const Color(0xFF06B6D4); // Consistent theme color
    
    return GestureDetector(
      onTap: () => setState(() => _selectedMethod = method['id']),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: isSelected
              ? themeColor.withOpacity(0.15)
              : Colors.grey.shade900.withOpacity(0.5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected 
                ? themeColor.withOpacity(0.6) 
                : Colors.grey.shade700.withOpacity(0.3),
            width: isSelected ? 1.5 : 1,
          ),
        ),
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isSelected 
                    ? themeColor.withOpacity(0.2)
                    : Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: isSelected
                      ? themeColor.withOpacity(0.4)
                      : Colors.transparent,
                  width: 1,
                ),
              ),
              child: Icon(
                method['icon'], 
                color: isSelected ? themeColor : Colors.white70, 
                size: 22,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              method['name'],
              style: TextStyle(
                color: isSelected ? Colors.white : Colors.white70,
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              alignment: WrapAlignment.center,
              children: (method['providers'] as List<String>).take(2).map((
                provider,
              ) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    provider,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6), 
                      fontSize: 9,
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDepositWithdrawTab() {
    final bool isDeposit = _tabController.index == 0;
    final double amount = double.tryParse(_amountController.text) ?? 0;
    final double fee = _calculateFee(amount, isDeposit);
    final double net = _calculateNet(amount, isDeposit);

    return SingleChildScrollView(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Currency Selector
            Text(
              'Select Currency',
              style: TextStyle(
                color: Color(0xFF06B6D4),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: Colors.grey.shade900.withOpacity(0.5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.3)),
              ),
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: _selectedCurrency,
                  isExpanded: true,
                  dropdownColor: Colors.grey.shade900,
                  style: TextStyle(color: Colors.white, fontSize: 16),
                  icon: Icon(
                    Icons.keyboard_arrow_down,
                    color: Color(0xFF06B6D4),
                  ),
                  items: _currencies.map((currency) {
                    return DropdownMenuItem(
                      value: currency,
                      child: Text(
                        currency,
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                    );
                  }).toList(),
                  onChanged: (value) =>
                      setState(() => _selectedCurrency = value!),
                ),
              ),
            ),
            SizedBox(height: 24),

            // Amount Input
            Text(
              'Amount',
              style: TextStyle(
                color: Color(0xFF06B6D4),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 12),
            TextField(
              controller: _amountController,
              keyboardType: TextInputType.numberWithOptions(decimal: true),
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
              decoration: InputDecoration(
                prefixIcon: Icon(Icons.attach_money, color: Color(0xFF06B6D4)),
                hintText: 'Enter amount',
                hintStyle: TextStyle(color: Colors.grey.shade600),
                filled: true,
                fillColor: Colors.grey.shade900.withOpacity(0.5),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: Color(0xFF06B6D4).withOpacity(0.3),
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: Color(0xFF06B6D4).withOpacity(0.3),
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Color(0xFF06B6D4), width: 2),
                ),
              ),
              onChanged: (value) => setState(() {}),
            ),
            if (amount > 0 && !_isMinimumMet(amount))
              Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  _selectedCurrency == 'GHS'
                      ?                       'Minimum deposit: GHS 500'
                      : 'Minimum deposit: 50 $_selectedCurrency',
                  style: TextStyle(color: Colors.orange, fontSize: 11),
                ),
              ),
            SizedBox(height: 24),

            // Payment Methods
            Text(
              'Payment Method',
              style: TextStyle(
                color: Color(0xFF06B6D4),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 12),
            GridView.builder(
              shrinkWrap: true,
              physics: NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.1,
              ),
              itemCount: _paymentMethods.length,
              itemBuilder: (context, index) {
                return _buildPaymentMethodCard(_paymentMethods[index]);
              },
            ),
            SizedBox(height: 24),

            // Fee Breakdown
            if (amount > 0) ...[
              Container(
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade900.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.2)),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Amount',
                          style: TextStyle(color: Colors.grey.shade400),
                        ),
                        Text(
                          '$_selectedCurrency ${amount.toStringAsFixed(2)}',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Fee (${isDeposit ? '2' : '5'}%)',
                          style: TextStyle(color: Colors.grey.shade400),
                        ),
                        Text(
                          '$_selectedCurrency ${fee.toStringAsFixed(2)}',
                          style: TextStyle(
                            color: Colors.orange,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    Divider(color: Colors.grey.shade700, height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'You ${isDeposit ? 'receive' : 'get'}',
                          style: TextStyle(
                            color: Color(0xFF06B6D4),
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                          ),
                        ),
                        Text(
                          '$_selectedCurrency ${net.toStringAsFixed(2)}',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              SizedBox(height: 24),
            ],

            // Submit Button
            Center(
              child: Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 0),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.3), width: 1),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0xFF06B6D4).withOpacity(0.3),
                      blurRadius: 12,
                      offset: Offset(0, 6),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: amount > 0 &&
                            _isMinimumMet(amount) &&
                            _selectedMethod.isNotEmpty &&
                            !_loading
                        ? () async {
                            setState(() => _loading = true);

                            try {
                              final api = Provider.of<ApiClient>(context, listen: false);

                              // Create transaction
                              final response = await api.post(
                                isDeposit
                                    ? '/payments/deposit'
                                    : '/payments/withdraw',
                                {
                                  'amount': amount,
                                  'currency': _selectedCurrency,
                                  'method': _selectedMethod,
                                },
                              );

                              // Navigate to payment detail with response data
                              if (mounted) {
                                Navigator.pushNamed(
                                  context,
                                  AppRoutes.paymentDetail,
                                  arguments: response,
                                );
                              }
                            } catch (e) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text('Error: $e'),
                                    backgroundColor: Colors.red,
                                  ),
                                );
                              }
                            } finally {
                              if (mounted) {
                                setState(() => _loading = false);
                              }
                            }
                          }
                        : null,
                    borderRadius: BorderRadius.circular(16),
                    child: Center(
                      child: _loading
                          ? SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                color: Colors.white,
                                strokeWidth: 2,
                              ),
                            )
                          : Text(
                              isDeposit ? 'Deposit Now' : 'Withdraw Now',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 0.2,
                              ),
                            ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTransactionsTab() {
    if (_loadingTransactions) {
      return Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation(Color(0xFF06B6D4)),
        ),
      );
    }

    if (_transactions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.receipt_long,
              size: 64,
              color: Colors.grey.shade600,
            ),
            SizedBox(height: 16),
            Text(
              'No transactions yet',
              style: TextStyle(
                color: Colors.grey.shade400,
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: EdgeInsets.all(20),
      itemCount: _transactions.length,
      itemBuilder: (context, index) {
        final transaction = _transactions[index];
        final bool isDeposit = transaction['type'] == 'deposit';
        final String status = transaction['status'] ?? 'pending';

        Color statusColor;
        IconData statusIcon;
        switch (status) {
          case 'completed':
            statusColor = Colors.green;
            statusIcon = Icons.check_circle;
            break;
          case 'pending':
            statusColor = Colors.orange;
            statusIcon = Icons.access_time;
            break;
          case 'failed':
            statusColor = Colors.red;
            statusIcon = Icons.cancel;
            break;
          default:
            statusColor = Colors.grey;
            statusIcon = Icons.help;
        }

        return Container(
          margin: EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.grey.shade900.withOpacity(0.5),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.grey.shade800),
          ),
          child: ListTile(
            contentPadding: EdgeInsets.all(16),
            leading: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isDeposit
                      ? [
                          Colors.green.withOpacity(0.2),
                          Colors.green.withOpacity(0.1),
                        ]
                      : [
                          Colors.orange.withOpacity(0.2),
                          Colors.orange.withOpacity(0.1),
                        ],
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                isDeposit ? Icons.arrow_downward : Icons.arrow_upward,
                color: isDeposit ? Colors.green : Colors.orange,
              ),
            ),
            title: Row(
              children: [
                Text(
                  '${transaction['currency'] ?? 'GHS'} ${(transaction['amount'] ?? 0).toStringAsFixed(2)}',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                SizedBox(width: 8),
                Icon(statusIcon, color: statusColor, size: 18),
              ],
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(height: 4),
                Text(
                  transaction['method'] ?? 'Unknown',
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                ),
                Text(
                  transaction['created_at'] ?? transaction['date'] ?? '',
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 11),
                ),
              ],
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  status.toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'Fee: ${(transaction['fee'] ?? 0).toStringAsFixed(2)}',
                  style: TextStyle(color: Colors.grey.shade500, fontSize: 10),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          color: Colors.black,
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Padding(
                padding: EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
                            ),
                            borderRadius: BorderRadius.circular(12),
                            boxShadow: [
                              BoxShadow(
                                color: Color(0xFF06B6D4).withOpacity(0.3),
                                blurRadius: 12,
                              ),
                            ],
                          ),
                          child: Icon(
                            Icons.account_balance_wallet,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Wallet',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Text(
                              'Manage your funds securely',
                              style: TextStyle(
                                color: Color(0xFF06B6D4),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    SizedBox(height: 20),
                    // Balance Cards
                    Row(
                      children: [
                        Expanded(
                          child: _buildBalanceCard(
                            'Total Balance',
                            12450.75,
                            Color(0xFF06B6D4),
                            Color(0xFF3B82F6),
                            Icons.account_balance,
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: _buildBalanceCard(
                            'Available',
                            11980.50,
                            Color(0xFFA855F7),
                            Color(0xFFEC4899),
                            Icons.trending_up,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Tab Bar
              Container(
                margin: EdgeInsets.symmetric(horizontal: 20),
                decoration: BoxDecoration(
                  color: Colors.grey.shade900.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.2)),
                ),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
                    ),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: Color(0xFF06B6D4).withOpacity(0.5),
                        blurRadius: 20,
                      ),
                    ],
                  ),
                  labelColor: Colors.white,
                  unselectedLabelColor: Colors.grey.shade500,
                  labelStyle: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                  onTap: (index) => setState(() {}),
                  tabs: [
                    Tab(text: 'Deposit'),
                    Tab(text: 'Withdraw'),
                    Tab(text: 'Transactions'),
                  ],
                ),
              ),

              // Tab Content
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildDepositWithdrawTab(),
                    _buildDepositWithdrawTab(),
                    _buildTransactionsTab(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
