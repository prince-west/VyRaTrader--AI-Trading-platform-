// lib/screens/profile/profile_screen.dart
// PRODUCTION READY - Fetches real user data from API

import 'package:flutter/material.dart';
import 'package:crypto/crypto.dart';
import 'dart:convert';
import 'dart:async';
import '../../routes/app_routes.dart';
import '../../core/secure_storage.dart';
import '../../core/api_client.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isDarkMode = true;
  bool _notificationsEnabled = true;
  bool _tradeAlertsEnabled = true;
  bool _emailNotifications = false;
  bool _biometricEnabled = false;
  bool _twoFactorEnabled = false;
  String _selectedLanguage = 'English';
  String _selectedCurrency = 'GHS';

  // Real user data
  String _userName = '';
  String _userEmail = '';
  bool _isVerified = false;
  int _totalDeposits = 0;
  int _totalWithdrawals = 0;
  int _activeTrades = 0;
  bool _isLoading = true;
  
  // Premium status
  bool _isPremium = false;
  String? _premiumExpiresAt;

  final List<String> _languages = [
    'English',
    'French',
    'Spanish',
    'German',
    'Chinese',
  ];
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadUserData();
      _loadUserStats();
    });
  }
  
  String _getDisplayName() {
    // Priority: _userName -> email prefix -> auth provider -> empty string
    if (_userName.isNotEmpty && _userName != 'User' && _userName != 'Guest') {
      return _userName;
    }
    
    if (_userEmail.isNotEmpty) {
      return _userEmail.split('@').first.capitalizeFirst();
    }
    
    // Fallback to auth provider
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final user = authProvider.user;
      if (user != null) {
        if (user.fullName != null && user.fullName!.isNotEmpty) {
          return user.fullName!;
        }
        if (user.email.isNotEmpty) {
          return user.email.split('@').first.capitalizeFirst();
        }
      }
    } catch (e) {
      // Ignore
    }
    
    // Return empty string instead of 'User' - UI should handle empty gracefully
    return '';
  }
  
  String _getEmail() {
    if (_userEmail.isNotEmpty) return _userEmail;
    
    // Fallback to auth provider
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      return authProvider.user?.email ?? '';
    } catch (e) {
      return '';
    }
  }

  Future<void> _loadUserData() async {
    if (!mounted) return;
    
    try {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      // First, try to get from auth provider (fast)
      var user = authProvider.user;
      if (user == null) {
        // Load profile if not available
        try {
          await authProvider.loadProfile().timeout(const Duration(seconds: 5));
          user = authProvider.user;
        } catch (e) {
          debugPrint('Failed to load profile from auth provider: $e');
        }
      }
      
      if (mounted && user != null) {
        setState(() {
          // Only use real data from user object
          if (user!.fullName != null && user!.fullName!.isNotEmpty) {
            _userName = user!.fullName!;
          } else if (user!.email.isNotEmpty) {
            _userName = user!.email.split('@').first.capitalizeFirst();
          }
          _userEmail = user!.email;
          _isLoading = false; // Clear loading immediately with cached data
        });
      } else if (mounted) {
        // No user data available - still clear loading to show UI
        setState(() {
          _isLoading = false;
        });
      }
      
      // Always fetch fresh data from API to ensure we have the latest (non-blocking)
      if (mounted) {
        await _refreshUserDataFromAPI();
      }
    } catch (e) {
      debugPrint('Error in _loadUserData: $e');
      // CRITICAL: Always clear loading state even on error
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
  
  Future<void> _refreshUserDataFromAPI() async {
    if (!mounted) return;
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      // Backend router is mounted at /api/v1/users, route is /me, so full path is /api/v1/users/me
      // API client baseUrl already includes /api/v1, so we call /users/me
      final response = await api.get('/users/me', params: {}, queryParams: {}).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw TimeoutException('Profile data request timed out');
        },
      );
      
      if (!mounted) return;
      
      if (response is Map<String, dynamic>) {
        debugPrint('Profile API Response: $response');
        
        // Update auth provider with fresh data
        await authProvider.loadProfile();
        
        if (!mounted) return;
        
        // Get updated user from provider
        final updatedUser = authProvider.user;
        
        if (mounted) {
          setState(() {
            // Extract full_name from API response
            final fullName = response['full_name']?.toString().trim() ?? '';
            final email = response['email']?.toString().trim() ?? '';
            
            if (fullName.isNotEmpty) {
              _userName = fullName;
            } else if (updatedUser?.fullName != null && updatedUser!.fullName!.isNotEmpty) {
              _userName = updatedUser.fullName!;
            } else if (email.isNotEmpty) {
              _userName = email.split('@').first.capitalizeFirst();
            } else if (updatedUser != null && updatedUser.email.isNotEmpty) {
              _userName = updatedUser.email.split('@').first.capitalizeFirst();
            }
            
            if (email.isNotEmpty) {
              _userEmail = email;
            } else if (updatedUser != null && updatedUser.email.isNotEmpty) {
              _userEmail = updatedUser.email;
            }
            
            // Update premium fields
            if (response.containsKey('is_premium')) {
              _isPremium = response['is_premium'] == true;
            }
            if (response['premium_expires_at'] != null) {
              _premiumExpiresAt = response['premium_expires_at'].toString();
            }
            
            // Always clear loading state
            _isLoading = false;
          });
        }
        
        debugPrint('Final _userName after setState: $_userName');
      } else {
        // Invalid response format - clear loading state
        if (mounted) {
          setState(() {
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      // If API fails, keep using auth provider data (already set above)
      debugPrint('Failed to refresh user data: $e');
      // CRITICAL: Always clear loading state even on error
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadUserStats() async {
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      // Try multiple possible endpoints
      Map<String, dynamic> stats;
      try {
        stats = await api.get('/api/v1/user/stats', params: {}, queryParams: {});
      } catch (e) {
        try {
          stats = await api.get('/api/v1/users/me/stats', params: {}, queryParams: {});
        } catch (e2) {
          stats = await api.get('/user/stats', params: {}, queryParams: {});
        }
      }

      setState(() {
        _totalDeposits = stats['total_deposits']?.toInt() ?? stats['total_deposits'] ?? 0;
        _totalWithdrawals = stats['total_withdrawals']?.toInt() ?? stats['total_withdrawals'] ?? 0;
        _activeTrades = stats['active_trades']?.toInt() ?? stats['active_trades'] ?? 0;
      });
    } catch (e) {
      // Keep default values (0) if API fails - don't show mock data
    }
  }

  void _showBottomSheet(BuildContext context, Widget content, String title) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.85,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF000C1F), Color(0xFF001F3F)],
          ),
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(24),
            topRight: Radius.circular(24),
          ),
        ),
        child: Column(
          children: [
            Container(
              margin: EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade600,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: Icon(Icons.close, color: Colors.white),
                  ),
                ],
              ),
            ),
            Divider(color: Color(0xFF06B6D4).withOpacity(0.2), height: 1),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(20),
                child: content,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Expanded(
      child: Container(
        padding: EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [color.withOpacity(0.1), color.withOpacity(0.05)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 22),
            SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Padding(
      padding: EdgeInsets.only(top: 24, bottom: 12),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: Colors.white, size: 20),
          ),
          SizedBox(width: 12),
          Text(
            title,
            style: TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  String _formatPremiumDate(String dateString) {
    try {
      final date = DateTime.parse(dateString);
      return '${date.day}/${date.month}/${date.year}';
    } catch (e) {
      return dateString;
    }
  }

  Future<void> _showPremiumUpgradeSheet(BuildContext context) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.85,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF000C1F), Color(0xFF001F3F)],
          ),
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(24),
            topRight: Radius.circular(24),
          ),
        ),
        child: Column(
          children: [
            Container(
              margin: EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade600,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Upgrade to Premium',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: Icon(Icons.close, color: Colors.white),
                  ),
                ],
              ),
            ),
            Divider(color: Color(0xFF06B6D4).withOpacity(0.2)),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            Colors.amber.withOpacity(0.2),
                            Colors.orange.withOpacity(0.1),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Colors.amber.withOpacity(0.5),
                          width: 2,
                        ),
                      ),
                      child: Column(
                        children: [
                          Icon(Icons.star, color: Colors.amber, size: 48),
                          SizedBox(height: 12),
                          Text(
                            'Premium Benefits',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 20),
                          _buildPremiumBenefit('Unlimited daily signals', Icons.all_inclusive),
                          _buildPremiumBenefit('No ads - Ad-free experience', Icons.block),
                          _buildPremiumBenefit('31 days access', Icons.calendar_today),
                          _buildPremiumBenefit('Priority AI signal generation', Icons.flash_on),
                        ],
                      ),
                    ),
                    SizedBox(height: 24),
                    Text(
                      'Select Payment Method',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 12),
                    _buildPaymentOption(context, 'Paystack', Icons.payment, 'GHS', '50.00'),
                    _buildPaymentOption(context, 'Stripe', Icons.credit_card, 'USD', '10.00'),
                    _buildPaymentOption(context, 'Hubtel', Icons.mobile_friendly, 'GHS', '50.00'),
                    _buildPaymentOption(context, 'PayPal', Icons.paypal, 'USD', '10.00'),
                    _buildPaymentOption(context, 'BinancePay', Icons.account_balance_wallet, 'USD', '10.00'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPremiumBenefit(String text, IconData icon) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: Colors.amber, size: 20),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: Colors.white,
                fontSize: 15,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPaymentOption(BuildContext context, String name, IconData icon, String currency, String amount) {
    return Container(
      margin: EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.grey.shade900.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.1)),
      ),
      child: ListTile(
        leading: Icon(icon, color: Color(0xFF06B6D4)),
        title: Text(
          name,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        subtitle: Text(
          '$amount $currency',
          style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
        ),
        trailing: Icon(Icons.chevron_right, color: Colors.grey.shade600),
        onTap: () => _processPremiumUpgrade(context, name, currency, amount),
      ),
    );
  }

  Future<void> _processPremiumUpgrade(BuildContext context, String provider, String currency, String amount) async {
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      final userId = authProvider.user?.id;
      if (userId == null) {
        throw Exception('User not authenticated');
      }

      // First initialize payment
      final initResponse = await api.post('/payments/initialize', {
        'user_id': userId,
        'amount': double.parse(amount),
        'currency': currency,
        'method': provider.toLowerCase(),
      });

      final transactionId = initResponse['transaction_id'];
      
      Navigator.pop(context); // Close payment sheet
      
      // Show processing dialog
      if (!context.mounted) return;
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => Center(
          child: CircularProgressIndicator(color: Color(0xFF06B6D4)),
        ),
      );

      // Call upgrade endpoint
      final upgradeResponse = await api.post('/payments/upgrade_premium', {
        'user_id': userId,
        'payment_provider': provider.toLowerCase(),
        'amount': double.parse(amount),
        'currency': currency,
        'transaction_id': transactionId,
      });

      if (!context.mounted) return;
      Navigator.pop(context); // Close loading

      if (upgradeResponse['success'] == true) {
        setState(() {
          _isPremium = true;
          _premiumExpiresAt = upgradeResponse['expires_at'];
        });

        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('🌟 Premium activated successfully!'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 3),
            ),
          );
        }
      } else {
        throw Exception('Premium activation failed');
      }
    } catch (e) {
      if (context.mounted) {
        Navigator.pop(context); // Close loading if still open
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to upgrade: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Widget _buildSettingTile({
    required String title,
    String? subtitle,
    required IconData icon,
    Widget? trailing,
    VoidCallback? onTap,
  }) {
    return Container(
      margin: EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.grey.shade900.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.1)),
      ),
      child: ListTile(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Icon(icon, color: Color(0xFF06B6D4)),
        title: Text(
          title,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        subtitle: subtitle != null
            ? Text(
                subtitle,
                style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
              )
            : null,
        trailing:
            trailing ?? Icon(Icons.chevron_right, color: Colors.grey.shade600),
        onTap: onTap,
      ),
    );
  }

  Widget _buildToggleTile({
    required String title,
    String? subtitle,
    required IconData icon,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Container(
      margin: EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.grey.shade900.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.1)),
      ),
      child: SwitchListTile(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        secondary: Icon(icon, color: Color(0xFF06B6D4)),
        title: Text(
          title,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        subtitle: subtitle != null
            ? Text(
                subtitle,
                style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
              )
            : null,
        value: value,
        onChanged: onChanged,
        activeThumbColor: Color(0xFF06B6D4),
      ),
    );
  }

  Widget _buildTermsContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildLegalSection(
          '1. Acceptance of Terms',
          'By accessing or using VyRaTrader, you agree to be bound by these Terms and Conditions. If you do not agree to these terms, you may not use the Platform.',
        ),
        _buildLegalSection(
          '2. Definitions',
          '"Platform" refers to VyRaTrader, an AI-powered trading platform. "User" refers to anyone accessing the Platform. "Prince AI" refers to the artificial intelligence system that generates trading signals and recommendations.',
        ),
        _buildLegalSection(
          '3. Eligibility',
          'You must be at least 18 years of age and have the legal capacity to enter into binding agreements in your jurisdiction. You must not use the Platform if it is illegal or prohibited.',
        ),
        _buildLegalSection(
          '4. Account Registration and Security',
          'You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorized access. You are responsible for all activities that occur under your account.',
        ),
        _buildLegalSection(
          '5. AI Trading Disclaimer',
          'Prince AI is an artificial intelligence system that provides trading signals and recommendations. The AI\'s recommendations are based on algorithmic analysis and are NOT financial advice. Past performance does NOT guarantee future results. All trading decisions are made at your own risk.',
        ),
        _buildLegalSection(
          '6. Trading Risks and Liabilities',
          'Trading involves substantial risk of loss and is not suitable for all investors. You may lose all or a portion of your invested capital. Market volatility can cause sudden and significant losses. We are NOT responsible for your trading losses.',
        ),
        _buildLegalSection(
          '7. Deposits and Withdrawals',
          'Minimum deposit: GHS 500 or equivalent. Deposit fee: 2% of the deposit amount. Withdrawal fee: 5% of the withdrawal amount. Withdrawals may take 1-5 business days to process. We reserve the right to verify your identity before processing withdrawals.',
        ),
        _buildLegalSection(
          '8. Fees and Charges',
          'All fees are disclosed at the time of deposit or withdrawal. Fees may vary by payment method. Third-party payment processor fees are separate and may apply. We reserve the right to update fees with 30 days\' notice.',
        ),
        _buildLegalSection(
          '9. Stop-Loss and Risk Management',
          'The Platform provides risk management tools (stop-loss, take-profit). Low-risk: up to 3% stop-loss, 25% max exposure. Medium-risk: up to 7% stop-loss, 25% max exposure. High-risk: up to 15% stop-loss, 60% max exposure. You can adjust your risk profile in settings.',
        ),
        _buildLegalSection(
          '10. Intellectual Property',
          'All content on the Platform is owned by VyRaTrader or its licensors. The AI algorithms, strategies, and Prince AI are proprietary intellectual property. You may NOT copy, reproduce, or reverse-engineer any part of the Platform.',
        ),
        _buildLegalSection(
          '11. Privacy and Data',
          'Your use of the Platform is also governed by our Privacy Policy. We collect and use your data as described in the Privacy Policy. We use your trading data to improve AI models. You have the right to request deletion of your data.',
        ),
        _buildLegalSection(
          '12. User Conduct',
          'You agree to use the Platform only for lawful purposes. You may NOT use the Platform for money laundering or illegal activities. You may NOT attempt to manipulate markets or engage in fraudulent activities. You may NOT share your account with others.',
        ),
        _buildLegalSection(
          '13. API and Data Usage',
          'The Platform uses multiple third-party APIs for market data. API rate limits may affect data availability. If data is unavailable, Prince AI will inform you and suggest alternatives. We cache API responses to reduce consumption and costs.',
        ),
        _buildLegalSection(
          '14. Limitation of Liability',
          'TO THE MAXIMUM EXTENT PERMITTED BY LAW, VYRATRADER SHALL NOT BE LIABLE FOR: any losses resulting from trading decisions, AI prediction errors, data delays, technical failures, unauthorized access, or third-party service failures. Our total liability shall not exceed the amount you paid in fees in the last 12 months.',
        ),
        _buildLegalSection(
          '15. Indemnification',
          'You agree to indemnify and hold harmless VyRaTrader, its officers, employees, and agents. This includes all claims, losses, damages, liabilities, costs, and expenses related to any breach of these terms by you.',
        ),
        _buildLegalSection(
          '16. Termination',
          'We may suspend or terminate your account for violation of these terms, suspected fraudulent activity, or regulatory compliance requirements. You may close your account at any time. Upon termination, you are entitled to your remaining balance (minus fees).',
        ),
        _buildLegalSection(
          '17. Disputes and Governing Law',
          'These terms are governed by the laws of Ghana. Any disputes shall be resolved through arbitration in Accra, Ghana. Class action lawsuits are waived to the extent permitted by law.',
        ),
        _buildLegalSection(
          '18. Changes to Terms',
          'We may update these terms at any time. You will be notified of material changes via email or Platform notification. Continued use of the Platform after changes constitutes acceptance. We recommend reviewing terms periodically.',
        ),
        _buildLegalSection(
          '19. Third-Party Services',
          'The Platform integrates with payment processors (Hubtel, Paystack, Stripe), trading exchanges (Binance, OANDA), market data providers (CoinGecko, Alpha Vantage), and AI providers (OpenAI). Third-party terms apply to their respective services.',
        ),
        _buildLegalSection(
          '20. Reliable Signals and Wait Periods',
          'Prince AI provides signals based on available market data. If market data is unavailable due to API limits, Prince AI will inform you. You may need to wait until the next day for updated data. Prince AI may suggest alternative markets (forex) during unavailability.',
        ),
        _buildLegalSection(
          '21. Notifications',
          'Prince AI may send push notifications when reliable signals are detected. You can opt-out of notifications in settings. Notifications expire after a certain time (typically 1-4 hours). You are responsible for acting on signals promptly.',
        ),
        _buildLegalSection(
          '22. Risk Management and Stop Loss',
          'All trades are subject to risk management rules based on your risk profile. Prince AI recommends stop-loss levels, but you can override them. We strongly recommend using stop-loss orders to limit losses. Dynamic position sizing is applied based on market volatility.',
        ),
        _buildLegalSection(
          '23. Support and Help',
          'For support, contact us at support@vyratrader.com. We aim to respond within 24-48 hours. Prince AI can help answer questions within the Platform.',
        ),
        _buildLegalSection(
          '24. KYC and Compliance',
          'We are committed to Know Your Customer (KYC) compliance. We may request additional documentation to verify your identity. We comply with anti-money laundering (AML) regulations. We may freeze accounts pending investigation if suspicious activity is detected.',
        ),
        _buildLegalSection(
          '25. Force Majeure',
          'We are not liable for delays or failures due to circumstances beyond our control. This includes but is not limited to: natural disasters, war, pandemic, cyber attacks, etc.',
        ),
        _buildLegalSection(
          '26. Entire Agreement',
          'These terms constitute the entire agreement between you and VyRaTrader. Any previous oral or written agreements are superseded.',
        ),
        _buildLegalSection(
          '27. Severability',
          'If any provision is deemed invalid, the remainder of terms remains in effect.',
        ),
        _buildLegalSection(
          '28. No Waiver',
          'Our failure to enforce a term does not constitute a waiver of our rights.',
        ),
        _buildLegalSection(
          '29. Contact Information',
          'If you have questions about these terms, contact us at: Email: legal@vyratrader.com, Address: Accra, Ghana. By using VyRaTrader, you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions.',
        ),
      ],
    );
  }

  Widget _buildPrivacyContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildLegalSection(
          '1. Information We Collect',
          'We collect personal information (name, email, phone, address, date of birth), financial data (account balances, transactions, trading history, deposits, withdrawals), usage data (app interactions, AI chat logs, feature usage, screen views), device information (IP address, device type, operating system), and market data (trade preferences, signals generated for you, portfolio composition).',
        ),
        _buildLegalSection(
          '2. How We Use Your Data',
          'We use your data to: provide services (process trades, manage accounts, execute orders), improve AI (train Prince AI using aggregated, anonymized trading data), personalize experience (customize signals and recommendations), communicate (send updates, notifications, alerts, marketing with consent), ensure security (detect fraud, prevent abuse, verify identity), meet compliance (legal obligations, KYC requirements, AML checks), and analyze usage patterns to improve the Platform.',
        ),
        _buildLegalSection(
          '3. Data Sharing',
          'We share data with payment processors (Hubtel, Paystack) for transactions, trading exchanges (Binance, OANDA) for order execution, market data providers for real-time prices, cloud service providers for hosting, and analytics services (anonymized). We do NOT sell your personal data to third parties. We may share data if required by law or to protect our rights.',
        ),
        _buildLegalSection(
          '4. Data Security',
          'We use industry-standard encryption (SSL/TLS) for data in transit. Sensitive data is encrypted at rest. Access controls limit who can view your data. Payment information is tokenized and never stored directly. We conduct regular security audits.',
        ),
        _buildLegalSection(
          '5. Your Rights',
          'You have the right to: access (request a copy of your data), correction (update incorrect information), deletion (request deletion subject to legal requirements), portability (export your data in a machine-readable format), opt-out (unsubscribe from marketing communications), and objection (object to certain data processing).',
        ),
        _buildLegalSection(
          '6. Data Retention',
          'We retain data while your account is active. After account closure: 90 days for legal compliance, then deletion. Trading data may be kept longer for analytics (anonymized).',
        ),
        _buildLegalSection(
          '7. Cookies and Tracking',
          'We use cookies and similar technologies for authentication, preferences, analytics, and security. You can manage cookies in your browser settings.',
        ),
        _buildLegalSection(
          '8. AI and Machine Learning',
          'Your trading data (anonymized) helps train Prince AI to improve predictions for all users. Your individual identity is not revealed to other users. We may use third-party AI services (OpenAI, etc.) - their privacy policies apply.',
        ),
        _buildLegalSection(
          '9. International Users',
          'We comply with GDPR for EU users. Data is primarily stored in Ghana. Some data may be processed in other countries for service delivery.',
        ),
        _buildLegalSection(
          '10. Children\'s Privacy',
          'We do not knowingly collect data from children under 18. If you believe we have, contact us to have it removed.',
        ),
        _buildLegalSection(
          '11. Changes to This Policy',
          'We may update this policy periodically. You will be notified of material changes. Continued use constitutes acceptance.',
        ),
        _buildLegalSection(
          '12. Contact Us',
          'For privacy concerns, contact: privacy@vyratrader.com',
        ),
      ],
    );
  }

  Widget _buildAboutContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Center(
          child: Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Color(0xFF06B6D4).withOpacity(0.5),
                  blurRadius: 30,
                ),
              ],
            ),
            child: Icon(Icons.auto_graph, color: Colors.white, size: 60),
          ),
        ),
        SizedBox(height: 24),
        Center(
          child: Column(
            children: [
              Text(
                'VyRaTrader',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'Version 1.0.0',
                style: TextStyle(color: Colors.grey.shade400, fontSize: 14),
              ),
            ],
          ),
        ),
        SizedBox(height: 32),
        _buildLegalSection(
          'What is VyRaTrader?',
          'VyRaTrader is an AI-powered trading platform featuring Prince, your intelligent trading assistant. We focus on capital preservation and smart risk management.',
        ),
        _buildLegalSection(
          'AI Trading Engine',
          'Our platform uses multiple strategies: Trend Following, Mean Reversion, Momentum, Breakout, Volatility Breakout, Sentiment Filter and Arbitrage. Prince adapts dynamically to market conditions.',
        ),
        _buildLegalSection(
          'Risk Management',
          'Choose your risk level (Low, Medium, High) and let Prince manage position sizing, stop-loss, and take-profit automatically.',
        ),
        _buildLegalSection(
          'Multi-Market Support',
          'Trade across Crypto and Forex with seamless currency conversion in 13+ currencies.',
        ),
        _buildLegalSection(
          'Ghana-Focused Payments',
          'Integrated with Mobile Money (MTN, Vodafone, AirtelTigo), Bank Cards, PayPal, and Cryptocurrency payments.',
        ),
        SizedBox(height: 24),
        Container(
          padding: EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Color(0xFF06B6D4).withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Color(0xFF06B6D4).withOpacity(0.3)),
          ),
          child: Column(
            children: [
              Icon(Icons.support_agent, color: Color(0xFF06B6D4), size: 40),
              SizedBox(height: 12),
              Text(
                'Need Help?',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'Contact us at support@vyratrader.com',
                style: TextStyle(color: Colors.grey.shade400, fontSize: 14),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLegalSection(String title, String content) {
    return Padding(
      padding: EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: Color(0xFF06B6D4),
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 8),
          Text(
            content,
            style: TextStyle(
              color: Colors.grey.shade300,
              fontSize: 14,
              height: 1.6,
            ),
          ),
        ],
      ),
    );
  }

  void _showChangePasswordDialog() {
    final currentPasswordController = TextEditingController();
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF001F3F),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(Icons.lock, color: Color(0xFF06B6D4)),
            SizedBox(width: 12),
            Text('Change Password', style: TextStyle(color: Colors.white)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: currentPasswordController,
              obscureText: true,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'Current Password',
                labelStyle: TextStyle(color: Colors.grey.shade400),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(
                    color: Color(0xFF06B6D4).withOpacity(0.3),
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: Color(0xFF06B6D4)),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            SizedBox(height: 16),
            TextField(
              controller: newPasswordController,
              obscureText: true,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'New Password',
                labelStyle: TextStyle(color: Colors.grey.shade400),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(
                    color: Color(0xFF06B6D4).withOpacity(0.3),
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: Color(0xFF06B6D4)),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            SizedBox(height: 16),
            TextField(
              controller: confirmPasswordController,
              obscureText: true,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'Confirm New Password',
                labelStyle: TextStyle(color: Colors.grey.shade400),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(
                    color: Color(0xFF06B6D4).withOpacity(0.3),
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: Color(0xFF06B6D4)),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () async {
              final current = currentPasswordController.text;
              final newPass = newPasswordController.text;
              final confirm = confirmPasswordController.text;

              if (current.isEmpty || newPass.isEmpty || confirm.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('All fields are required')),
                );
                return;
              }

              if (newPass != confirm) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('New passwords do not match')),
                );
                return;
              }

              if (newPass.length < 8) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Password must be at least 8 characters'),
                  ),
                );
                return;
              }

              try {
                final api = Provider.of<ApiClient>(context, listen: false);
                await api.post('/auth/change-password', {
                  'current_password': current,
                  'new_password': newPass,
                });

                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Password changed successfully'),
                    backgroundColor: Colors.green,
                  ),
                );
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Failed to change password: $e'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Color(0xFF06B6D4),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              minimumSize: const Size(0, 40),
            ),
            child: Text('Change Password', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }

  void _showLogoutDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF001F3F),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(Icons.logout, color: Colors.red),
            SizedBox(width: 12),
            Text('Logout', style: TextStyle(color: Colors.white)),
          ],
        ),
        content: Text(
          'Are you sure you want to logout?',
          style: TextStyle(color: Colors.grey.shade300),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                final storage = SecureStorage();
                await storage.deleteAll();

                try {
                  final api = Provider.of<ApiClient>(context, listen: false);
                  await api.post('/auth/logout', {});
                } catch (e) {
                  // Continue even if backend logout fails
                }

                if (mounted) {
                  Navigator.pop(context);
                  Navigator.pushNamedAndRemoveUntil(
                    context,
                    AppRoutes.login,
                    (route) => false,
                  );
                }
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Logout error: $e'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              minimumSize: const Size(0, 40),
            ),
            child: Text('Logout', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
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
          child: _isLoading
              ? Center(
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation(Color(0xFF06B6D4)),
                  ),
                )
              : SingleChildScrollView(
                  padding: EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Profile Header
                      Container(
        padding: EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFF06B6D4).withOpacity(0.15),
              Color(0xFF3B82F6).withOpacity(0.08),
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Color(0xFF06B6D4).withOpacity(0.3),
            width: 1,
          ),
        ),
                        child: Row(
                          children: [
                            Container(
                              width: 64,
                              height: 64,
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    Color(0xFF06B6D4),
                                    Color(0xFF3B82F6)
                                  ],
                                ),
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color: Color(0xFF06B6D4).withOpacity(0.3),
                                    blurRadius: 12,
                                  ),
                                ],
                              ),
                              child: Icon(
                                Icons.person,
                                color: Colors.white,
                                size: 32,
                              ),
                            ),
                            SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _getDisplayName(),
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 18,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  if (_getEmail().isNotEmpty)
                                    Text(
                                      _getEmail(),
                                      style: TextStyle(
                                        color: Colors.grey.shade400,
                                        fontSize: 14,
                                      ),
                                    ),
                                  SizedBox(height: 8),
                                  if (_isVerified)
                                    Container(
                                      padding: EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.green.withOpacity(0.2),
                                        borderRadius: BorderRadius.circular(20),
                                        border: Border.all(color: Colors.green),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.verified,
                                            color: Colors.green,
                                            size: 14,
                                          ),
                                          SizedBox(width: 4),
                                          Text(
                                            'Verified',
                                            style: TextStyle(
                                              color: Colors.green,
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                ],
                              ),
                            ),
                            IconButton(
                              onPressed: () {
                                showModalBottomSheet(
                                  context: context,
                                  isScrollControlled: true,
                                  backgroundColor: Colors.transparent,
                                  builder: (context) => _EditProfileSheet(
                                    currentName: _userName,
                                    currentEmail: _userEmail,
                                    onSave: (name, email) async {
                                      try {
                                        final api = Provider.of<ApiClient>(context, listen: false);
                                        final authProvider = Provider.of<AuthProvider>(context, listen: false);
                                        
                                        final response = await api.put('/api/v1/users/me', {
                                          'full_name': name,
                                          'email': email,
                                        });

                                        // Update local state
                                        setState(() {
                                          _userName = name;
                                          _userEmail = email;
                                        });
                                        
                                        // Update auth provider by reloading profile to get latest data
                                        await authProvider.loadProfile();

                                        if (context.mounted) {
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(
                                            SnackBar(
                                              content: Text(
                                                  'Profile updated successfully'),
                                              backgroundColor: Colors.green,
                                            ),
                                          );
                                        }
                                      } catch (e) {
                                        if (context.mounted) {
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(
                                            SnackBar(
                                              content: Text(
                                                'Failed to update profile: $e',
                                              ),
                                              backgroundColor: Colors.red,
                                            ),
                                          );
                                        }
                                      }
                                    },
                                  ),
                                );
                              },
                              icon: Icon(Icons.edit, color: Color(0xFF06B6D4)),
                            ),
                          ],
                        ),
                      ),

                      SizedBox(height: 24),

                      // Stats
                      Row(
                        children: [
                          _buildStatCard(
                            'Deposits',
                            '$_totalDeposits',
                            Icons.arrow_downward,
                            Colors.green,
                          ),
                          SizedBox(width: 12),
                          _buildStatCard(
                            'Withdrawals',
                            '$_totalWithdrawals',
                            Icons.arrow_upward,
                            Colors.orange,
                          ),
                          SizedBox(width: 12),
                          _buildStatCard(
                            'Active Trades',
                            '$_activeTrades',
                            Icons.trending_up,
                            Color(0xFF06B6D4),
                          ),
                        ],
                      ),

                      SizedBox(height: 24),

                      // Premium Section
                      Container(
                        padding: EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: _isPremium
                                ? [
                                    Colors.amber.withOpacity(0.2),
                                    Colors.orange.withOpacity(0.1),
                                  ]
                                : [
                                    Color(0xFF06B6D4).withOpacity(0.15),
                                    Color(0xFF3B82F6).withOpacity(0.08),
                                  ],
                          ),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: _isPremium
                                ? Colors.amber.withOpacity(0.5)
                                : Color(0xFF06B6D4).withOpacity(0.3),
                            width: 2,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  _isPremium ? Icons.star : Icons.star_border,
                                  color: _isPremium ? Colors.amber : Color(0xFF06B6D4),
                                  size: 28,
                                ),
                                SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        _isPremium ? '🌟 Premium Active' : '💸 Upgrade to Premium',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      SizedBox(height: 4),
                                      if (_isPremium && _premiumExpiresAt != null)
                                        Text(
                                          'Active until ${_formatPremiumDate(_premiumExpiresAt!)}',
                                          style: TextStyle(
                                            color: Colors.grey.shade300,
                                            fontSize: 13,
                                          ),
                                        )
                                      else if (!_isPremium)
                                        Text(
                                          'Enjoy 31 days ad-free with unlimited signals',
                                          style: TextStyle(
                                            color: Colors.grey.shade300,
                                            fontSize: 13,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: 16),
                            if (_isPremium)
                              Container(
                                padding: EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: Colors.amber.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Row(
                                  children: [
                                    Icon(Icons.check_circle, color: Colors.amber, size: 20),
                                    SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        'Unlimited signals • No ads • Premium features',
                                        style: TextStyle(
                                          color: Colors.amber.shade200,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            else
                              Center(
                                child: ElevatedButton(
                                  onPressed: () => _showPremiumUpgradeSheet(context),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Color(0xFF06B6D4),
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                                    minimumSize: const Size(0, 44),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                  ),
                                  child: Text(
                                    'Go Premium',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),

                      // Settings Section
                      _buildSectionHeader('Settings', Icons.settings),
                      _buildToggleTile(
                        title: 'Dark Mode',
                        subtitle: 'Enable dark theme',
                        icon: Icons.dark_mode,
                        value: _isDarkMode,
                        onChanged: (val) => setState(() => _isDarkMode = val),
                      ),
                      _buildToggleTile(
                        title: 'Push Notifications',
                        subtitle: 'Receive app notifications',
                        icon: Icons.notifications,
                        value: _notificationsEnabled,
                        onChanged: (val) =>
                            setState(() => _notificationsEnabled = val),
                      ),
                      _buildToggleTile(
                        title: 'Trade Alerts',
                        subtitle: 'Get notified of trade executions',
                        icon: Icons.assessment,
                        value: _tradeAlertsEnabled,
                        onChanged: (val) =>
                            setState(() => _tradeAlertsEnabled = val),
                      ),
                      _buildToggleTile(
                        title: 'Email Notifications',
                        subtitle: 'Receive updates via email',
                        icon: Icons.email,
                        value: _emailNotifications,
                        onChanged: (val) =>
                            setState(() => _emailNotifications = val),
                      ),
                      _buildSettingTile(
                        title: 'Language',
                        subtitle: _selectedLanguage,
                        icon: Icons.language,
                        onTap: () {
                          showModalBottomSheet(
                            context: context,
                            backgroundColor: Color(0xFF001F3F),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.vertical(
                                top: Radius.circular(20),
                              ),
                            ),
                            builder: (context) => Column(
                              mainAxisSize: MainAxisSize.min,
                              children: _languages
                                  .map(
                                    (lang) => ListTile(
                                      title: Text(
                                        lang,
                                        style: TextStyle(color: Colors.white),
                                      ),
                                      trailing: _selectedLanguage == lang
                                          ? Icon(
                                              Icons.check,
                                              color: Color(0xFF06B6D4),
                                            )
                                          : null,
                                      onTap: () {
                                        setState(
                                            () => _selectedLanguage = lang);
                                        Navigator.pop(context);
                                      },
                                    ),
                                  )
                                  .toList(),
                            ),
                          );
                        },
                      ),
                      _buildSettingTile(
                        title: 'Default Currency',
                        subtitle: _selectedCurrency,
                        icon: Icons.attach_money,
                        onTap: () {
                          showModalBottomSheet(
                            context: context,
                            backgroundColor: Color(0xFF001F3F),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.vertical(
                                top: Radius.circular(20),
                              ),
                            ),
                            builder: (context) => SizedBox(
                              height: 400,
                              child: ListView(
                                children: _currencies
                                    .map(
                                      (currency) => ListTile(
                                        title: Text(
                                          currency,
                                          style: TextStyle(color: Colors.white),
                                        ),
                                        trailing: _selectedCurrency == currency
                                            ? Icon(
                                                Icons.check,
                                                color: Color(0xFF06B6D4),
                                              )
                                            : null,
                                        onTap: () {
                                          setState(
                                            () => _selectedCurrency = currency,
                                          );
                                          Navigator.pop(context);
                                        },
                                      ),
                                    )
                                    .toList(),
                              ),
                            ),
                          );
                        },
                      ),

                      // Security Section
                      _buildSectionHeader('Security', Icons.security),
                      _buildSettingTile(
                        title: 'Change Password',
                        subtitle: 'Update your account password',
                        icon: Icons.lock,
                        onTap: _showChangePasswordDialog,
                      ),
                      _buildToggleTile(
                        title: 'Biometric Login',
                        subtitle: 'Use fingerprint or face ID',
                        icon: Icons.fingerprint,
                        value: _biometricEnabled,
                        onChanged: (val) =>
                            setState(() => _biometricEnabled = val),
                      ),
                      _buildToggleTile(
                        title: 'Two-Factor Authentication',
                        subtitle: 'Add extra security layer',
                        icon: Icons.verified_user,
                        value: _twoFactorEnabled,
                        onChanged: (val) =>
                            setState(() => _twoFactorEnabled = val),
                      ),
                      _buildSettingTile(
                        title: 'Security PIN',
                        subtitle: 'Manage your transaction PIN',
                        icon: Icons.pin,
                        onTap: () {
                          showDialog(
                            context: context,
                            builder: (context) => _PinManagementDialog(
                              onSetPin: (pin) async {
                                try {
                                  // ignore: unused_local_variable
                                  final storage = SecureStorage();
                                  await SecureStorage.write(
                                      'transaction_pin', pin);

                                  final api = Provider.of<ApiClient>(context, listen: false);
                                  await api.post('/users/me/security/pin', {
                                    'pin_hash': _hashPin(pin),
                                  });

                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('PIN set successfully'),
                                      backgroundColor: Colors.green,
                                    ),
                                  );
                                } catch (e) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Failed to set PIN: $e'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                }
                              },
                            ),
                          );
                        },
                      ),

                      // Legal Section
                      _buildSectionHeader('Legal & Support', Icons.gavel),
                      _buildSettingTile(
                        title: 'Terms & Conditions',
                        icon: Icons.description,
                        onTap: () => _showBottomSheet(
                          context,
                          _buildTermsContent(),
                          'Terms & Conditions',
                        ),
                      ),
                      _buildSettingTile(
                        title: 'Privacy Policy',
                        icon: Icons.privacy_tip,
                        onTap: () => _showBottomSheet(
                          context,
                          _buildPrivacyContent(),
                          'Privacy Policy',
                        ),
                      ),
                      _buildSettingTile(
                        title: 'About VyRaTrader',
                        icon: Icons.info,
                        onTap: () => _showBottomSheet(
                          context,
                          _buildAboutContent(),
                          'About VyRaTrader',
                        ),
                      ),
                      _buildSettingTile(
                        title: 'Help & Support',
                        subtitle: 'Get help from our team',
                        icon: Icons.help,
                        onTap: () {
                          showModalBottomSheet(
                            context: context,
                            isScrollControlled: true,
                            backgroundColor: Colors.transparent,
                            builder: (context) => _SupportSheet(
                              onSubmit: (subject, message) async {
                                try {
                                  final api = Provider.of<ApiClient>(context, listen: false);
                                  await api.post('/support/ticket', {
                                    'subject': subject,
                                    'message': message,
                                    'priority': 'normal',
                                  });

                                  Navigator.pop(context);
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Support ticket created. We\'ll respond within 24 hours.',
                                      ),
                                      backgroundColor: Colors.green,
                                    ),
                                  );
                                } catch (e) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Failed to submit: $e'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                }
                              },
                            ),
                          );
                        },
                      ),

                      SizedBox(height: 32),

                      // Logout Button
                      Center(
                        child: Container(
                          height: 44,
                          padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 0),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [Colors.red.shade600, Colors.red.shade800],
                            ),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.red.withOpacity(0.3), width: 1),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.red.withOpacity(0.2),
                                blurRadius: 12,
                                offset: Offset(0, 6),
                              ),
                            ],
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: _showLogoutDialog,
                              borderRadius: BorderRadius.circular(12),
                              child: Center(
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.logout, color: Colors.white, size: 18),
                                    SizedBox(width: 8),
                                    Text(
                                      'Logout',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        letterSpacing: 0.2,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),

                      SizedBox(height: 20),
                    ],
                  ),
                ),
        ),
      ),
    );
  }

  String _hashPin(String pin) {
    final bytes = utf8.encode(pin);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }
}

