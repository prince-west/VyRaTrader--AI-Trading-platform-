// lib/routes/app_routes.dart
import 'package:flutter/material.dart';

// Onboarding & Auth
import '../screens/onboarding/onboarding_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/auth/forgot_password_screen.dart';

// Main App Screens
import '../screens/home/main_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/trading/trade_screen.dart';
import '../screens/payments/payments_screen.dart';
import '../screens/payments/payment_detail_screen.dart';

// Profile & Settings
import '../screens/profile/profile_screen.dart';

// Notifications
import '../screens/notifications/notifications_screen.dart';

// Legal Screens - Full Terms & Privacy Policy
class TermsScreen extends StatelessWidget {
  const TermsScreen({super.key});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF000C1F),
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF001F3F),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF06B6D4).withOpacity(0.3),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: Colors.white),
                    onPressed: () => Navigator.pop(context),
                  ),
                  const Expanded(
                    child: Text(
                      'Terms & Conditions',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildLegalSection(context, '1. Acceptance of Terms',
                        'By accessing or using VyRaTrader, you agree to be bound by these Terms and Conditions. If you do not agree to these terms, you may not use the Platform.'),
                    _buildLegalSection(context, '2. Definitions',
                        '"Platform" refers to VyRaTrader, an AI-powered trading platform. "User" refers to anyone accessing the Platform. "Prince AI" refers to the artificial intelligence system that generates trading signals and recommendations.'),
                    _buildLegalSection(context, '3. Eligibility',
                        'You must be at least 18 years of age and have the legal capacity to enter into binding agreements in your jurisdiction. You must not use the Platform if it is illegal or prohibited.'),
                    _buildLegalSection(context, '4. Account Registration and Security',
                        'You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorized access. You are responsible for all activities that occur under your account.'),
                    _buildLegalSection(context, '5. AI Trading Disclaimer',
                        'Prince AI is an artificial intelligence system that provides trading signals and recommendations. The AI\'s recommendations are based on algorithmic analysis and are NOT financial advice. Past performance does NOT guarantee future results. All trading decisions are made at your own risk.'),
                    _buildLegalSection(context, '6. Trading Risks and Liabilities',
                        'Trading involves substantial risk of loss and is not suitable for all investors. You may lose all or a portion of your invested capital. Market volatility can cause sudden and significant losses. We are NOT responsible for your trading losses.'),
                    _buildLegalSection(context, '7. Deposits and Withdrawals',
                        'Minimum deposit: GHS 500 or equivalent. Deposit fee: 2% of the deposit amount. Withdrawal fee: 5% of the withdrawal amount. Withdrawals may take 1-5 business days to process. We reserve the right to verify your identity before processing withdrawals.'),
                    _buildLegalSection(context, '8. Fees and Charges',
                        'All fees are disclosed at the time of deposit or withdrawal. Fees may vary by payment method. Third-party payment processor fees are separate and may apply. We reserve the right to update fees with 30 days\' notice.'),
                    _buildLegalSection(context, '9. Stop-Loss and Risk Management',
                        'The Platform provides risk management tools (stop-loss, take-profit). Low-risk: up to 3% stop-loss, 25% max exposure. Medium-risk: up to 7% stop-loss, 25% max exposure. High-risk: up to 15% stop-loss, 60% max exposure. You can adjust your risk profile in settings.'),
                    _buildLegalSection(context, '10. Intellectual Property',
                        'All content on the Platform is owned by VyRaTrader or its licensors. The AI algorithms, strategies, and Prince AI are proprietary intellectual property. You may NOT copy, reproduce, or reverse-engineer any part of the Platform.'),
                    _buildLegalSection(context, '11. Privacy and Data',
                        'Your use of the Platform is also governed by our Privacy Policy. We collect and use your data as described in the Privacy Policy. We use your trading data to improve AI models. You have the right to request deletion of your data.'),
                    _buildLegalSection(context, '12. User Conduct',
                        'You agree to use the Platform only for lawful purposes. You may NOT use the Platform for money laundering or illegal activities. You may NOT attempt to manipulate markets or engage in fraudulent activities. You may NOT share your account with others.'),
                    _buildLegalSection(context, '13. API and Data Usage',
                        'The Platform uses multiple third-party APIs for market data. API rate limits may affect data availability. If data is unavailable, Prince AI will inform you and suggest alternatives. We cache API responses to reduce consumption and costs.'),
                    _buildLegalSection(context, '14. Limitation of Liability',
                        'TO THE MAXIMUM EXTENT PERMITTED BY LAW, VYRATRADER SHALL NOT BE LIABLE FOR: any losses resulting from trading decisions, AI prediction errors, data delays, technical failures, unauthorized access, or third-party service failures. Our total liability shall not exceed the amount you paid in fees in the last 12 months.'),
                    _buildLegalSection(context, '15. Indemnification',
                        'You agree to indemnify and hold harmless VyRaTrader, its officers, employees, and agents. This includes all claims, losses, damages, liabilities, costs, and expenses related to any breach of these terms by you.'),
                    _buildLegalSection(context, '16. Termination',
                        'We may suspend or terminate your account for violation of these terms, suspected fraudulent activity, or regulatory compliance requirements. You may close your account at any time. Upon termination, you are entitled to your remaining balance (minus fees).'),
                    _buildLegalSection(context, '17. Disputes and Governing Law',
                        'These terms are governed by the laws of Ghana. Any disputes shall be resolved through arbitration in Accra, Ghana. Class action lawsuits are waived to the extent permitted by law.'),
                    _buildLegalSection(context, '18. Changes to Terms',
                        'We may update these terms at any time. You will be notified of material changes via email or Platform notification. Continued use of the Platform after changes constitutes acceptance. We recommend reviewing terms periodically.'),
                    _buildLegalSection(context, '19. Third-Party Services',
                        'The Platform integrates with payment processors (Hubtel, Paystack, Stripe), trading exchanges (Binance, OANDA), market data providers (CoinGecko, Alpha Vantage), and AI providers (OpenAI). Third-party terms apply to their respective services.'),
                    _buildLegalSection(context, '20. Reliable Signals and Wait Periods',
                        'Prince AI provides signals based on available market data. If market data is unavailable due to API limits, Prince AI will inform you. You may need to wait until the next day for updated data. Prince AI may suggest alternative markets (forex) during unavailability.'),
                    _buildLegalSection(context, '21. Notifications',
                        'Prince AI may send push notifications when reliable signals are detected. You can opt-out of notifications in settings. Notifications expire after a certain time (typically 1-4 hours). You are responsible for acting on signals promptly.'),
                    _buildLegalSection(context, '22. Risk Management and Stop Loss',
                        'All trades are subject to risk management rules based on your risk profile. Prince AI recommends stop-loss levels, but you can override them. We strongly recommend using stop-loss orders to limit losses. Dynamic position sizing is applied based on market volatility.'),
                    _buildLegalSection(context, '23. Support and Help',
                        'For support, contact us at support@vyratrader.com. We aim to respond within 24-48 hours. Prince AI can help answer questions within the Platform.'),
                    _buildLegalSection(context, '24. KYC and Compliance',
                        'We are committed to Know Your Customer (KYC) compliance. We may request additional documentation to verify your identity. We comply with anti-money laundering (AML) regulations. We may freeze accounts pending investigation if suspicious activity is detected.'),
                    _buildLegalSection(context, '25. Force Majeure',
                        'We are not liable for delays or failures due to circumstances beyond our control. This includes but is not limited to: natural disasters, war, pandemic, cyber attacks, etc.'),
                    _buildLegalSection(context, '26. Entire Agreement',
                        'These terms constitute the entire agreement between you and VyRaTrader. Any previous oral or written agreements are superseded.'),
                    _buildLegalSection(context, '27. Severability',
                        'If any provision is deemed invalid, the remainder of terms remains in effect.'),
                    _buildLegalSection(context, '28. No Waiver',
                        'Our failure to enforce a term does not constitute a waiver of our rights.'),
                    _buildLegalSection(context, '29. Contact Information',
                        'If you have questions about these terms, contact us at: Email: legal@vyratrader.com, Address: Accra, Ghana. By using VyRaTrader, you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions.'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildLegalSection(BuildContext context, String title, String content) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF06B6D4),
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
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
}

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF000C1F),
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF001F3F),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF06B6D4).withOpacity(0.3),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: Colors.white),
                    onPressed: () => Navigator.pop(context),
                  ),
                  const Expanded(
                    child: Text(
                      'Privacy Policy',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildLegalSection(context, '1. Information We Collect',
                        'We collect personal information (name, email, phone, address, date of birth), financial data (account balances, transactions, trading history, deposits, withdrawals), usage data (app interactions, AI chat logs, feature usage, screen views), device information (IP address, device type, operating system), and market data (trade preferences, signals generated for you, portfolio composition).'),
                    _buildLegalSection(context, '2. How We Use Your Data',
                        'We use your data to: provide services (process trades, manage accounts, execute orders), improve AI (train Prince AI using aggregated, anonymized trading data), personalize experience (customize signals and recommendations), communicate (send updates, notifications, alerts, marketing with consent), ensure security (detect fraud, prevent abuse, verify identity), meet compliance (legal obligations, KYC requirements, AML checks), and analyze usage patterns to improve the Platform.'),
                    _buildLegalSection(context, '3. Data Sharing',
                        'We share data with payment processors (Hubtel, Paystack) for transactions, trading exchanges (Binance, OANDA) for order execution, market data providers for real-time prices, cloud service providers for hosting, and analytics services (anonymized). We do NOT sell your personal data to third parties. We may share data if required by law or to protect our rights.'),
                    _buildLegalSection(context, '4. Data Security',
                        'We use industry-standard encryption (SSL/TLS) for data in transit. Sensitive data is encrypted at rest. Access controls limit who can view your data. Payment information is tokenized and never stored directly. We conduct regular security audits.'),
                    _buildLegalSection(context, '5. Your Rights',
                        'You have the right to: access (request a copy of your data), correction (update incorrect information), deletion (request deletion subject to legal requirements), portability (export your data in a machine-readable format), opt-out (unsubscribe from marketing communications), and objection (object to certain data processing).'),
                    _buildLegalSection(context, '6. Data Retention',
                        'We retain data while your account is active. After account closure: 90 days for legal compliance, then deletion. Trading data may be kept longer for analytics (anonymized).'),
                    _buildLegalSection(context, '7. Cookies and Tracking',
                        'We use cookies and similar technologies for authentication, preferences, analytics, and security. You can manage cookies in your browser settings.'),
                    _buildLegalSection(context, '8. AI and Machine Learning',
                        'Your trading data (anonymized) helps train Prince AI to improve predictions for all users. Your individual identity is not revealed to other users. We may use third-party AI services (OpenAI, etc.) - their privacy policies apply.'),
                    _buildLegalSection(context, '9. International Users',
                        'We comply with GDPR for EU users. Data is primarily stored in Ghana. Some data may be processed in other countries for service delivery.'),
                    _buildLegalSection(context, '10. Children\'s Privacy',
                        'We do not knowingly collect data from children under 18. If you believe we have, contact us to have it removed.'),
                    _buildLegalSection(context, '11. Changes to This Policy',
                        'We may update this policy periodically. You will be notified of material changes. Continued use constitutes acceptance.'),
                    _buildLegalSection(context, '12. Contact Us',
                        'For privacy concerns, contact: privacy@vyratrader.com'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildLegalSection(BuildContext context, String title, String content) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF06B6D4),
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
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
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('About VyRaTrader')),
      body: const Center(child: Text('About VyRaTrader Content')),
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: const Center(child: Text('Settings Content')),
    );
  }
}

