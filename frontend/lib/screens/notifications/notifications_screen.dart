// lib/screens/notifications/notifications_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:ui';
import '../../core/api_client.dart';

class NotificationsScreen extends StatefulWidget {
  static const routeName = '/notifications';
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen>
    with TickerProviderStateMixin {
  bool loading = true;
  List<dynamic> items = [];
  late AnimationController _fadeController;
  late AnimationController _pulseController;
  String selectedFilter = 'All';

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);
    _load();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => loading = true);
    _fadeController.forward(from: 0);

    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      final res = await api.get('/notifications', params: {}, queryParams: {});
      items = (res['notifications'] ?? []) as List<dynamic>;
    } catch (e) {
      if (mounted) {
        _showStyledSnackBar('Failed to load notifications: $e', isError: true);
      }
    } finally {
      if (mounted) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> _markAllRead() async {
    try {
      final api = Provider.of<ApiClient>(context, listen: false);
      await api.post('/notifications/mark_read', {});
      setState(() => items = items.map((i) => {...i, 'read': true}).toList());
      _showStyledSnackBar('All notifications marked as read', isError: false);
    } catch (e) {
      _showStyledSnackBar('Failed to mark as read: $e', isError: true);
    }
  }

  void _showStyledSnackBar(String message, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError ? Icons.error_outline : Icons.check_circle_outline,
              color: isError ? Colors.redAccent : const Color(0xFF00FFFF),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(message, style: const TextStyle(color: Colors.white)),
            ),
          ],
        ),
        backgroundColor: Colors.black.withOpacity(0.9),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  List<dynamic> get filteredItems {
    if (selectedFilter == 'All') return items;
    if (selectedFilter == 'Unread') {
      return items.where((i) => i['read'] != true).toList();
    }
    return items
        .where((i) => i['type'] == selectedFilter.toLowerCase())
        .toList();
  }

  int get unreadCount => items.where((i) => i['read'] != true).length;

  @override
  Widget build(BuildContext context) {
    final displayItems = filteredItems;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: ClipRect(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    const Color(0xFF00FFFF).withOpacity(0.1),
                    Colors.black.withOpacity(0.3),
                  ],
                ),
              ),
            ),
          ),
        ),
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFF00FFFF), width: 1),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00FFFF).withOpacity(0.3),
                  blurRadius: 8,
                ),
              ],
            ),
            child: const Icon(
              Icons.arrow_back,
              color: Color(0xFF00FFFF),
              size: 20,
            ),
          ),
          onPressed: () => Navigator.pop(context),
        ),
        title: Row(
          children: [
            ShaderMask(
              shaderCallback: (bounds) => const LinearGradient(
                colors: [Color(0xFF00FFFF), Color(0xFF00BFFF)],
              ).createShader(bounds),
              child: const Text(
                'Notifications',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
            if (unreadCount > 0) ...[
              const SizedBox(width: 12),
              AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  return Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
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
                          color: const Color(
                            0xFF00FFFF,
                          ).withOpacity(0.3 + (_pulseController.value * 0.3)),
                          blurRadius: 8 + (_pulseController.value * 4),
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                    child: Text(
                      '$unreadCount',
                      style: const TextStyle(
                        color: Colors.black,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  );
                },
              ),
            ],
          ],
        ),
        actions: [
          if (unreadCount > 0)
            IconButton(
              icon: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFF00FFFF).withOpacity(0.2),
                      Colors.transparent,
                    ],
                  ),
                  border: Border.all(
                    color: const Color(0xFF00FFFF).withOpacity(0.5),
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.done_all,
                  color: Color(0xFF00FFFF),
                  size: 20,
                ),
              ),
              onPressed: _markAllRead,
              tooltip: 'Mark all as read',
            ),
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF00FFFF).withOpacity(0.2),
                    Colors.transparent,
                  ],
                ),
                border: Border.all(
                  color: const Color(0xFF00FFFF).withOpacity(0.5),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.refresh,
                color: Color(0xFF00FFFF),
                size: 20,
              ),
            ),
            onPressed: _load,
            tooltip: 'Refresh',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF000C1F), Color(0xFF001F3F), Color(0xFF000C1F)],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Filter chips
              Container(
                height: 50,
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  children: [
                    _buildFilterChip('All'),
                    _buildFilterChip('Unread'),
                    _buildFilterChip('Trade'),
                    _buildFilterChip('Payment'),
                    _buildFilterChip('System'),
                  ],
                ),
              ),

              // Content
              Expanded(
                child: loading
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              width: 60,
                              height: 60,
                              child: CircularProgressIndicator(
                                strokeWidth: 3,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  const Color(0xFF00FFFF),
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),
                            ShaderMask(
                              shaderCallback: (bounds) => const LinearGradient(
                                colors: [Color(0xFF00FFFF), Color(0xFF00BFFF)],
                              ).createShader(bounds),
                              child: const Text(
                                'Loading notifications...',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )
                    : displayItems.isEmpty
                        ? _buildEmptyState()
                        : FadeTransition(
                            opacity: _fadeController,
                            child: ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: displayItems.length,
                              itemBuilder: (context, index) {
                                return TweenAnimationBuilder<double>(
                                  tween: Tween(begin: 0.0, end: 1.0),
                                  duration: Duration(
                                    milliseconds: 300 + (index * 50),
                                  ),
                                  curve: Curves.easeOutCubic,
                                  builder: (context, value, child) {
                                    return Transform.translate(
                                      offset: Offset(0, 20 * (1 - value)),
                                      child:
                                          Opacity(opacity: value, child: child),
                                    );
                                  },
                                  child: _buildNotificationCard(
                                    displayItems[index] as Map<String, dynamic>,
                                    index,
                                  ),
                                );
                              },
                            ),
                          ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterChip(String label) {
    final isSelected = selectedFilter == label;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (selected) {
          setState(() => selectedFilter = label);
        },
        backgroundColor: Colors.black.withOpacity(0.3),
        selectedColor: const Color(0xFF00FFFF).withOpacity(0.2),
        checkmarkColor: const Color(0xFF00FFFF),
        labelStyle: TextStyle(
          color: isSelected ? const Color(0xFF00FFFF) : Colors.white70,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
        side: BorderSide(
          color: isSelected
              ? const Color(0xFF00FFFF)
              : Colors.white.withOpacity(0.2),
          width: isSelected ? 2 : 1,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF00FFFF).withOpacity(0.1),
                  Colors.transparent,
                ],
              ),
              border: Border.all(
                color: const Color(0xFF00FFFF).withOpacity(0.3),
                width: 2,
              ),
            ),
            child: Icon(
              Icons.notifications_none,
              size: 64,
              color: const Color(0xFF00FFFF).withOpacity(0.5),
            ),
          ),
          const SizedBox(height: 24),
          ShaderMask(
            shaderCallback: (bounds) => const LinearGradient(
              colors: [Color(0xFF00FFFF), Color(0xFF00BFFF)],
            ).createShader(bounds),
            child: const Text(
              'No Notifications',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            selectedFilter == 'All'
                ? 'You\'re all caught up!'
                : 'No $selectedFilter notifications',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotificationCard(Map<String, dynamic> item, int index) {
    final isUnread = item['read'] != true;
    final type = (item['type'] ?? 'system').toString().toLowerCase();
    final title = item['title'] ?? item['message'] ?? 'Notification';
    final body = item['body'] ?? '';
    final timestamp = item['created_at']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isUnread
              ? [
                  const Color(0xFF00FFFF).withOpacity(0.15),
                  Colors.black.withOpacity(0.4),
                ]
              : [Colors.black.withOpacity(0.3), Colors.black.withOpacity(0.2)],
        ),
        border: Border.all(
          color: isUnread
              ? const Color(0xFF00FFFF).withOpacity(0.5)
              : Colors.white.withOpacity(0.1),
          width: isUnread ? 1.5 : 1,
        ),
        boxShadow: isUnread
            ? [
                BoxShadow(
                  color: const Color(0xFF00FFFF).withOpacity(0.2),
                  blurRadius: 12,
                  spreadRadius: 1,
                ),
              ]
            : [],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          children: [
            // Glow effect for unread
            if (isUnread)
              Positioned(
                top: 0,
                left: 0,
                child: Container(
                  width: 4,
                  height: 60,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        const Color(0xFF00FFFF),
                        const Color(0xFF00FFFF).withOpacity(0.0),
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF00FFFF).withOpacity(0.5),
                        blurRadius: 8,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                ),
              ),

            // Content
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Icon
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [
                          _getTypeColor(type).withOpacity(0.2),
                          Colors.transparent,
                        ],
                      ),
                      border: Border.all(
                        color: _getTypeColor(type).withOpacity(0.5),
                        width: 1.5,
                      ),
                    ),
                    child: Icon(
                      _getTypeIcon(type),
                      color: _getTypeColor(type),
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 16),

                  // Text content
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                title,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: isUnread
                                      ? FontWeight.bold
                                      : FontWeight.w500,
                                ),
                              ),
                            ),
                            if (isUnread)
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: const Color(0xFF00FFFF),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(
                                        0xFF00FFFF,
                                      ).withOpacity(0.5),
                                      blurRadius: 6,
                                      spreadRadius: 1,
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                        if (body.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            body,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.7),
                              fontSize: 14,
                              height: 1.4,
                            ),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(
                              Icons.access_time,
                              size: 12,
                              color: Colors.white.withOpacity(0.5),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              _formatTimestamp(timestamp),
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'trade':
        return Icons.trending_up;
      case 'payment':
        return Icons.account_balance_wallet;
      case 'deposit':
        return Icons.arrow_downward;
      case 'withdrawal':
        return Icons.arrow_upward;
      case 'system':
        return Icons.info_outline;
      case 'alert':
        return Icons.warning_amber_rounded;
      default:
        return Icons.notifications;
    }
  }

  Color _getTypeColor(String type) {
    switch (type) {
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

  String _formatTimestamp(String timestamp) {
    if (timestamp.isEmpty) return 'Just now';
    try {
      final date = DateTime.parse(timestamp);
      final now = DateTime.now();
      final diff = now.difference(date);

      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${date.day}/${date.month}/${date.year}';
    } catch (e) {
      return timestamp;
    }
  }
}
