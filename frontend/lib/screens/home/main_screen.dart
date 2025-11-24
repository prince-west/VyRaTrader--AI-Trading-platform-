// lib/screens/home/main_screen.dart
// Main screen with bottom navigation bar + Ad-based AI Signal System
// Production Ready - Complete implementation with interstitial and rewarded ads

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';
import '../../widgets/bottom_nav_bar.dart';
import '../../screens/dashboard/dashboard_screen.dart';
import '../../screens/trading/trade_screen.dart';
import '../../screens/history/history_screen.dart';
import '../../screens/payments/payments_screen.dart';
import '../../screens/profile/profile_screen.dart';
import '../../services/ad_manager.dart';
import '../../services/ai_service.dart';
import '../../widgets/signal_card.dart';
import '../../core/api_client.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();

  // Helper to get state from context
  static _MainScreenState? of(BuildContext context) {
    return context.findAncestorStateOfType<_MainScreenState>();
  }
}

class _MainScreenState extends State<MainScreen> with WidgetsBindingObserver {
  int _currentIndex = 0;
  bool _hasReceivedFreeSignal = false;
  bool _hasWatchedRewardedAd = false;
  bool _isCheckingQuota = false;
  bool _adFlowHandled = false;

  bool _isNavigating = false;

  // Public method to change navigation index
  void navigateToIndex(int index) {
    if (!mounted || index < 0 || index >= _screens.length || _isNavigating) return;
    if (_currentIndex == index) return; // Already on this tab
    
    _isNavigating = true;
    
    // Use SchedulerBinding to ensure we're not in a build phase
    SchedulerBinding.instance.addPostFrameCallback((_) {
      _isNavigating = false;
      if (mounted && index >= 0 && index < _screens.length && _currentIndex != index) {
        setState(() {
          _currentIndex = index;
        });
      }
    });
  }