// Edit Profile Sheet Component
class _EditProfileSheet extends StatefulWidget {
  final String currentName;
  final String currentEmail;
  final Function(String name, String email) onSave;

  const _EditProfileSheet({
    required this.currentName,
    required this.currentEmail,
    required this.onSave,
  });

  @override
  State<_EditProfileSheet> createState() => _EditProfileSheetState();
}

class _EditProfileSheetState extends State<_EditProfileSheet> {
  late TextEditingController _nameController;
  late TextEditingController _emailController;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.currentName);
    _emailController = TextEditingController(text: widget.currentEmail);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF000C1F), Color(0xFF001F3F)],
        ),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Form(
        key: _formKey,
        child: Column(
          children: [
            Container(
              margin: EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade600,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: EdgeInsets.all(20),
              child: Row(
                children: [
                  Icon(Icons.edit, color: Color(0xFF06B6D4)),
                  SizedBox(width: 12),
                  Text(
                    'Edit Profile',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            Divider(color: Color(0xFF06B6D4).withOpacity(0.2)),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(20),
                child: Column(
                  children: [
                    _buildTextField(
                      controller: _nameController,
                      label: 'Full Name',
                      icon: Icons.person,
                      validator: (val) =>
                          val?.isEmpty ?? true ? 'Required' : null,
                    ),
                    SizedBox(height: 16),
                    _buildTextField(
                      controller: _emailController,
                      label: 'Email',
                      icon: Icons.email,
                      keyboardType: TextInputType.emailAddress,
                      validator: (val) {
                        if (val?.isEmpty ?? true) return 'Required';
                        if (!val!.contains('@')) return 'Invalid email';
                        return null;
                      },
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: EdgeInsets.all(20),
              child: Center(
                child: SizedBox(
                  height: 44,
                  child: ElevatedButton(
                    onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      widget.onSave(
                        _nameController.text,
                        _emailController.text,
                      );
                      Navigator.pop(context);
                    }
                  },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Color(0xFF06B6D4),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                      minimumSize: const Size(0, 44),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: Text(
                      'Save Changes',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
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

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      validator: validator,
      style: TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: Color(0xFF06B6D4)),
        prefixIcon: Icon(icon, color: Color(0xFF06B6D4)),
        filled: true,
        fillColor: Colors.black.withOpacity(0.3),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Color(0xFF06B6D4).withOpacity(0.3)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Color(0xFF06B6D4).withOpacity(0.3)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Color(0xFF06B6D4), width: 2),
        ),
      ),
    );
  }
}

// Extension for string capitalization
extension StringExtension on String {
  String capitalizeFirst() {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }
}

// PIN Management Dialog Component
class _PinManagementDialog extends StatefulWidget {
  final Function(String pin) onSetPin;

  const _PinManagementDialog({required this.onSetPin});

  @override
  State<_PinManagementDialog> createState() => _PinManagementDialogState();
}

class _PinManagementDialogState extends State<_PinManagementDialog> {
  final _pinController = TextEditingController();
  final _confirmPinController = TextEditingController();

  @override
  void dispose() {
    _pinController.dispose();
    _confirmPinController.dispose();
    super.dispose();
  }

  void _submit() {
    final pin = _pinController.text;
    final confirm = _confirmPinController.text;

    if (pin.length != 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('PIN must be 4 digits')),
      );
      return;
    }

    if (pin != confirm) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('PINs do not match')),
      );
      return;
    }

    widget.onSetPin(pin);
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: Color(0xFF001F3F),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Row(
        children: [
          Icon(Icons.pin, color: Color(0xFF06B6D4)),
          SizedBox(width: 12),
          Text('Set Transaction PIN', style: TextStyle(color: Colors.white)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _pinController,
            keyboardType: TextInputType.number,
            maxLength: 4,
            obscureText: true,
            style: TextStyle(color: Colors.white, letterSpacing: 20),
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              labelText: 'Enter 4-digit PIN',
              labelStyle: TextStyle(color: Colors.grey.shade400),
              counterText: '',
              enabledBorder: OutlineInputBorder(
                borderSide:
                    BorderSide(color: Color(0xFF06B6D4).withOpacity(0.3)),
                borderRadius: BorderRadius.circular(12),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Color(0xFF06B6D4)),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          SizedBox(height: 16),
          TextField(
            controller: _confirmPinController,
            keyboardType: TextInputType.number,
            maxLength: 4,
            obscureText: true,
            style: TextStyle(color: Colors.white, letterSpacing: 20),
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              labelText: 'Confirm PIN',
              labelStyle: TextStyle(color: Colors.grey.shade400),
              counterText: '',
              enabledBorder: OutlineInputBorder(
                borderSide:
                    BorderSide(color: Color(0xFF06B6D4).withOpacity(0.3)),
                borderRadius: BorderRadius.circular(12),
              ),
              focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: Color(0xFF06B6D4)),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Cancel', style: TextStyle(color: Colors.grey)),
        ),
        ElevatedButton(
          onPressed: _submit,
          style: ElevatedButton.styleFrom(
            backgroundColor: Color(0xFF06B6D4),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            minimumSize: const Size(0, 40),
          ),
          child: Text('Set PIN', style: TextStyle(fontSize: 13)),
        ),
      ],
    );
  }
}