class SecurityScreen extends StatelessWidget {
  const SecurityScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Security')),
      body: const Center(child: Text('Security Content')),
    );
  }
}

class PrinceChatScreen extends StatelessWidget {
  const PrinceChatScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Prince AI Chat')),
      body: const Center(child: Text('Full Screen Prince Chat')),
    );
  }
}

class TradeDetailScreen extends StatelessWidget {
  const TradeDetailScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Trade Details')),
      body: const Center(child: Text('Trade Details Content')),
    );
  }
}

/// App routing configuration
/// Matches VyRaTrader blueprint screen structure
class AppRoutes {
  // ============================================================================
  // ROUTE NAMES
  // ============================================================================

  // Onboarding & Auth (Blueprint Section 2)
  static const String onboarding = '/onboarding';
  static const String login = '/login';
  static const String signup = '/signup';
  static const String forgotPassword = '/forgot-password';
  static const String forgot = '/forgot'; // Alias
  static const String terms = '/terms';

  // Main App (Blueprint Section 4)
  static const String main = '/main';
  static const String dashboard = '/dashboard';
  static const String home = '/'; // Alias for dashboard

  // Trading (Blueprint Section 6)
  static const String trading = '/trading';
  static const String tradeDetail = '/trade-detail';

  // Payments (Blueprint Section 5)
  static const String payments = '/payments';
  static const String paymentDetail = '/payment-detail';

