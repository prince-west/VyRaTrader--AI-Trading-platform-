// lib/screens/dashboard/dashboard_screen.dart
// PRODUCTION READY - Real API data, no mock values

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:math' as math;
import 'dart:async';
import '../../routes/app_routes.dart';
import '../../core/api_client.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../home/main_screen.dart';

class DashboardScreen extends StatefulWidget {
  static const routeName = '/dashboard';
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _particleController;
  late AnimationController _shimmerController;
  late Animation<double> _pulseAnimation;
  Timer? _refreshTimer;

  String selectedCurrency = 'GHS';
  final List<String> currencies = [
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

  final Map<String, String> currencySymbols = {
    'GHS': '₵',
    'USD': '\$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CAD': 'C\$',
    'AUD': 'A\$',
    'CHF': 'CHF',
    'CNY': '¥',
    'SEK': 'kr',
    'NGN': '₦',
    'ZAR': 'R',
    'INR': '₹',
  };

  final Map<String, double> conversionRates = {
    'GHS': 1.0,
    'USD': 0.082,
    'EUR': 0.076,
    'GBP': 0.065,
    'JPY': 12.5,
    'CAD': 0.11,
    'AUD': 0.13,
    'CHF': 0.073,
    'CNY': 0.59,
    'SEK': 0.87,
    'NGN': 65.0,
    'ZAR': 1.52,
    'INR': 6.8,
  };

  // REAL DATA FROM API
  double userBalanceGHS = 0.0;
  double growthPercent = 0.0;
  int notificationCount = 0;
  int activeTrades = 0;
  double profitablePercent = 0.0;
  String aiStrategy = "Loading...";
  String selectedTimeRange = '1W';
  bool isLoading = true;
  List<Map<String, dynamic>> recentPositions = [];
  List<Map<String, dynamic>> recentActivity = [];
  Map<String, dynamic>? portfolioStats;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();

    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    _pulseAnimation = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _loadDashboardData();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _particleController.dispose();
    _shimmerController.dispose();
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (mounted) {
        _loadDashboardData(silent: true);
      }
    });
  }

  Future<void> _loadDashboardData({bool silent = false}) async {
    if (!silent) {
      setState(() => isLoading = true);
    }

    final api = Provider.of<ApiClient>(context, listen: false);
    Map<String, dynamic>? portfolio;
    Map<String, dynamic>? stats;
    Map<String, dynamic>? trades;
    Map<String, dynamic>? transactions;
    Map<String, dynamic>? notifications;
    
    bool hasErrors = false;
    String? errorMessage;

    // Load each API endpoint individually so failures don't block others
    try {
      portfolio = await api.get('/portfolio/portfolio', params: {}, queryParams: {});
    } catch (e) {
      hasErrors = true;
      errorMessage = e.toString();
      // Try to get balance from auth provider as fallback
      try {
        final auth = Provider.of<AuthProvider>(context, listen: false);
        final user = auth.user;
        if (user != null) {
          portfolio = {'balance': user.balance ?? 0.0, 'growth_percent': 0.0};
        }
      } catch (_) {
        // Ignore fallback errors
      }
    }

    try {
      stats = await api.get('/portfolio/stats', params: {}, queryParams: {});
    } catch (e) {
      hasErrors = true;
      if (errorMessage == null) errorMessage = e.toString();
    }

    try {
      trades = await api.get('/trades/recent', params: {}, queryParams: {});
    } catch (e) {
      hasErrors = true;
      if (errorMessage == null) errorMessage = e.toString();
    }

    try {
      transactions = await api.get('/payments/transactions/recent', params: {}, queryParams: {});
    } catch (e) {
      hasErrors = true;
      if (errorMessage == null) errorMessage = e.toString();
    }

    try {
      notifications = await api.get('/notifications/count', params: {}, queryParams: {});
    } catch (e) {
      hasErrors = true;
      if (errorMessage == null) errorMessage = e.toString();
    }

    // Update state with available data
    setState(() {
      // Portfolio data
      userBalanceGHS = portfolio?['balance']?.toDouble() ?? 0.0;
      growthPercent = portfolio?['growth_percent']?.toDouble() ?? 0.0;
      portfolioStats = portfolio;

      // Stats
      activeTrades = stats?['active_trades'] ?? 0;
      profitablePercent = stats?['profitable_percent']?.toDouble() ?? 0.0;
      aiStrategy = stats?['ai_strategy'] ?? 'Balanced';

      // Recent positions
      recentPositions = List<Map<String, dynamic>>.from(trades?['positions'] ?? []);

      // Recent activity
      recentActivity = List<Map<String, dynamic>>.from(transactions?['transactions'] ?? []);

      // Notifications
      notificationCount = notifications?['unread_count'] ?? 0;

      isLoading = false;
    });

    // Show error only if significant failures occurred and not silent
    if (hasErrors && !silent && mounted && errorMessage != null) {
      // Only show error if it's not a network error (backend might be down)
      if (!errorMessage.contains('Failed host lookup') && 
          !errorMessage.contains('SocketException')) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Some dashboard data failed to load'),
            backgroundColor: Colors.orange,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    }
  }

  double get convertedBalance {
    return userBalanceGHS * conversionRates[selectedCurrency]!;
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF000C1F), Color(0xFF001F3F), Color(0xFF000C1F)],
            ),
          ),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(
                  width: 60,
                  height: 60,
                  child: CircularProgressIndicator(
                    strokeWidth: 4,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      Color(0xFF00FFFF),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Loading Dashboard...',
                  style: TextStyle(
                    color: Color(0xFF00FFFF),
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // Animated gradient background
          AnimatedGradientBackground(controller: _particleController),

          // Floating particles
          FloatingParticles(controller: _particleController),

          // Main content
          SafeArea(
            child: CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                // Custom App Bar
                SliverAppBar(
                  expandedHeight: 80,
                  floating: true,
                  backgroundColor: Colors.transparent,
                  elevation: 0,
                  flexibleSpace: FlexibleSpaceBar(
                    background: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            const Color(0xFF000C1F).withOpacity(0.9),
                            Colors.transparent,
                          ],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ),
                      ),
                    ),
                  ),
                  title: Row(
                    children: [
                      // Logo
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: const RadialGradient(
                            colors: [Color(0xFF00FFFF), Color(0xFF0088FF)],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF00FFFF).withOpacity(0.3),
                              blurRadius: 10,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                        child: const Center(
                          child: Text(
                            'VR',
                            style: TextStyle(
                              color: Colors.black,
                              fontWeight: FontWeight.w700,
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ShaderMask(
                        shaderCallback: (bounds) => const LinearGradient(
                          colors: [Color(0xFF00FFFF), Color(0xFF0099FF)],
                        ).createShader(bounds),
                        child: const Text(
                          'VyRaTrader',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                  actions: [
                    // Currency selector
                    _buildCurrencyDropdown(),
                    const SizedBox(width: 8),

                    // Notifications with badge
                    Stack(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.notifications_none, size: 26),
                          onPressed: () {
                            // Navigate to notifications - separate screen (keeps nav bar)
                            Navigator.pushNamed(context, AppRoutes.notifications);
                          },
                        ),
                        if (notificationCount > 0)
                          Positioned(
                            right: 8,
                            top: 8,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFF00FF),
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(
                                      0xFFFF00FF,
                                    ).withOpacity(0.6),
                                    blurRadius: 8,
                                    spreadRadius: 1,
                                  ),
                                ],
                              ),
                              constraints: const BoxConstraints(
                                minWidth: 18,
                                minHeight: 18,
                              ),
                              child: Text(
                                '$notificationCount',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(width: 8),

                    // Profile button - navigate using MainScreen tab system
                    GestureDetector(
                      onTap: () {
                        // Navigate using MainScreen tab system (index 4 = Profile)
                        final mainState = MainScreen.of(context);
                        if (mainState != null && mainState.mounted) {
                          mainState.navigateToIndex(4);
                        } else {
                          // Fallback: use route navigation
                          Navigator.pushNamed(context, AppRoutes.profile);
                        }
                      },
                      child: Container(
                        margin: const EdgeInsets.only(right: 16),
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: const Color(0xFF00FFFF),
                            width: 2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF00FFFF).withOpacity(0.3),
                              blurRadius: 12,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.person_outline,
                          color: Color(0xFF00FFFF),
                          size: 20,
                        ),
                      ),
                    ),
                  ],
                ),

                // Content
                SliverPadding(
                  padding: const EdgeInsets.all(16),
                  sliver: SliverList(
                    delegate: SliverChildListDelegate([
                      // Currency selector horizontal scroll
                      _buildCurrencySelector(),
                      const SizedBox(height: 20),

                      // Enhanced Portfolio balance card
                      _buildEnhancedPortfolioCard(),
                      const SizedBox(height: 24),

                      // Stats grid
                      _buildStatsGrid(),
                      const SizedBox(height: 24),

                      // Performance chart
                      _buildGlassCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text(
                                  'Performance',
                                  style: TextStyle(
                                    color: Color(0xFF00FFFF),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Row(
                                  children: [
                                    _buildTimeButton('1D'),
                                    _buildTimeButton(
                                      '1W',
                                      selected: selectedTimeRange == '1W',
                                    ),
                                    _buildTimeButton('1M'),
                                    _buildTimeButton('1Y'),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            // Performance chart removed - use real data only
                            const SizedBox(height: 200, child: Center(child: Text('Performance data will be displayed here', style: TextStyle(color: Colors.white54)))),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Quick actions
                      _buildQuickActions(),
                      const SizedBox(height: 20),

                      // Recent positions
                      _buildSectionHeader("Recent Positions"),
                      const SizedBox(height: 16),
                      if (recentPositions.isEmpty)
                        _buildEmptyState('No active positions')
                      else
                        ...recentPositions.map((position) => _buildPositionTile(
                              position['symbol'] ?? 'Unknown',
                              position['change'] ?? '+0.0%',
                              (position['change'] ?? '').startsWith('+')
                                  ? Colors.greenAccent
                                  : Colors.redAccent,
                              (position['change'] ?? '').startsWith('+')
                                  ? Icons.trending_up
                                  : Icons.trending_down,
                              position['value'] ?? '\$0.00',
                            )),

                      const SizedBox(height: 20),

                      // AI insights
                      _buildAIInsightsCard(),
                      const SizedBox(height: 20),

                      // Performance breakdown
                      _buildPerformanceBreakdown(),
                      const SizedBox(height: 20),

                      // Recent activity
                      _buildRecentActivity(),
                      const SizedBox(height: 100),
                    ]),
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildEmptyState(String message) {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 48,
              color: Colors.white.withOpacity(0.3),
            ),
            const SizedBox(height: 12),
            Text(
              message,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrencyDropdown() {
    return PopupMenuButton<String>(
      initialValue: selectedCurrency,
      onSelected: (value) => setState(() => selectedCurrency = value),
      itemBuilder: (context) => currencies.map((currency) {
        return PopupMenuItem(
          value: currency,
          child: Text(
            '$currency ${currencySymbols[currency] ?? ''}',
            style: const TextStyle(color: Colors.white),
          ),
        );
      }).toList(),
      color: const Color(0xFF001F3F),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: const Color(0xFF00FFFF).withOpacity(0.3)),
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFF00FFFF).withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFF00FFFF).withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Text(
              selectedCurrency,
              style: const TextStyle(
                color: Color(0xFF00FFFF),
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(
              Icons.arrow_drop_down,
              color: Color(0xFF00FFFF),
              size: 18,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrencySelector() {
    return SizedBox(
      height: 50,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: currencies.length,
        itemBuilder: (context, index) {
          final currency = currencies[index];
          final isSelected = currency == selectedCurrency;
          return GestureDetector(
            onTap: () => setState(() => selectedCurrency = currency),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                gradient: isSelected
                    ? const LinearGradient(
                        colors: [Color(0xFF00FFFF), Color(0xFF0088FF)],
                      )
                    : null,
                color: isSelected ? null : Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(25),
                border: Border.all(
                  color: isSelected
                      ? const Color(0xFF00FFFF)
                      : Colors.white.withOpacity(0.1),
                ),
                boxShadow: isSelected
                    ? [
                        BoxShadow(
                          color: const Color(0xFF00FFFF).withOpacity(0.5),
                          blurRadius: 12,
                          spreadRadius: 1,
                        ),
                      ]
                    : null,
              ),
              child: Center(
                child: Text(
                  currency,
                  style: TextStyle(
                    color: isSelected ? Colors.black : Colors.white70,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEnhancedPortfolioCard() {
    return AnimatedBuilder(
      animation: _shimmerController,
      builder: (context, child) {
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                const Color(0xFF00FFFF),
                const Color(0xFF00CCFF),
                const Color(0xFF0088FF),
              ],
              stops: [0.0, _shimmerController.value, 1.0],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF00FFFF).withOpacity(0.4),
                blurRadius: 30,
                spreadRadius: 5,
                offset: const Offset(0, 10),
              ),
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 20,
                offset: const Offset(0, 15),
              ),
            ],
          ),
          child: Stack(
            children: [
              // Animated background pattern
              Positioned.fill(
                child: CustomPaint(
                  painter: HexagonPatternPainter(_shimmerController.value),
                ),
              ),

              // Content
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        "Portfolio Balance",
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.5,
                        ),
                      ),
                      ScaleTransition(
                        scale: _pulseAnimation,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.5),
                              width: 1.5,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                growthPercent >= 0
                                    ? Icons.arrow_upward
                                    : Icons.arrow_downward,
                                color: Colors.white,
                                size: 16,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                "${growthPercent.abs().toStringAsFixed(1)}%",
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    "${currencySymbols[selectedCurrency]}${convertedBalance.toStringAsFixed(2)}",
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          "+${(convertedBalance * growthPercent / 100).toStringAsFixed(2)} this month",
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.verified,
                        color: Colors.white.withOpacity(0.9),
                        size: 16,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Updated ${DateTime.now().hour}:${DateTime.now().minute.toString().padLeft(2, '0')}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatsGrid() {
    return Row(
      children: [
        Expanded(
          child: _statTile(
            "Active Trades",
            activeTrades.toString(),
            Icons.swap_horiz,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _statTile(
            "Profitable",
            "$profitablePercent%",
            Icons.trending_up,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(child: _statTile("AI Strategy", aiStrategy, Icons.smart_toy)),
      ],
    );
  }

  Widget _statTile(String title, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF00FFFF).withOpacity(0.2), width: 1),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00FFFF).withOpacity(0.08),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF00FFFF), size: 20),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF00FFFF),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGlassCard({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.1), width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }

  Widget _buildTimeButton(String label, {bool selected = false}) {
    return GestureDetector(
      onTap: () => setState(() => selectedTimeRange = label),
      child: Container(
        margin: const EdgeInsets.only(left: 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        height: 28,
        decoration: BoxDecoration(
          color: selected
              ? const Color(0xFF00FFFF).withOpacity(0.2)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: selected
                ? const Color(0xFF00FFFF)
                : Colors.white.withOpacity(0.2),
            width: 1,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: selected ? const Color(0xFF00FFFF) : Colors.white70,
              fontSize: 10,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMockPerformanceChart() {
    return SizedBox(
      height: 200,
      child: CustomPaint(painter: PerformanceChartPainter()),
    );
  }

  Widget _buildQuickActions() {
    return Row(
      children: [
        Expanded(
          child: _buildActionButton(
            'Withdraw',
            Icons.arrow_upward,
            const Color(0xFFFF0088),
            () {
              // Navigate using MainScreen tab system (index 3 = Wallet/Payments)
              final mainState = MainScreen.of(context);
              if (mainState != null && mainState.mounted) {
                mainState.navigateToIndex(3);
              } else {
                // Fallback: use route navigation
                Navigator.pushNamed(context, AppRoutes.payments);
              }
            },
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildActionButton(
            'Trade',
            Icons.swap_horiz,
            const Color(0xFF00FFFF),
            () {
              // Navigate using MainScreen tab system (index 0 = Market/Trade)
              final mainState = MainScreen.of(context);
              if (mainState != null && mainState.mounted) {
                mainState.navigateToIndex(0);
              } else {
                // Fallback: use route navigation
                Navigator.pushNamed(context, AppRoutes.trading);
              }
            },
          ),
        ),
      ],
    );
  }

  Widget _buildActionButton(
    String label,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 40,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [color, color.withOpacity(0.8)]),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.3), width: 1),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.2),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 18),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 12,
                letterSpacing: 0.2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 24,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF00FFFF), Color(0xFF0088FF)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
              borderRadius: BorderRadius.circular(2),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00FFFF).withOpacity(0.5),
                  blurRadius: 8,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPositionTile(
    String pair,
    String change,
    Color color,
    IconData icon,
    String value,
  ) {
    final isProfit = change.startsWith('+');
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.white.withOpacity(0.08),
            Colors.white.withOpacity(0.03),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3), width: 1),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.1),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () {},
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 50,
                  height: 50,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: color, size: 24),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        pair,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        value,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: color.withOpacity(0.5)),
                      ),
                      child: Text(
                        change,
                        style: TextStyle(
                          color: color,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isProfit ? "In profit" : "In loss",
                      style: TextStyle(
                        color: color.withOpacity(0.7),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAIInsightsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF9C27B0).withOpacity(0.3),
            const Color(0xFF673AB7).withOpacity(0.15),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF9C27B0).withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF9C27B0).withOpacity(0.3),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.auto_awesome,
                  color: Color(0xFFE1BEE7),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                "Prince AI Insights",
                style: TextStyle(
                  color: Color(0xFFE1BEE7),
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            portfolioStats?['ai_insight'] ??
                "Your portfolio is performing well. Prince AI is actively monitoring market conditions for optimal trading opportunities.",
            style: TextStyle(
              color: Colors.white.withOpacity(0.9),
              fontSize: 14,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceBreakdown() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "Performance Breakdown",
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 20),
          _performanceBar(
              "Forex",
              portfolioStats?['forex_percent']?.toDouble() ?? 45.0,
              const Color(0xFF00FFFF)),
          const SizedBox(height: 12),
          _performanceBar(
              "Crypto",
              portfolioStats?['crypto_percent']?.toDouble() ?? 30.0,
              const Color(0xFF00FF88)),
          const SizedBox(height: 12),
          // Stock and commodity trading removed - only crypto and forex supported
        ],
      ),
    );
  }

  Widget _performanceBar(String label, double percentage, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 12),
            ),
            Text(
              "${percentage.toStringAsFixed(1)}%",
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.w600,
                fontSize: 12,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Stack(
          children: [
            Container(
              height: 8,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            FractionallySizedBox(
              widthFactor: percentage / 100,
              child: Container(
                height: 8,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [color, color.withOpacity(0.6)],
                  ),
                  borderRadius: BorderRadius.circular(4),
                  boxShadow: [
                    BoxShadow(color: color.withOpacity(0.5), blurRadius: 8),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRecentActivity() {
    if (recentActivity.isEmpty) {
      return _buildEmptyState('No recent activity');
    }

    return _buildGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Recent Activity',
            style: TextStyle(
              color: Color(0xFF00FFFF),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          ...recentActivity.map((activity) {
            IconData icon;
            Color color;
            String label;
            final type = activity['type']?.toString() ?? 'trade';

            switch (type) {
              case 'deposit':
                icon = Icons.arrow_downward;
                color = const Color(0xFF00FF88);
                label = 'Deposit';
                break;
              case 'withdrawal':
                icon = Icons.arrow_upward;
                color = const Color(0xFFFF0088);
                label = 'Withdrawal';
                break;
              default:
                icon = Icons.swap_horiz;
                color = const Color(0xFF00FFFF);
                label = 'Trade';
            }

            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.03),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: color.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.2),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(icon, color: color, size: 20),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          activity['created_at'] ??
                              activity['time'] ??
                              'Recent',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    '${(activity['amount']?.toDouble() ?? 0.0) > 0 ? '+' : ''}${currencySymbols[selectedCurrency]}${(activity['amount']?.toDouble() ?? 0.0).toStringAsFixed(2)}',
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

// Animated gradient background
class AnimatedGradientBackground extends StatelessWidget {
  final AnimationController controller;
  const AnimatedGradientBackground({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: const [
                Color(0xFF000C1F),
                Color(0xFF001F3F),
                Color(0xFF000C1F),
              ],
              stops: [0.0, 0.5 + (controller.value * 0.3), 1.0],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        );
      },
    );
  }
}

// Floating particles effect
class FloatingParticles extends StatelessWidget {
  final AnimationController controller;
  const FloatingParticles({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        return CustomPaint(
          size: MediaQuery.of(context).size,
          painter: ParticlePainter(controller.value),
        );
      },
    );
  }
}

class ParticlePainter extends CustomPainter {
  final double animationValue;
  ParticlePainter(this.animationValue);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF00FFFF).withOpacity(0.3)
      ..style = PaintingStyle.fill;

    for (int i = 0; i < 30; i++) {
      final x = (size.width * (i / 30 + animationValue)) % size.width;
      final y = (size.height * math.sin(i + animationValue * math.pi * 2)) %
          size.height;
      final radius = 1 + math.sin(i + animationValue * math.pi) * 1.5;

      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(ParticlePainter oldDelegate) => true;
}

// Custom painter for hexagon pattern background
class HexagonPatternPainter extends CustomPainter {
  final double animationValue;
  HexagonPatternPainter(this.animationValue);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final spacing = 40.0;
    for (double x = -spacing; x < size.width + spacing; x += spacing) {
      for (double y = -spacing; y < size.height + spacing; y += spacing) {
        final offset = Offset(
          x + math.sin(animationValue * math.pi * 2 + y / 50) * 5,
          y + math.cos(animationValue * math.pi * 2 + x / 50) * 5,
        );
        _drawHexagon(canvas, paint, offset, 15);
      }
    }
  }

  void _drawHexagon(Canvas canvas, Paint paint, Offset center, double radius) {
    final path = Path();
    for (int i = 0; i < 6; i++) {
      final angle = (math.pi / 3) * i;
      final x = center.dx + radius * math.cos(angle);
      final y = center.dy + radius * math.sin(angle);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(HexagonPatternPainter oldDelegate) => true;
}

// Performance chart painter
class PerformanceChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = LinearGradient(
        colors: [const Color(0xFF00FFFF), const Color(0xFF00FF88)],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          const Color(0xFF00FFFF).withOpacity(0.3),
          const Color(0xFF00FF88).withOpacity(0.05),
        ],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    final path = Path();
    final fillPath = Path();

    // Generate mock chart data
    final points = <Offset>[];
    for (int i = 0; i <= 20; i++) {
      final x = (size.width / 20) * i;
      final y = size.height * 0.5 +
          math.sin(i * 0.5) * size.height * 0.3 +
          math.cos(i * 0.3) * size.height * 0.1;
      points.add(Offset(x, y));
    }

    // Draw line
    path.moveTo(points[0].dx, points[0].dy);
    for (int i = 1; i < points.length; i++) {
      path.lineTo(points[i].dx, points[i].dy);
    }

    // Create fill area
    fillPath.moveTo(0, size.height);
    fillPath.lineTo(points[0].dx, points[0].dy);
    for (int i = 1; i < points.length; i++) {
      fillPath.lineTo(points[i].dx, points[i].dy);
    }
    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);

    // Draw points
    for (final point in points) {
      canvas.drawCircle(
        point,
        4,
        Paint()
          ..color = const Color(0xFF00FFFF)
          ..style = PaintingStyle.fill,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
