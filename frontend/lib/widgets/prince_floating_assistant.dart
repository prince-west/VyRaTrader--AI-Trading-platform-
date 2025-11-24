// lib/widgets/prince_floating_assistant.dart
// COMPLETE VERSION - All UI features + Backend connectivity

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'dart:ui';
import '../core/api_client.dart';
import '/core/constants.dart';
import '../services/ai_service.dart';
import '../services/ad_manager.dart';
import 'dart:async';

/// Prince Floating Bubble - Sits above bottom navigation bar
class PrinceFloatingAssistant extends StatefulWidget {
  final Widget child;
  final String? userId;
  final String? initialSymbol; // NEW: optional initial symbol context
  final bool autoOpenOnLaunch; // NEW: auto-open chat on launch

  const PrinceFloatingAssistant({
    super.key,
    required this.child,
    this.userId,
    this.initialSymbol, // NEW: accept initial symbol
    this.autoOpenOnLaunch = false, // NEW: auto-open option
  });

  @override
  _PrinceFloatingAssistantState createState() =>
      _PrinceFloatingAssistantState();
}

class _PrinceFloatingAssistantState extends State<PrinceFloatingAssistant>
    with SingleTickerProviderStateMixin {
  bool _isChatOpen = false;
  bool _isExpanded = false;
  late AnimationController _pulseController;
  
  // Draggable bubble position
  double _bubbleBottom = 200.0;
  double _bubbleRight = 20.0;
  bool _isDragging = false;
  Offset? _dragInitialOffset; // Offset from touch point to bubble center

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    
    // Auto-open Prince AI on app launch if requested
    if (widget.autoOpenOnLaunch) {
      Future.delayed(const Duration(milliseconds: 800), () {
        if (mounted) {
          _toggleChat();
        }
      });
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  void _toggleChat() {
    // Don't toggle if user was dragging
    if (_isDragging) {
      return;
    }
    setState(() {
      _isChatOpen = !_isChatOpen;
      if (!_isChatOpen) {
        _isExpanded = false;
      }
    });
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Stack(
          children: [
            // Base child widget - fills the screen
            Positioned.fill(
              child: widget.child,
            ),

            // Overlay backdrop
            if (_isChatOpen)
              Positioned.fill(
                child: GestureDetector(
                  onTap: _toggleChat,
                  child: Container(
                    color: Colors.black.withOpacity(0.75),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                      child: Container(color: Colors.transparent),
                    ),
                  ),
                ),
              ),

            // Chat window
            if (_isChatOpen)
              Positioned(
                // When expanded, position from top to ensure header is visible above browser bar
                // When not expanded, position from bottom
                bottom: _isExpanded ? null : 80.0, // Position just above nav bar (70px) + small gap
                top: _isExpanded ? MediaQuery.of(context).padding.top + 16 : null,
                right: 16.0,
                left: _isExpanded ? 16.0 : null,
                child: Material(
                  elevation: 8,
                  borderRadius: BorderRadius.circular(20),
                  color: Colors.transparent,
                  shadowColor: const Color(0xFF00FFFF).withOpacity(0.3),
                  child: GestureDetector(
                    onTap: () {},
                    child: _PrinceChatWindow(
                      onClose: _toggleChat,
                      onToggleExpand: _toggleExpanded,
                      isExpanded: _isExpanded,
                      userId: widget.userId,
                      initialSymbol: widget.initialSymbol, // NEW: pass symbol
                    ),
                  ),
                ),
              ),

            // Floating bubble - draggable and positioned to avoid covering send button
            Positioned(
              bottom: _bubbleBottom,
              right: _bubbleRight,
              child: _FloatingBubble(
                isOpen: _isChatOpen,
                onTap: _toggleChat,
                onPanStart: (details) {
                  _isDragging = false;
                  // Store the initial touch position relative to bubble center
                  final RenderBox? stackBox = context.findRenderObject() as RenderBox?;
                  if (stackBox != null) {
                    final stackLocal = stackBox.globalToLocal(details.globalPosition);
                    final bubbleSize = 70.0;
                    // Calculate where the bubble center currently is
                    final currentBubbleCenterX = stackBox.size.width - _bubbleRight - (bubbleSize / 2);
                    final currentBubbleCenterY = stackBox.size.height - _bubbleBottom - (bubbleSize / 2);
                    // Calculate offset from touch point to bubble center
                    _dragInitialOffset = Offset(
                      stackLocal.dx - currentBubbleCenterX,
                      stackLocal.dy - currentBubbleCenterY,
                    );
                  }
                },
                onPanUpdate: (details) {
                  // Check if user is actually dragging (not just a tap)
                  if (details.delta.distance > 3.0) {
                    _isDragging = true;
                  }
                  
                  // Update bubble position to follow finger/pointer precisely
                  if (_isDragging) {
                    setState(() {
                      final screenHeight = constraints.maxHeight;
                      final screenWidth = constraints.maxWidth;
                      final bubbleSize = 70.0;
                      
                      final RenderBox? stackBox = context.findRenderObject() as RenderBox?;
                      if (stackBox != null && _dragInitialOffset != null) {
                        // Get current finger position relative to stack
                        final stackLocal = stackBox.globalToLocal(details.globalPosition);
                        
                        // Calculate where bubble center should be (maintaining touch offset)
                        final bubbleCenterX = stackLocal.dx - _dragInitialOffset!.dx;
                        final bubbleCenterY = stackLocal.dy - _dragInitialOffset!.dy;
                        
                        // Convert to bottom/right coordinates for Positioned widget
                        final newRight = screenWidth - bubbleCenterX - (bubbleSize / 2);
                        final newBottom = screenHeight - bubbleCenterY - (bubbleSize / 2);
                        
                        // Constrain to screen bounds
                        _bubbleRight = newRight.clamp(0.0, screenWidth - bubbleSize);
                        _bubbleBottom = newBottom.clamp(0.0, screenHeight - bubbleSize);
                      } else {
                        // Fallback: use delta movement if render box unavailable
                        final newRight = _bubbleRight - details.delta.dx;
                        final newBottom = _bubbleBottom - details.delta.dy;
                        
                        _bubbleRight = newRight.clamp(0.0, screenWidth - bubbleSize);
                        _bubbleBottom = newBottom.clamp(0.0, screenHeight - bubbleSize);
                      }
                    });
                  }
                },
                onPanEnd: (_) {
                  _isDragging = false;
                  _dragInitialOffset = null;
                },
                pulseController: _pulseController,
              ),
            ),
          ],
        );
      },
    );
  }
}