  final List<Widget> _screens = [
    const TradeScreen(),      // Index 0: Market
    const DashboardScreen(),  // Index 1: Dashboard
    const HistoryScreen(),    // Index 2: History
    const PaymentsScreen(),   // Index 3: Wallet
    const ProfileScreen(),    // Index 4: Profile
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadSessionFlags();
    // Trigger app launch flow (shows ad)
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted) {
        _handleAppLaunch();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Load session flags from local storage
  /// Reset flags on each app launch for fresh session
  Future<void> _loadSessionFlags() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // Clear flags on app launch (fresh session each time)
      await prefs.remove('hasReceivedFreeSignal');
      await prefs.remove('hasWatchedRewardedAd');
      setState(() {
        _hasReceivedFreeSignal = false;
        _hasWatchedRewardedAd = false;
      });
    } catch (e) {
      debugPrint('⚠️ Failed to load session flags: $e');
    }
  }

  /// Save session flags to local storage
  Future<void> _saveSessionFlag(String key, bool value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(key, value);
    } catch (e) {
      debugPrint('⚠️ Failed to save session flag: $e');
    }
  }

  /// Handle app launch - Show ad, then direct to Prince AI
  Future<void> _handleAppLaunch() async {
    if (_adFlowHandled) return;
    
    // Wait a bit for UI to settle
    await Future.delayed(const Duration(milliseconds: 500));
    
    if (!mounted) return;
    
    setState(() => _adFlowHandled = true);

    // Show interstitial ad (original brilliant idea)
    await _showInterstitialAdAndSignal();
  }

  /// Check daily quota before showing ads
  Future<bool> _checkDailyQuota() async {
    if (_isCheckingQuota) return true;
    
    setState(() => _isCheckingQuota = true);
    
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final aiService = AIService(api);
      final status = await aiService.checkDailyStatus();
      
      setState(() => _isCheckingQuota = false);
      return status.available;
    } catch (e) {
      debugPrint('⚠️ Quota check failed: $e - proceeding anyway');
      setState(() => _isCheckingQuota = false);
      return true; // Assume available on error
    }
  }

  /// Show quota exceeded dialog
  void _showQuotaExceededDialog() {
    if (!mounted) return;
    
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF001F3F),
        title: const Text(
          '📉 Daily Limit Reached',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'AI daily signal limit reached. Please come back tomorrow.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK', style: TextStyle(color: Color(0xFF06B6D4))),
          ),
        ],
      ),
    );
  }

  /// Show interstitial ad, then direct to Prince AI (no duplicate AI dialog)
  Future<void> _showInterstitialAdAndSignal() async {
    // Show interstitial ad (original brilliant idea)
    final adShown = await AdManager.instance.showInterstitialAd();
    
    // Wait a moment after ad (or if ad failed)
    await Future.delayed(const Duration(milliseconds: 500));
    
    if (!mounted) return;
    
    // NO market selection dialog - users use Prince AI instead
    // Show snackbar directing to Prince AI
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Row(
          children: [
            Icon(Icons.auto_awesome, color: Color(0xFF00FFFF), size: 20),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                '👑 Tap Prince AI to get your trading signal!',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF001F3F),
        duration: const Duration(seconds: 4),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  /// Show category selection modal
  Future<void> _showCategorySelectionModal({required bool isBonus}) async {
    if (!mounted) return;

    // Fetch market status before showing dialog
    Map<String, MarketStatus>? marketStatuses;
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final aiService = AIService(api);
      final status = await aiService.checkDailyStatus();
      marketStatuses = status.markets;
    } catch (e) {
      debugPrint('⚠️ Failed to fetch market status: $e');
    }

    final category = await showDialog<MarketCategory>(
      context: context,
      barrierDismissible: false,
      builder: (context) => _CategorySelectionDialog(
        isBonus: isBonus,
        marketStatuses: marketStatuses,
      ),
    );

    if (category != null && mounted) {
      await _fetchAndShowSignal(category, isBonus: isBonus);
    }
  }

  /// Fetch AI signal for selected category
  Future<void> _fetchAndShowSignal(
    MarketCategory category, {
    required bool isBonus,
  }) async {
    if (!mounted) return;

    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: CircularProgressIndicator(
          color: Color(0xFF06B6D4),
        ),
      ),
    );

    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final aiService = AIService(api);
      final signalResponse = await aiService.getSignal(category);

      if (!mounted) return;
      Navigator.of(context).pop(); // Close loading

      if (signalResponse.categoryUnavailable) {
        // Show suggestion dialog with alternatives
        _showCategoryUnavailableDialog(category, signalResponse);
      } else if (signalResponse.success && signalResponse.signal != null) {
        // Show signal successfully
        setState(() => _hasReceivedFreeSignal = true);
        
        await showSignalModal(context, signalResponse, isBonus: isBonus);
      } else {
        // Error case
        _showErrorDialog(signalResponse.message ?? 'Failed to fetch signal');
      }
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context).pop(); // Close loading
      _showErrorDialog('Network connection failed. Please check your internet or backend.');
    }
  }

  /// Show dialog when category is unavailable with alternative suggestions
  void _showCategoryUnavailableDialog(
    MarketCategory unavailableCategory,
    AISignalResponse response,
  ) {
    if (!mounted) return;

    final alternatives = AIService.getAlternativeCategories(unavailableCategory);
    
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF001F3F),
        title: const Text(
          '⚠️ Category Unavailable',
          style: TextStyle(color: Colors.orange, fontSize: 18),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              response.message ?? 'No optimal setup found in ${unavailableCategory.displayName} now.',
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 16),
            const Text(
              '💡 Suggestion: Try one of these categories for better opportunities today:',
              style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ...alternatives.map((cat) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(cat),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF06B6D4),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 40),
                ),
                child: Text(cat.displayName),
              ),
            )),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
          ),
        ],
      ),
    ).then((selectedCategory) {
      if (selectedCategory != null && mounted) {
        _fetchAndShowSignal(selectedCategory, isBonus: false);
      }
    });
  }

  /// Show error dialog
  void _showErrorDialog(String message) {
    if (!mounted) return;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF001F3F),
        title: const Text(
          '🚫 Error',
          style: TextStyle(color: Colors.red),
        ),
        content: Text(
          message,
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK', style: TextStyle(color: Color(0xFF06B6D4))),
          ),
        ],
      ),
    );
  }

  /// Handle back button press - offer rewarded ad
  Future<bool> _handleBackButton() async {
    // Check if user is premium (skip ads for premium)
    bool isPremium = false;
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final userResponse = await api.get('/users/me', params: {}, queryParams: {});
      isPremium = userResponse['is_premium'] == true;
    } catch (e) {
      debugPrint('⚠️ Failed to check premium status: $e');
    }
    
    // Premium users can exit without watching ads
    if (isPremium) {
      return true;
    }
    
    // If user already watched rewarded ad this session, allow normal exit
    if (_hasWatchedRewardedAd) {
      return true;
    }

    // Offer rewarded ad
    final watchAd = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF001F3F),
        title: const Text(
          '🎁 Bonus Signal',
          style: TextStyle(color: Colors.amber, fontSize: 18),
        ),
        content: const Text(
          'Watch one ad to unlock an extra signal before leaving?',
          style: TextStyle(color: Colors.white70, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Exit', style: TextStyle(color: Colors.grey)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF06B6D4),
              foregroundColor: Colors.white,
            ),
            child: const Text('Watch Ad'),
          ),
        ],
      ),
    );

      if (watchAd == true && mounted) {
      // Show rewarded ad
      final adShown = await AdManager.instance.showRewardedAd(
        onRewarded: () {
          _hasWatchedRewardedAd = true;
          
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('🎯 Bonus signal unlocked!'),
                backgroundColor: Colors.green,
                duration: Duration(seconds: 2),
              ),
            );
            
            // Show category selection for bonus signal
            Future.delayed(const Duration(milliseconds: 500), () {
              if (mounted) {
                _showCategorySelectionModal(isBonus: true);
              }
            });
          }
        },
        onFailed: () {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Ad failed to load. Exiting...'),
                backgroundColor: Colors.orange,
              ),
            );
          }
        },
      );
      
      // If ad didn't show, allow exit
      if (!adShown) {
        Future.delayed(const Duration(milliseconds: 500), () {
          if (mounted && Navigator.canPop(context)) {
            Navigator.of(context).pop();
          }
        });
      }
      
      // Don't exit immediately - wait for ad result
      return false;
    }

    return watchAd == false; // Exit if user chose not to watch
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (!didPop) {
          final shouldPop = await _handleBackButton();
          if (shouldPop && context.mounted) {
            Navigator.of(context).pop();
          }
        }
      },
      child: Scaffold(
        body: _screens[_currentIndex],
        bottomNavigationBar: BottomNavBar(
          currentIndex: _currentIndex,
          onTap: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
        ),
      ),
    );
  }
}

