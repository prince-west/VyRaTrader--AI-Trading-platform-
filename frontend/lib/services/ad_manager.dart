// lib/services/ad_manager.dart
// Google Mobile Ads Manager - Production Ready
// Handles interstitial and rewarded ads with proper initialization

import 'package:flutter/foundation.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

class AdManager {
  static AdManager? _instance;
  static AdManager get instance {
    _instance ??= AdManager._();
    return _instance!;
  }

  AdManager._();

  bool _isInitialized = false;
  InterstitialAd? _interstitialAd;
  RewardedAd? _rewardedAd;
  bool _isInterstitialReady = false;
  bool _isRewardedReady = false;

  // Google Official Test Ad Unit IDs
  // These work immediately without any configuration
  static String get _testInterstitialAdUnitId {
    if (kIsWeb) {
      return 'ca-app-pub-3940256099942544/1033173712'; // Web Test Interstitial
    }
    // For mobile, use Android as default (can be detected at runtime if needed)
    return 'ca-app-pub-3940256099942544/1033173712'; // Android Test Interstitial
  }

  static String get _testRewardedAdUnitId {
    if (kIsWeb) {
      return 'ca-app-pub-3940256099942544/5224354917'; // Web Test Rewarded
    }
    // For mobile, use Android as default (can be detected at runtime if needed)
    return 'ca-app-pub-3940256099942544/5224354917'; // Android Test Rewarded
  }

  // Production Ad Unit IDs (update these when ready)
  static String get _productionInterstitialAdUnitId {
    if (kIsWeb) {
      return ''; // Replace with your Web production ID
    }
    return ''; // Replace with your production ID
  }

  static String get _productionRewardedAdUnitId {
    if (kIsWeb) {
      return ''; // Replace with your Web production ID
    }
    return ''; // Replace with your production ID
  }

  // Use test IDs for now - switch to production IDs when ready
  static String get interstitialAdUnitId => _testInterstitialAdUnitId;
  static String get rewardedAdUnitId => _testRewardedAdUnitId;

  /// Initialize Google Mobile Ads SDK
  Future<void> initialize() async {
    if (_isInitialized) return;

    // Google Mobile Ads doesn't support web platform
    if (kIsWeb) {
      debugPrint('⚠️ Google Mobile Ads not supported on web platform - skipping initialization');
      _isInitialized = true; // Mark as initialized to prevent retries
      return;
    }

    try {
      await MobileAds.instance.initialize();
      _isInitialized = true;
      debugPrint('✅ Google Mobile Ads initialized');
      
      // Preload ads immediately
      loadInterstitialAd();
      loadRewardedAd();
    } catch (e) {
      debugPrint('❌ Failed to initialize Mobile Ads: $e');
      _isInitialized = true; // Mark as initialized to prevent retries
      // Continue anyway - ads will fail gracefully
    }
  }

  /// Load interstitial ad
  void loadInterstitialAd() {
    if (!_isInitialized) return;
    if (kIsWeb) return; // Skip on web

    InterstitialAd.load(
      adUnitId: interstitialAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) {
          _interstitialAd = ad;
          _isInterstitialReady = true;
          debugPrint('✅ Interstitial ad loaded');

          // Set full screen content callback
          ad.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              _interstitialAd?.dispose();
              _interstitialAd = null;
              _isInterstitialReady = false;
              // Reload for next time
              loadInterstitialAd();
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              debugPrint('❌ Interstitial ad failed to show: $error');
              ad.dispose();
              _interstitialAd = null;
              _isInterstitialReady = false;
              loadInterstitialAd();
            },
          );
        },
        onAdFailedToLoad: (error) {
          debugPrint('❌ Failed to load interstitial ad: $error');
          _isInterstitialReady = false;
          // Retry after delay
          Future.delayed(const Duration(seconds: 5), () {
            loadInterstitialAd();
          });
        },
      ),
    );
  }

  /// Load rewarded ad
  void loadRewardedAd() {
    if (!_isInitialized) return;
    if (kIsWeb) return; // Skip on web

    RewardedAd.load(
      adUnitId: rewardedAdUnitId,
      request: const AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: (ad) {
          _rewardedAd = ad;
          _isRewardedReady = true;
          debugPrint('✅ Rewarded ad loaded');

          // Set full screen content callback
          ad.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              _rewardedAd?.dispose();
              _rewardedAd = null;
              _isRewardedReady = false;
              // Reload for next time
              loadRewardedAd();
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              debugPrint('❌ Rewarded ad failed to show: $error');
              ad.dispose();
              _rewardedAd = null;
              _isRewardedReady = false;
              loadRewardedAd();
            },
          );
        },
        onAdFailedToLoad: (error) {
          debugPrint('❌ Failed to load rewarded ad: $error');
          _isRewardedReady = false;
          // Retry after delay
          Future.delayed(const Duration(seconds: 5), () {
            loadRewardedAd();
          });
        },
      ),
    );
  }

  /// Show interstitial ad
  /// Returns true if ad was shown, false if not available
  Future<bool> showInterstitialAd() async {
    // No ads on web platform
    if (kIsWeb) {
      debugPrint('⚠️ Interstitial ads not supported on web platform');
      return false;
    }
    
    if (!_isInterstitialReady || _interstitialAd == null) {
      debugPrint('⚠️ Interstitial ad not ready');
      return false;
    }

    try {
      await _interstitialAd!.show();
      return true;
    } catch (e) {
      debugPrint('❌ Error showing interstitial ad: $e');
      return false;
    }
  }

  /// Show rewarded ad
  /// Calls onRewarded callback when user watches ad successfully
  /// Returns true if ad was shown, false if not available
  Future<bool> showRewardedAd({
    required VoidCallback onRewarded,
    VoidCallback? onFailed,
  }) async {
    // No ads on web platform
    if (kIsWeb) {
      debugPrint('⚠️ Rewarded ads not supported on web platform');
      onFailed?.call();
      return false;
    }
    
    if (!_isRewardedReady || _rewardedAd == null) {
      debugPrint('⚠️ Rewarded ad not ready');
      onFailed?.call();
      return false;
    }

    try {
      await _rewardedAd!.show(
        onUserEarnedReward: (ad, reward) {
          debugPrint('✅ User earned reward: ${reward.amount} ${reward.type}');
          onRewarded();
        },
      );
      return true;
    } catch (e) {
      debugPrint('❌ Error showing rewarded ad: $e');
      onFailed?.call();
      return false;
    }
  }

  /// Check if ads are ready
  bool get isInterstitialReady => _isInterstitialReady;
  bool get isRewardedReady => _isRewardedReady;

  /// Dispose all ads
  void dispose() {
    _interstitialAd?.dispose();
    _rewardedAd?.dispose();
    _interstitialAd = null;
    _rewardedAd = null;
    _isInterstitialReady = false;
    _isRewardedReady = false;
  }
}