// ============================================================================
// FLOATING BUBBLE
// ============================================================================

class _FloatingBubble extends StatelessWidget {
  final bool isOpen;
  final VoidCallback onTap;
  final Function(DragStartDetails)? onPanStart;
  final Function(DragUpdateDetails) onPanUpdate;
  final Function(DragEndDetails)? onPanEnd;
  final AnimationController pulseController;

  const _FloatingBubble({
    required this.isOpen,
    required this.onTap,
    this.onPanStart,
    required this.onPanUpdate,
    this.onPanEnd,
    required this.pulseController,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      onPanStart: onPanStart,
      onPanUpdate: onPanUpdate,
      onPanEnd: onPanEnd,
      child: AnimatedBuilder(
        animation: pulseController,
        builder: (context, child) {
          return Container(
            width: 70,
            height: 70,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF00FFFF), Color(0xFF00D4FF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF000C1F).withOpacity(0.3),
                width: 3,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00FFFF).withOpacity(
                    isOpen ? 0.6 : 0.5 + pulseController.value * 0.2,
                  ),
                  blurRadius: isOpen ? 40 : 30 + pulseController.value * 20,
                  spreadRadius: isOpen ? 8 : 6 + pulseController.value * 4,
                ),
                BoxShadow(
                  color: const Color(0xFF00D4FF).withOpacity(0.3),
                  blurRadius: 60,
                  spreadRadius: 10,
                ),
              ],
            ),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Icon(
                isOpen ? Icons.close : Icons.auto_awesome,
                key: ValueKey(isOpen),
                color: const Color(0xFF000C1F),
                size: 32,
              ),
            ),
          );
        },
      ),
    );
  }
}