// Support Sheet Component
class _SupportSheet extends StatefulWidget {
  final Function(String subject, String message) onSubmit;

  const _SupportSheet({required this.onSubmit});

  @override
  State<_SupportSheet> createState() => _SupportSheetState();
}

class _SupportSheetState extends State<_SupportSheet> {
  final _subjectController = TextEditingController();
  final _messageController = TextEditingController();
  String _selectedCategory = 'General';

  final List<String> _categories = [
    'General',
    'Account',
    'Payments',
    'Trading',
    'Technical',
    'Other',
  ];

  @override
  void dispose() {
    _subjectController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.8,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF000C1F), Color(0xFF001F3F)],
        ),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          Container(
            margin: EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.shade600,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Padding(
            padding: EdgeInsets.all(20),
            child: Row(
              children: [
                Icon(Icons.support_agent, color: Color(0xFF06B6D4)),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Contact Support',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'We typically respond within 24 hours',
                        style: TextStyle(
                            color: Colors.grey.shade400, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: Icon(Icons.close, color: Colors.white),
                ),
              ],
            ),
          ),
          Divider(color: Color(0xFF06B6D4).withOpacity(0.2)),
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Category',
                    style: TextStyle(color: Color(0xFF06B6D4), fontSize: 14),
                  ),
                  SizedBox(height: 8),
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(12),
                      border:
                          Border.all(color: Color(0xFF06B6D4).withOpacity(0.3)),
                    ),
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _selectedCategory,
                        isExpanded: true,
                        dropdownColor: Color(0xFF001F3F),
                        style: TextStyle(color: Colors.white),
                        icon: Icon(Icons.arrow_drop_down,
                            color: Color(0xFF06B6D4)),
                        items: _categories.map((cat) {
                          return DropdownMenuItem(
                            value: cat,
                            child: Text(cat),
                          );
                        }).toList(),
                        onChanged: (val) =>
                            setState(() => _selectedCategory = val!),
                      ),
                    ),
                  ),
                  SizedBox(height: 20),
                  Text(
                    'Subject',
                    style: TextStyle(color: Color(0xFF06B6D4), fontSize: 14),
                  ),
                  SizedBox(height: 8),
                  TextField(
                    controller: _subjectController,
                    style: TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Brief description of your issue',
                      hintStyle: TextStyle(color: Colors.grey.shade600),
                      filled: true,
                      fillColor: Colors.black.withOpacity(0.3),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                            color: Color(0xFF06B6D4).withOpacity(0.3)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                            color: Color(0xFF06B6D4).withOpacity(0.3)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide:
                            BorderSide(color: Color(0xFF06B6D4), width: 2),
                      ),
                    ),
                  ),
                  SizedBox(height: 20),
                  Text(
                    'Message',
                    style: TextStyle(color: Color(0xFF06B6D4), fontSize: 14),
                  ),
                  SizedBox(height: 8),
                  TextField(
                    controller: _messageController,
                    maxLines: 6,
                    style: TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Describe your issue in detail...',
                      hintStyle: TextStyle(color: Colors.grey.shade600),
                      filled: true,
                      fillColor: Colors.black.withOpacity(0.3),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                            color: Color(0xFF06B6D4).withOpacity(0.3)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                            color: Color(0xFF06B6D4).withOpacity(0.3)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide:
                            BorderSide(color: Color(0xFF06B6D4), width: 2),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.all(20),
              child: Center(
                child: SizedBox(
                  height: 44,
                  child: ElevatedButton(
                    onPressed: () {
                    if (_subjectController.text.isEmpty ||
                        _messageController.text.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Please fill in all fields')),
                      );
                      return;
                    }
                    widget.onSubmit(
                      '[$_selectedCategory] ${_subjectController.text}',
                      _messageController.text,
                    );
                  },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Color(0xFF06B6D4),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                      minimumSize: const Size(0, 44),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      elevation: 0,
                    ),
                    child: const Text(
                      'Submit Ticket',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, letterSpacing: 0.2),
                    ),
                  ),
                ),
              ),
          ),
        ],
      ),
    );
  }
}
