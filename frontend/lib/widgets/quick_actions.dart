// lib/widgets/quick_actions.dart
import 'package:flutter/material.dart';

class QuickActions extends StatefulWidget {
  final void Function()? onDeposit;
  final void Function()? onWithdraw;
  final void Function()? onTrade;
  final Color primaryColor;
  final Color depositColor;
  final Color withdrawColor;
  final Color tradeColor;

  const QuickActions({
    super.key,
    this.onDeposit,
    this.onWithdraw,
    this.onTrade,
    this.primaryColor = const Color(0xFF00FFFF),
    this.depositColor = const Color(0xFF00FF88),
    this.withdrawColor = const Color(0xFFFF0080),
    this.tradeColor = const Color(0xFF00FFFF),
  });

  @override
  State<QuickActions> createState() => _QuickActionsState();
}

class _QuickActionsState extends State<QuickActions>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _shimmerController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();

    _pulseAnimation = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _shimmerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_pulseController, _shimmerController]),
      builder: (context, child) {
        return Row(
          children: [
            Expanded(
              child: _ActionButton(
                onPressed: widget.onDeposit,
                icon: Icons.add_circle_outline,
                label: 'DEPOSIT',
                glowColor: widget.depositColor,
                pulseValue: _pulseAnimation.value,
                shimmerValue: _shimmerController.value,
                gradientColors: [
                  widget.depositColor.withOpacity(0.2),
                  widget.depositColor.withOpacity(0.05),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionButton(
                onPressed: widget.onWithdraw,
                icon: Icons.arrow_circle_down_outlined,
                label: 'WITHDRAW',
                glowColor: widget.withdrawColor,
                pulseValue: _pulseAnimation.value,
                shimmerValue: _shimmerController.value,
                gradientColors: [
                  widget.withdrawColor.withOpacity(0.2),
                  widget.withdrawColor.withOpacity(0.05),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionButton(
                onPressed: widget.onTrade,
                icon: Icons.swap_vert_circle_outlined,
                label: 'TRADE',
                glowColor: widget.tradeColor,
                pulseValue: _pulseAnimation.value,
                shimmerValue: _shimmerController.value,
                gradientColors: [
                  widget.tradeColor.withOpacity(0.2),
                  widget.tradeColor.withOpacity(0.05),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _ActionButton extends StatefulWidget {
  final VoidCallback? onPressed;
  final IconData icon;
  final String label;
  final Color glowColor;
  final double pulseValue;
  final double shimmerValue;
  final List<Color> gradientColors;

  const _ActionButton({
    required this.onPressed,
    required this.icon,
    required this.label,
    required this.glowColor,
    required this.pulseValue,
    required this.shimmerValue,
    required this.gradientColors,
  });

  @override
  State<_ActionButton> createState() => _ActionButtonState();
}

class _ActionButtonState extends State<_ActionButton> {
  bool _isPressed = false;
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTapDown: (_) => setState(() => _isPressed = true),
        onTapUp: (_) {
          setState(() => _isPressed = false);
          widget.onPressed?.call();
        },
        onTapCancel: () => setState(() => _isPressed = false),
        child: AnimatedScale(
          scale: _isPressed ? 0.95 : (_isHovered ? 1.02 : 1.0),
          duration: const Duration(milliseconds: 150),
          curve: Curves.easeOut,
          child: Container(
            height: 60,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              gradient: LinearGradient(
                colors: widget.gradientColors,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              border: Border.all(
                color: widget.glowColor.withOpacity(
                  _isHovered
                      ? widget.pulseValue * 0.8
                      : widget.pulseValue * 0.5,
                ),
                width: _isHovered ? 2.0 : 1.5,
              ),
              boxShadow: [
                // Outer glow
                BoxShadow(
                  color: widget.glowColor.withOpacity(
                    _isHovered
                        ? widget.pulseValue * 0.4
                        : widget.pulseValue * 0.2,
                  ),
                  blurRadius: _isHovered ? 20 : 16,
                  spreadRadius: _isHovered ? 3 : 1,
                ),
                // Inner highlight
                BoxShadow(
                  color: widget.glowColor.withOpacity(widget.pulseValue * 0.15),
                  blurRadius: 8,
                  spreadRadius: -2,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Stack(
                children: [
                  // Shimmer effect
                  Positioned.fill(
                    child: CustomPaint(
                      painter: _ShimmerPainter(
                        progress: widget.shimmerValue,
                        color: widget.glowColor.withOpacity(0.1),
                      ),
                    ),
                  ),

                  // Content
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: widget.onPressed,
                      borderRadius: BorderRadius.circular(16),
                      splashColor: widget.glowColor.withOpacity(0.2),
                      highlightColor: widget.glowColor.withOpacity(0.1),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          vertical: 16,
                          horizontal: 12,
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            // Icon with glow
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: RadialGradient(
                                  colors: [
                                    widget.glowColor.withOpacity(0.3),
                                    widget.glowColor.withOpacity(0.1),
                                    Colors.transparent,
                                  ],
                                  stops: const [0.0, 0.5, 1.0],
                                ),
                              ),
                              child: Icon(
                                widget.icon,
                                color: widget.glowColor,
                                size: 22,
                                shadows: [
                                  Shadow(
                                    color: widget.glowColor.withOpacity(0.8),
                                    blurRadius: 12,
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 8),

                            // Label text
                            Text(
                              widget.label,
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 0.5,
                                shadows: [
                                  Shadow(
                                    color: widget.glowColor.withOpacity(0.6),
                                    blurRadius: 8,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  // Corner accent
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: widget.glowColor,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: widget.glowColor,
                            blurRadius: 6,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                    ),
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

class _ShimmerPainter extends CustomPainter {
  final double progress;
  final Color color;

  _ShimmerPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = LinearGradient(
        colors: [Colors.transparent, color, Colors.transparent],
        stops: const [0.0, 0.5, 1.0],
        transform: GradientRotation(progress * 6.28), // Full rotation
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final path = Path()
      ..moveTo(size.width * progress, 0)
      ..lineTo(size.width * progress + size.width * 0.3, 0)
      ..lineTo(size.width * progress + size.width * 0.1, size.height)
      ..lineTo(size.width * progress - size.width * 0.2, size.height)
      ..close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_ShimmerPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