  // AI Chat (Blueprint Section 3)
  static const String princeChat = '/prince-chat';

  // Profile & Settings (Blueprint Section 7)
  static const String profile = '/profile';
  static const String settings = '/settings';
  static const String security = '/security';

  // Notifications (Blueprint Section 9)
  static const String notifications = '/notifications';

  // Legal (Blueprint Section 8)
  static const String privacy = '/privacy';
  static const String about = '/about';

  // ============================================================================
  // ROUTE MAP
  // ============================================================================

  static Map<String, WidgetBuilder> get routes => {
        // Onboarding & Auth
        onboarding: (_) => const OnboardingScreen(),
        login: (_) => const LoginScreen(),
        signup: (_) => const SignupScreen(),
        forgotPassword: (_) => const ForgotPasswordScreen(),
        forgot: (_) => const ForgotPasswordScreen(), // Alias
        terms: (_) => const TermsScreen(),

        // Main App
        main: (_) => const MainScreen(),
        home: (_) => const DashboardScreen(),
        dashboard: (_) => const DashboardScreen(),

        // Trading
        trading: (_) => const TradeScreen(),
        tradeDetail: (_) => const TradeDetailScreen(),

        // Payments - Updated to use correct screen name
        payments: (_) => const PaymentsScreen(),
        paymentDetail: (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          if (args is Map<String, dynamic>) {
            return PaymentDetailScreen(payment: args);
          }
          return PaymentDetailScreen(payment: const {});
        },

        // AI Chat
        princeChat: (_) => const PrinceChatScreen(),

        // Profile & Settings
        profile: (_) => const ProfileScreen(),
        settings: (_) => const SettingsScreen(),
        security: (_) => const SecurityScreen(),

        // Notifications
        notifications: (_) => const NotificationsScreen(),

        // Legal
        privacy: (_) => const PrivacyPolicyScreen(),
        about: (_) => const AboutScreen(),
      };

