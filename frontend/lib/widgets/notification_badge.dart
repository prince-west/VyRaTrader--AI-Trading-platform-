// lib/widgets/notification_badge.dart
// PRODUCTION READY - Fixed API URL
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import 'dart:math' as math;
import '../screens/notifications/notifications_screen.dart';
import '../core/api_client.dart';

class NotificationBadge extends StatefulWidget {
  final bool showLabel;
  final double iconSize;

  const NotificationBadge({
    super.key,
    this.showLabel = false,
    this.iconSize = 24,
  });

  @override
  State<NotificationBadge> createState() => _NotificationBadgeState();
}

class _NotificationBadgeState extends State<NotificationBadge>
    with TickerProviderStateMixin {
  int unreadCount = 0;
  Timer? _pollTimer;
  late AnimationController _pulseController;
  late AnimationController _shakeController;
  late AnimationController _glowController;
  late Animation<double> _shakeAnimation;
  OverlayEntry? _overlayEntry;
  bool _isShowingPopup = false;
  String? _latestNotificationTitle;
  String? _latestNotificationType;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);

    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _shakeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _shakeController, curve: Curves.elasticInOut),
    );

    _glowController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    _fetchNotifications();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _pulseController.dispose();
    _shakeController.dispose();
    _glowController.dispose();
    _removePopup();
    super.dispose();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _fetchNotifications();
    });
  }

  Future<void> _fetchNotifications() async {
    try {
      // FIXED: Use production API URL
      final api = Provider.of<ApiClient>(context, listen: false);
      final res = await api.get('/notifications', params: {}, queryParams: {});
      final notifications = (res['notifications'] ?? []) as List<dynamic>;

      final newUnreadCount =
          notifications.where((n) => n['read'] != true).length;

      if (mounted) {
        final hadIncrease = newUnreadCount > unreadCount;
        setState(() {
          unreadCount = newUnreadCount;
          if (hadIncrease && notifications.isNotEmpty) {
            final latest = notifications.firstWhere(
              (n) => n['read'] != true,
              orElse: () => notifications.first,
            ) as Map<String, dynamic>;
            _latestNotificationTitle =
                latest['title'] ?? latest['message'] ?? 'New notification';
            _latestNotificationType = (latest['type'] ?? 'system').toString();
          }
        });

        if (hadIncrease) {
          _shakeController.forward(from: 0);
          _showPopupNotification();
        }
      }
    } catch (e) {
      debugPrint('Failed to fetch notifications: $e');
    }
  }

  void _showPopupNotification() {
    if (_isShowingPopup || _latestNotificationTitle == null) return;

    _removePopup();
    _isShowingPopup = true;

    _overlayEntry = OverlayEntry(
      builder: (context) => _PopupNotification(
        title: _latestNotificationTitle!,
        type: _latestNotificationType ?? 'system',
        onDismiss: _removePopup,
        onTap: () {
          _removePopup();
          Navigator.pushNamed(context, NotificationsScreen.routeName);
        },
      ),
    );

    try {
      Overlay.of(context).insert(_overlayEntry!);
      
      Future.delayed(const Duration(seconds: 5), () {
        _removePopup();
      });
    } catch (e) {
      debugPrint('Failed to show overlay notification: $e');
      _isShowingPopup = false;
      _overlayEntry = null;
    }
  }

  void _removePopup() {
    _overlayEntry?.remove();
    _overlayEntry = null;
    _isShowingPopup = false;
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.pushNamed(context, NotificationsScreen.routeName);
      },
      child: AnimatedBuilder(
        animation: Listenable.merge([_shakeAnimation, _glowController]),
        builder: (context, child) {
          final shake = math.sin(_shakeAnimation.value * math.pi * 4) *
              (1 - _shakeAnimation.value) *
              5;

          return Transform.translate(
            offset: Offset(shake, 0),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: unreadCount > 0
                    ? LinearGradient(
                        colors: [
                          const Color(0xFF00FFFF).withOpacity(0.2),
                          Colors.transparent,
                        ],
                      )
                    : null,
                border: Border.all(
                  color: unreadCount > 0
                      ? const Color(
                          0xFF00FFFF,
                        ).withOpacity(0.3 + (_glowController.value * 0.4))
                      : Colors.white.withOpacity(0.3),
                  width: unreadCount > 0 ? 2 : 1,
                ),
                boxShadow: unreadCount > 0
                    ? [
                        BoxShadow(
                          color: const Color(
                            0xFF00FFFF,
                          ).withOpacity(0.3 + (_glowController.value * 0.3)),
                          blurRadius: 12 + (_glowController.value * 8),
                          spreadRadius: 2,
                        ),
                      ]
                    : null,
              ),
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Icon(
                    unreadCount > 0
                        ? Icons.notifications_active
                        : Icons.notifications_outlined,
                    color: unreadCount > 0
                        ? const Color(0xFF00FFFF)
                        : Colors.white.withOpacity(0.7),
                    size: widget.iconSize,
                  ),
                  if (unreadCount > 0)
                    Positioned(
                      right: -8,
                      top: -8,
                      child: AnimatedBuilder(
                        animation: _pulseController,
                        builder: (context, child) {
                          return Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: LinearGradient(
                                colors: [
                                  Color.lerp(
                                    const Color(0xFF00FFFF),
                                    Colors.white,
                                    _pulseController.value * 0.3,
                                  )!,
                                  const Color(0xFF00BFFF),
                                ],
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(0xFF00FFFF).withOpacity(
                                    0.5 + (_pulseController.value * 0.3),
                                  ),
                                  blurRadius: 8 + (_pulseController.value * 4),
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                            child: Text(
                              unreadCount > 99 ? '99+' : '$unreadCount',
                              style: const TextStyle(
                                color: Colors.black,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _PopupNotification extends StatefulWidget {
  final String title;
  final String type;
  final VoidCallback onDismiss;
  final VoidCallback onTap;

  const _PopupNotification({
    required this.title,
    required this.type,
    required this.onDismiss,
    required this.onTap,
  });

  @override
  State<_PopupNotification> createState() => _PopupNotificationState();
}

class _PopupNotificationState extends State<_PopupNotification>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.elasticOut));

    _fadeAnimation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeIn));

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _dismiss() {
    _controller.reverse().then((_) {
      widget.onDismiss();
    });
  }

  Color _getTypeColor() {
    switch (widget.type.toLowerCase()) {
      case 'trade':
        return const Color(0xFF00FF88);
      case 'payment':
      case 'deposit':
        return const Color(0xFF00FFFF);
      case 'withdrawal':
        return const Color(0xFFFF8800);
      case 'alert':
        return const Color(0xFFFF0088);
      default:
        return const Color(0xFF00BFFF);
    }
  }

  IconData _getTypeIcon() {
    switch (widget.type.toLowerCase()) {
      case 'trade':
        return Icons.trending_up;
      case 'payment':
      case 'deposit':
        return Icons.account_balance_wallet;
      case 'withdrawal':
        return Icons.arrow_upward;
      case 'alert':
        return Icons.warning_amber_rounded;
      default:
        return Icons.notifications_active;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).padding.top + 16,
      left: 16,
      right: 16,
      child: SlideTransition(
        position: _slideAnimation,
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: GestureDetector(
            onTap: widget.onTap,
            onHorizontalDragEnd: (details) {
              if (details.velocity.pixelsPerSecond.dx.abs() > 300) {
                _dismiss();
              }
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: LinearGradient(
                  colors: [
                    _getTypeColor().withOpacity(0.9),
                    Colors.black.withOpacity(0.95),
                  ],
                ),
                border: Border.all(color: _getTypeColor(), width: 2),
                boxShadow: [
                  BoxShadow(
                    color: _getTypeColor().withOpacity(0.5),
                    blurRadius: 20,
                    spreadRadius: 2,
                  ),
                  BoxShadow(
                    color: Colors.black.withOpacity(0.8),
                    blurRadius: 10,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _getTypeColor().withOpacity(0.2),
                      border: Border.all(color: _getTypeColor(), width: 2),
                    ),
                    child: Icon(
                      _getTypeIcon(),
                      color: _getTypeColor(),
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'New Notification',
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          widget.title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: Icon(
                      Icons.close,
                      color: Colors.white.withOpacity(0.7),
                      size: 20,
                    ),
                    onPressed: _dismiss,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