/// Category selection dialog widget
class _CategorySelectionDialog extends StatelessWidget {
  final bool isBonus;
  final Map<String, MarketStatus>? marketStatuses;

  const _CategorySelectionDialog({
    required this.isBonus,
    this.marketStatuses,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF001F3F),
      title: Text(
        isBonus ? '🎯 Bonus Signal - Choose Category' : '🔮 Select Market Category',
        style: const TextStyle(color: Colors.white, fontSize: 18),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            isBonus
                ? 'Select which market you want your bonus signal for:'
                : 'Select which market you want today\'s signal for:',
            style: const TextStyle(color: Colors.white70, fontSize: 14),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          ...MarketCategory.values.map((category) {
            final status = marketStatuses?[category.value];
            final isAvailable = status?.available ?? true;
            final remaining = status?.remaining ?? 2;
            
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: ElevatedButton(
                onPressed: isAvailable
                    ? () => Navigator.of(context).pop(category)
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: isAvailable
                      ? const Color(0xFF06B6D4)
                      : Colors.grey.withOpacity(0.3),
                  foregroundColor: Colors.white,
                  disabledBackgroundColor: Colors.grey.withOpacity(0.2),
                  disabledForegroundColor: Colors.grey,
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      category.displayName,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (status != null)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: isAvailable
                                  ? Colors.green.withOpacity(0.2)
                                  : Colors.red.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isAvailable ? Colors.green : Colors.red,
                                width: 1,
                              ),
                            ),
                            child: Text(
                              remaining > 0 ? '$remaining left' : 'Limit reached',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: isAvailable ? Colors.green : Colors.red,
                              ),
                            ),
                          ),
                          if (status.maxLimit > status.baseLimit && isAvailable)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'Up to ${status.maxLimit} with quality',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.orange.shade300,
                                  fontStyle: FontStyle.italic,
                                ),
                              ),
                            ),
                        ],
                      ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