  // ============================================================================
  // NAVIGATION HELPERS
  // ============================================================================

  /// Navigate to a route
  static Future<T?> navigateTo<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushNamed<T>(context, routeName, arguments: arguments);
  }

  /// Navigate and replace current route
  static Future<T?> navigateReplaceTo<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushReplacementNamed(
      context,
      routeName,
      arguments: arguments,
    );
  }

  /// Navigate and clear stack
  static Future<T?> navigateAndClearStack<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushNamedAndRemoveUntil<T>(
      context,
      routeName,
      (route) => false,
      arguments: arguments,
    );
  }

  /// Go back
  static void goBack(BuildContext context, {Object? result}) {
    Navigator.pop(context, result);
  }

  /// Check if can go back
  static bool canGoBack(BuildContext context) {
    return Navigator.canPop(context);
  }

  // ============================================================================
  // INITIAL ROUTE LOGIC
  // ============================================================================

  /// Determine initial route based on app state
  static String getInitialRoute({
    required bool isFirstLaunch,
    required bool isAuthenticated,
    required bool hasAcceptedTerms,
  }) {
    if (isFirstLaunch || !hasAcceptedTerms) {
      return onboarding;
    }

    if (!isAuthenticated) {
      return login;
    }

    return dashboard;
  }

  // ============================================================================
  // ROUTE GUARDS (for protected routes)
  // ============================================================================

  /// Check if route requires authentication
  static bool requiresAuth(String routeName) {
    const authRequiredRoutes = [
      dashboard,
      home,
      trading,
      tradeDetail,
      payments,
      paymentDetail,
      princeChat,
      profile,
      settings,
      security,
      notifications,
    ];

    return authRequiredRoutes.contains(routeName);
  }

  /// Check if route is public (no auth needed)
  static bool isPublicRoute(String routeName) {
    const publicRoutes = [
      onboarding,
      login,
      signup,
      forgotPassword,
      forgot,
      terms,
      privacy,
      about,
    ];

    return publicRoutes.contains(routeName);
  }

  // ============================================================================
  // ROUTE ARGUMENTS HELPERS
  // ============================================================================

  /// Extract arguments from route
  static T? getArguments<T>(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments;
    return args is T ? args : null;
  }

  /// Navigate with typed arguments
  static Future<T?> navigateWithArgs<T>(
    BuildContext context,
    String routeName,
    Object arguments,
  ) {
    return Navigator.pushNamed<T>(context, routeName, arguments: arguments);
  }

  // ============================================================================
  // SPECIFIC NAVIGATION HELPERS
  // ============================================================================

  /// Navigate to trade detail with trade ID
  static Future<void> navigateToTradeDetail(
    BuildContext context,
    String tradeId,
  ) {
    return navigateWithArgs(context, tradeDetail, {'trade_id': tradeId});
  }

  /// Navigate to payment detail with payment method
  static Future<void> navigateToPaymentDetail(
    BuildContext context,
    Map<String, dynamic> paymentData,
  ) {
    return navigateWithArgs(context, paymentDetail, paymentData);
  }

  /// Navigate to Prince chat with optional initial message
  static Future<void> navigateToPrinceChat(
    BuildContext context, {
    String? initialMessage,
  }) {
    return navigateWithArgs(context, princeChat, {
      if (initialMessage != null) 'initial_message': initialMessage,
    });
  }

  /// Logout and navigate to login
  static Future<void> logout(BuildContext context) {
    return navigateAndClearStack(context, login);
  }

  /// Complete onboarding and navigate to signup
  static Future<void> completeOnboarding(BuildContext context) {
    return navigateReplaceTo(context, signup);
  }

  /// Login success - navigate to dashboard
  static Future<void> loginSuccess(BuildContext context) {
    return navigateAndClearStack(context, dashboard);
  }

  /// Signup success - navigate to dashboard
  static Future<void> signupSuccess(BuildContext context) {
    return navigateAndClearStack(context, dashboard);
  }
}

// ============================================================================
// ROUTE ARGUMENTS CLASSES (for type safety)
// ============================================================================

/// Arguments for trade detail screen
class TradeDetailArguments {
  final String tradeId;
  final bool showExplanation;

  TradeDetailArguments({required this.tradeId, this.showExplanation = false});
}

/// Arguments for payment detail screen
class PaymentDetailArguments {
  final String method; // 'momo', 'card', 'paypal', 'crypto'
  final String type; // 'deposit' or 'withdrawal'
  final double? prefilledAmount;

  PaymentDetailArguments({
    required this.method,
    required this.type,
    this.prefilledAmount,
  });
}

/// Arguments for Prince chat screen
class PrinceChatArguments {
  final String? initialMessage;
  final String? tradeId; // If opened from trade explanation

  PrinceChatArguments({this.initialMessage, this.tradeId});
}