// ============================================================================
// CHAT WINDOW - FULL FEATURED WITH BACKEND CONNECTIVITY
// ============================================================================

class _PrinceChatWindow extends StatefulWidget {
  final VoidCallback onClose;
  final VoidCallback onToggleExpand;
  final bool isExpanded;
  final String? userId;
  final String? initialSymbol; // NEW: initial symbol

  const _PrinceChatWindow({
    required this.onClose,
    required this.onToggleExpand,
    required this.isExpanded,
    this.userId,
    this.initialSymbol, // NEW
  });

  @override
  _PrinceChatWindowState createState() => _PrinceChatWindowState();
}

class _PrinceChatWindowState extends State<_PrinceChatWindow>
    with SingleTickerProviderStateMixin {
  final _ctrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _quickActionsScrollCtrl = ScrollController();
  List<Map<String, dynamic>> messages = [];
  bool typing = false;
  late AnimationController _glowController;
  late ApiClient _api;
  String? _selectedSymbol; // NEW: track selected symbol
  MarketCategory? _pendingSignalCategory; // Track if waiting for ad confirmation

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    // Initialize API client from Provider
    _api = Provider.of<ApiClient>(context, listen: false);

    // NEW: Initialize symbol from widget
    _selectedSymbol = widget.initialSymbol;

    // Enhanced greeting message
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted) {
        setState(() {
          messages.add({
            'role': 'prince',
            'text': 'Hi! I\'m Prince 👑, your AI trading genius.\n\n'
                'Welcome to VyRaTrader! I can help you get trading signals and market analysis.\n\n'
                '**To get started, simply ask me:**\n'
                '• "Give me a signal for crypto"\n'
                '• "I want a signal for forex"\n\n'
                'Or use the quick action buttons below to get market analysis!\n\n'
                'I also provide:\n'
                '• Advanced trading strategies (8 ensemble strategies)\n'
                '• Multi-currency trading (${kSupportedCurrencies.length} currencies)\n'
                '• Real-time risk analysis & portfolio optimization\n'
                '• Payment methods & fee structures\n'
                '• Market predictions & trend analysis\n\n'
                '${_selectedSymbol != null ? "Currently analyzing: $_selectedSymbol\n\n" : ""}'
                'What would you like to know? 🚀',
            'timestamp': DateTime.now(),
          });
        });
        _scrollToBottom();
      }
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _scrollCtrl.dispose();
    _quickActionsScrollCtrl.dispose();
    _glowController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollCtrl.hasClients) {
      Future.delayed(const Duration(milliseconds: 100), () {
        if (_scrollCtrl.hasClients) {
          _scrollCtrl.animateTo(
            _scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  String _getCurrentScreen() {
    return ModalRoute.of(context)?.settings.name ?? 'unknown';
  }

  // NEW: Enhanced send function with backend connectivity
  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || typing) return;

    setState(() {
      messages.add({'role': 'user', 'text': text, 'timestamp': DateTime.now()});
      typing = true;
    });
    _ctrl.clear();
    _scrollToBottom();

    try {
      // Check if user is confirming ad watch or requesting signal
      final isAdConfirmation = (_pendingSignalCategory != null) && 
          (text.toLowerCase() == 'yes' || 
           text.toLowerCase().contains('watch') || 
           text.toLowerCase().contains('ad'));
      
      if (isAdConfirmation) {
        // User agreed to watch ad - show ad and grant signal
        await _handleAdWatchForSignal();
        return;
      }

      // Check if user is requesting a signal
      final isSignalRequest = text.toLowerCase().contains('signal') ||
          text.toLowerCase().contains('give me') ||
          text.toLowerCase().contains('crypto') ||
          text.toLowerCase().contains('forex');

      if (isSignalRequest) {
        // Handle signal request - check status and handle ads if needed
        await _handleSignalRequest(text);
        return;
      }

      // Regular chat message
      final body = {
        "message": text,
        "symbol": _selectedSymbol, // Include symbol context
        "userId": widget.userId ?? 'guest',
        "context": {
          'screen': _getCurrentScreen(),
          'timestamp': DateTime.now().toIso8601String(),
          'request_detailed_response': true,
          'supported_currencies': kSupportedCurrencies,
        },
      };

      // POST to backend AI endpoint (matches your backend route)
      final res = await _api.post('/ai/chat', body);

      await Future.delayed(const Duration(milliseconds: 600));

      // NEW: Handle multiple response formats from backend
      String reply = "";
      if (res.containsKey('reply')) {
        reply = res['reply'].toString();
      } else if (res.containsKey('response')) {
        reply = res['response'].toString();
      } else {
        reply = res.toString();
      }

      setState(() {
        messages.add({
          'role': 'prince',
          'text': reply.isEmpty
              ? 'I apologize, I couldn\'t process that. Please try again.'
              : reply,
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() {
        messages.add({
          'role': 'prince',
          'text': "I'm currently offline, but I can still help with general trading questions! "
              "Try asking about trading strategies, risk management, or market analysis. "
              "I'll be back online soon! 🤖",
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _scrollToBottom();
    }
  }

  // Handle signal requests with ad/premium checking
  Future<void> _handleSignalRequest(String text) async {
    // Extract market category from text
    MarketCategory? category;
    if (text.toLowerCase().contains('crypto')) {
      category = MarketCategory.crypto;
    } else if (text.toLowerCase().contains('forex')) {
      category = MarketCategory.forex;
    } else {
      // Default to crypto if unclear
      category = MarketCategory.crypto;
    }

    // Check user status and quota
    try {
      final aiService = AIService(_api);
      final status = await aiService.checkDailyStatus();
      
      // Check if user is premium
      bool isPremium = false;
      try {
        final userResponse = await _api.get('/users/me', params: {}, queryParams: {});
        isPremium = userResponse['is_premium'] == true;
      } catch (e) {
        debugPrint('⚠️ Failed to check premium status: $e');
      }

      final marketStatus = status.markets[category.value];
      
      if (isPremium) {
        // Premium user - get signal directly
        setState(() {
          messages.add({
            'role': 'prince',
            'text': '🟢 Premium user detected! Getting your signal...',
            'timestamp': DateTime.now(),
          });
          typing = false;
        });
        _scrollToBottom();
        await _fetchSignal(category);
      } else if (marketStatus?.available == true && (marketStatus?.remaining ?? 0) > 0) {
        // Has quota available - get signal directly
        setState(() {
          messages.add({
            'role': 'prince',
            'text': 'Getting your ${category?.displayName ?? 'market'} signal...',
            'timestamp': DateTime.now(),
          });
          typing = false;
        });
        _scrollToBottom();
        await _fetchSignal(category);
      } else {
        // Quota exceeded - suggest watching ad
        _pendingSignalCategory = category; // Store category for ad confirmation
        setState(() {
          messages.add({
            'role': 'prince',
            'text': '📺 You\'ve used your daily signal quota for ${category?.displayName ?? 'this market'}.\n\n'
                'Watch a short ad to get an extra signal, or upgrade to Premium for unlimited signals!\n\n'
                'Would you like to watch an ad? (Type "yes" or "watch ad")',
            'timestamp': DateTime.now(),
          });
          typing = false;
        });
        _scrollToBottom();
      }
    } catch (e) {
      setState(() {
        messages.add({
          'role': 'prince',
          'text': 'I had trouble checking your quota. Let me try getting the signal directly...',
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _scrollToBottom();
      if (category != null) {
        await _fetchSignal(category);
      }
    }
  }

  // Handle ad watch for signal
  Future<void> _handleAdWatchForSignal() async {
    if (_pendingSignalCategory == null) {
      setState(() {
        messages.add({
          'role': 'prince',
          'text': 'Sorry, I lost track of which signal you wanted. Please ask again.',
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _pendingSignalCategory = null;
      return;
    }

    final category = _pendingSignalCategory!;
    _pendingSignalCategory = null;

    setState(() {
      messages.add({
        'role': 'prince',
        'text': 'Showing ad... Please watch to unlock your signal! 🎬',
        'timestamp': DateTime.now(),
      });
      typing = false;
    });
    _scrollToBottom();

      // Show rewarded ad
    final adShown = await AdManager.instance.showRewardedAd(
      onRewarded: () {
        // Ad watched - grant signal with ad_watched flag
        if (mounted) {
          setState(() {
            messages.add({
              'role': 'prince',
              'text': '🎯 Ad watched! Getting your ${category.displayName} signal...',
              'timestamp': DateTime.now(),
            });
            typing = true;
          });
          _scrollToBottom();
          _fetchSignal(category, adWatched: true);
        }
      },
      onFailed: () {
        if (mounted) {
          setState(() {
            messages.add({
              'role': 'prince',
              'text': 'Ad failed to load. You can still upgrade to Premium for unlimited signals!',
              'timestamp': DateTime.now(),
            });
            typing = false;
          });
          _scrollToBottom();
        }
      },
    );

    if (!adShown && mounted) {
      setState(() {
        messages.add({
          'role': 'prince',
          'text': 'Ad not available. You can upgrade to Premium for unlimited signals!',
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _scrollToBottom();
    }
  }

  // Fetch signal from backend
  Future<void> _fetchSignal(MarketCategory category, {bool adWatched = false}) async {
    try {
      setState(() {
        typing = true;
      });
      _scrollToBottom();

      final aiService = AIService(_api);
      final signalResponse = await aiService.getSignal(category, adWatched: adWatched);

      if (!mounted) return;

      if (signalResponse.success && signalResponse.signal != null) {
        setState(() {
          messages.add({
            'role': 'prince',
            'text': signalResponse.signal!,
            'timestamp': DateTime.now(),
          });
          typing = false;
        });
      } else {
        setState(() {
          messages.add({
            'role': 'prince',
            'text': signalResponse.message ?? 'Unable to get signal at this time. Please try again later.',
            'timestamp': DateTime.now(),
          });
          typing = false;
        });
      }
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        messages.add({
          'role': 'prince',
          'text': 'Sorry, I couldn\'t fetch the signal. Please try again.',
          'timestamp': DateTime.now(),
        });
        typing = false;
      });
      _scrollToBottom();
    }
  }

  void _sendQuickAction(String message) {
    _ctrl.text = message;
  }

  Widget _buildQuickActions() {
    final actions = [
      // Market Signal Quick Actions - Ready to use phrases
      {
        'icon': Icons.currency_bitcoin,
        'label': 'Crypto Signal',
        'message': 'Give me crypto signal',
      },
      {
        'icon': Icons.attach_money,
        'label': 'Forex Signal',
        'message': 'Give me forex signal',
      },
      {
        'icon': Icons.analytics_outlined,
        'label': 'Market Analysis',
        'message': 'Give me a detailed market analysis',
      },
      {
        'icon': Icons.account_balance_wallet,
        'label': 'Portfolio Review',
        'message': 'Review my portfolio performance',
      },
      {
        'icon': Icons.shield,
        'label': 'Risk Assessment',
        'message': 'Explain my current risk level',
      },
        {
          'icon': Icons.auto_awesome,
          'label': 'Strategy Explain',
          'message':
              'Explain the ${TradingStrategies.userVisible.length} trading strategies',
        },
      {
        'icon': Icons.payment,
        'label': 'Payment Options',
        'message': 'List the available payment methods',
      },
      {
        'icon': Icons.show_chart,
        'label': 'Trend Prediction',
        'message': 'Predict upcoming market trends',
      },
      // NEW: Symbol-specific action if symbol is set
      if (_selectedSymbol != null)
        {
          'icon': Icons.analytics,
          'label': 'Analyze $_selectedSymbol',
          'message': 'Analyze $_selectedSymbol with all strategies',
        },
      {
        'icon': Icons.lightbulb,
        'label': 'Tips',
        'message': 'Give me advanced trading tips',
      },
      {
        'icon': Icons.question_answer,
        'label': 'Help',
        'message': 'How can you assist me?',
      },
      {
        'icon': Icons.psychology,
        'label': 'Strategies',
        'message': 'Explain the trading strategies you support',
      },
    ];

    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF000C1F).withOpacity(0.5),
        border: const Border(
          top: BorderSide(color: Color(0xFF00FFFF), width: 0.5),
        ),
      ),
      child: Scrollbar(
        controller: _quickActionsScrollCtrl,
        thumbVisibility: true,
        thickness: 4,
        radius: const Radius.circular(2),
        child: ListView.builder(
          controller: _quickActionsScrollCtrl,
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          itemCount: actions.length,
          itemBuilder: (context, index) {
            final action = actions[index];
            return GestureDetector(
              onTap: () => _sendQuickAction(action['message'] as String),
              child: Container(
                margin: const EdgeInsets.only(right: 8),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF00FFFF).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: const Color(0xFF00FFFF).withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      action['icon'] as IconData,
                      size: 16,
                      color: const Color(0xFF00FFFF),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      action['label'] as String,
                      style: const TextStyle(
                        color: Color(0xFF00FFFF),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildBubble(Map<String, dynamic> m) {
    final isUser = m['role'] == 'user';
    final isSystem = m['role'] == 'system';
    final isPrince = m['role'] == 'prince';
    final timestamp = m['timestamp'] as DateTime?;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        constraints: BoxConstraints(
          maxWidth: widget.isExpanded
              ? MediaQuery.of(context).size.width * 0.85
              : 280,
        ),
        decoration: BoxDecoration(
          gradient: isUser
              ? const LinearGradient(
                  colors: [Color(0xFF00FFFF), Color(0xFF00D4FF)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSystem
              ? const Color(0xFF991B1B).withOpacity(0.2)
              : isPrince
                  ? const Color(0xFF001F3F)
                  : null,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isUser
                ? const Color(0xFF00FFFF).withOpacity(0.5)
                : isSystem
                    ? const Color(0xFF991B1B).withOpacity(0.5)
                    : const Color(0xFF00FFFF).withOpacity(0.2),
            width: 1,
          ),
          boxShadow: isUser || isPrince
              ? [
                  BoxShadow(
                    color: const Color(0xFF00FFFF).withOpacity(0.3),
                    blurRadius: 8,
                    spreadRadius: 1,
                  ),
                ]
              : [],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            isPrince
                ? AnimatedBuilder(
                    animation: _glowController,
                    builder: (context, child) {
                      return ShaderMask(
                        shaderCallback: (bounds) {
                          return LinearGradient(
                            colors: [
                              const Color(0xFF00FFFF).withOpacity(
                                  0.6 + _glowController.value * 0.4),
                              const Color(0xFF00FFFF),
                              const Color(0xFF00D4FF),
                            ],
                            stops: const [0.0, 0.5, 1.0],
                          ).createShader(bounds);
                        },
                        child: Text(
                          m['text'] ?? '',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13.5,
                            height: 1.6,
                          ),
                        ),
                      );
                    },
                  )
                : Text(
                    m['text'] ?? '',
                    style: TextStyle(
                      color: isSystem
                          ? const Color(0xFFEF4444)
                          : isUser
                              ? const Color(0xFF000C1F)
                              : Colors.white,
                      fontSize: 13.5,
                      height: 1.6,
                      fontWeight: isUser ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
            if (timestamp != null) ...[
              const SizedBox(height: 6),
              Text(
                DateFormat('HH:mm').format(timestamp),
                style: TextStyle(
                  fontSize: 10,
                  color: isUser
                      ? const Color(0xFF000C1F).withOpacity(0.6)
                      : Colors.white.withOpacity(0.4),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFF001F3F),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: const Color(0xFF00FFFF).withOpacity(0.2),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ...List.generate(3, (i) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: AnimatedBuilder(
                      animation: _glowController,
                      builder: (context, child) {
                        final delay = i * 0.15;
                        final value = (_glowController.value + delay) % 1.0;
                        return Transform.translate(
                          offset: Offset(
                            0,
                            -4 * (value > 0.5 ? 1 - value : value),
                          ),
                          child: Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: Color(0xFF00FFFF),
                              shape: BoxShape.circle,
                            ),
                          ),
                        );
                      },
                    ),
                  );
                }),
                const SizedBox(width: 8),
                Text(
                  'Prince is analyzing...',
                  style: TextStyle(
                    color: const Color(0xFF00FFFF).withOpacity(0.8),
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _glowController,
              builder: (context, child) {
                return Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Color.lerp(
                          const Color(0xFF00FFFF).withOpacity(0.2),
                          const Color(0xFF00FFFF).withOpacity(0.5),
                          _glowController.value,
                        )!,
                        Color.lerp(
                          const Color(0xFF00D4FF).withOpacity(0.2),
                          const Color(0xFF00D4FF).withOpacity(0.5),
                          _glowController.value,
                        )!,
                      ],
                    ),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Color.lerp(
                          const Color(0xFF00FFFF).withOpacity(0.3),
                          const Color(0xFF00FFFF).withOpacity(0.5),
                          _glowController.value,
                        )!,
                        blurRadius: 40,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.auto_awesome,
                    size: 48,
                    color: Color(0xFF00FFFF),
                  ),
                );
              },
            ),
            const SizedBox(height: 20),
            const Text(
              'Prince AI Trading Genius',
              style: TextStyle(
                fontSize: 20,
                color: Color(0xFF00FFFF),
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              widget.isExpanded
                  ? 'Ask me anything about trading strategies,\nrisk management, market analysis, or VyRaTrader features.\nI provide comprehensive, detailed responses!'
                  : 'Your elite AI trading companion\nAsk me anything!',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12,
                color: Colors.white.withOpacity(0.6),
                height: 1.6,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;
    final padding = MediaQuery.of(context).padding;
    
    // Calculate available height accounting for safe areas
    final availableHeight = widget.isExpanded 
        ? (screenHeight - padding.top - padding.bottom - 32).toDouble() // Account for safe areas
        : 520.0;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeInOut,
      width: widget.isExpanded ? (screenWidth - 32).toDouble() : 360.0,
      height: availableHeight,
      decoration: BoxDecoration(
        color: const Color(0xFF000C1F),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFF00FFFF).withOpacity(0.4),
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00FFFF).withOpacity(0.3),
            blurRadius: 40,
            spreadRadius: 6,
          ),
          BoxShadow(
            color: const Color(0xFF00D4FF).withOpacity(0.2),
            blurRadius: 80,
            spreadRadius: 10,
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF000C1F), Color(0xFF001F3F)],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
                child: messages.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        controller: _scrollCtrl,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        itemCount: messages.length,
                        itemBuilder: (_, i) => _buildBubble(messages[i]),
                      ),
              ),
            ),
            if (typing) _buildTypingIndicator(),
            if (messages.isNotEmpty) _buildQuickActions(),
            _buildInputArea(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF00FFFF), Color(0xFF00D4FF)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00FFFF).withOpacity(0.15),
            blurRadius: 4,
            spreadRadius: 0.5,
          ),
        ],
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Stack(
            clipBehavior: Clip.hardEdge, // Prevent overflow
            children: [
              // Light blue speckle effect
              ...List.generate(20, (i) {
                final leftPos = (i * 35.0) % constraints.maxWidth.clamp(0, 380);
                final topPos = (i * 15.0) % 60;
                return Positioned(
                  left: leftPos.clamp(0.0, constraints.maxWidth - 10), // Ensure within bounds
                  top: topPos.clamp(0.0, 60.0), // Ensure within header height
                  child: AnimatedBuilder(
                    animation: _glowController,
                    builder: (context, child) {
                      final delay = i * 0.08;
                      final value = (_glowController.value + delay) % 1.0;
                      return Opacity(
                        opacity: 0.2 + value * 0.3,
                        child: Container(
                          width: 3 + (i % 3),
                          height: 3 + (i % 3),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white.withOpacity(0.5),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.white.withOpacity(0.15),
                                blurRadius: 1,
                                spreadRadius: 0.3,
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                );
              }),
              Row(
                children: [
                  // Circular icon with star/sparkle
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.white.withOpacity(0.3),
                        width: 1.5,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.white.withOpacity(0.2),
                          blurRadius: 8,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.auto_awesome,
                      size: 20,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Title and subtitle
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Prince AI',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          widget.isExpanded
                              ? 'Expanded Analysis Mode'
                              : _selectedSymbol != null
                                  ? 'Analyzing $_selectedSymbol'
                                  : 'Elite Trading Assistant',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.9),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                    ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Expand button (square with rounded corners)
                  GestureDetector(
                    onTap: widget.onToggleExpand,
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.3),
                          width: 1,
                        ),
                      ),
                      child: Icon(
                        widget.isExpanded
                            ? Icons.fullscreen_exit
                            : Icons.fullscreen,
                        color: Colors.white,
                        size: 18,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  // Close button (square with rounded corners)
                  GestureDetector(
                    onTap: widget.onClose,
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.3),
                          width: 1,
                        ),
                      ),
                      child: const Icon(
                        Icons.close,
                        color: Colors.white,
                        size: 18,
                      ),
                    ),
                  ),
            ],
          ),
          ],
        );
      },
    ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: Color(0xFF001F3F),
        border: Border(top: BorderSide(color: Color(0xFF00FFFF), width: 0.5)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF000C1F),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: const Color(0xFF00FFFF).withOpacity(0.3),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                    spreadRadius: -2,
                  ),
                ],
              ),
              child: TextField(
                controller: _ctrl,
                enabled: !typing,
                style: const TextStyle(color: Colors.white, fontSize: 13.5),
                maxLines: null,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _send(),
                decoration: InputDecoration(
                  hintText: 'Ask Prince anything...',
                  hintStyle: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 13,
                  ),
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          GestureDetector(
            onTap: typing ? null : _send,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: typing
                    ? null
                    : const LinearGradient(
                        colors: [Color(0xFF00FFFF), Color(0xFF00D4FF)],
                      ),
                color: typing ? const Color(0xFF001F3F) : null,
                shape: BoxShape.circle,
                boxShadow: typing
                    ? []
                    : [
                        BoxShadow(
                          color: const Color(0xFF00FFFF).withOpacity(0.5),
                          blurRadius: 12,
                          spreadRadius: 2,
                        ),
                      ],
              ),
              child: Icon(
                Icons.send_rounded,
                color: typing
                    ? Colors.white.withOpacity(0.3)
                    : const Color(0xFF000C1F),
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
