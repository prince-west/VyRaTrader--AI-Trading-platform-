// lib/widgets/glow_button.dart
import 'package:flutter/material.dart';

class GlowButton extends StatefulWidget {
  final VoidCallback? onPressed;
  final Widget? child;
  final String? text;
  final Color glowColor;
  final double radius;
  final bool isLoading;
  final IconData? icon;
  final double width;
  final double height;

  const GlowButton({
    super.key,
    required this.onPressed,
    this.child,
    this.text,
    this.glowColor = const Color(0xFF00FFFF),
    this.radius = 14,
    this.isLoading = false,
    this.icon,
    this.width = double.infinity,
    this.height = 56,
  });

  @override
  State<GlowButton> createState() => _GlowButtonState();
}

class _GlowButtonState extends State<GlowButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _pulseAnimation;
  late Animation<double> _scaleAnimation;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(
      begin: 0.6,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));

    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    // Use the _scaleAnimation field in your logic
    _scaleAnimation.addListener(() {
      setState(() {
        // Update the button's scale based on the _scaleAnimation value
        _isPressed = _scaleAnimation.value < 1.0;
      });
    });

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _controller.reverse();
      } else if (status == AnimationStatus.dismissed) {
        _controller.forward();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return GestureDetector(
          onTapDown: (_) => setState(() => _isPressed = true),
          onTapUp: (_) => setState(() => _isPressed = false),
          onTapCancel: () => setState(() => _isPressed = false),
          child: Transform.scale(
            scale: _isPressed ? 0.97 : 1.0,
            child: Container(
              width: widget.width,
              height: widget.height,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(widget.radius),
                gradient: LinearGradient(
                  colors: [
                    widget.glowColor.withOpacity(0.1),
                    widget.glowColor.withOpacity(0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(
                  color: widget.glowColor.withOpacity(
                    _pulseAnimation.value * 0.8,
                  ),
                  width: 1.5,
                ),
                boxShadow: [
                  // Outer glow
                  BoxShadow(
                    color: widget.glowColor.withOpacity(
                      _pulseAnimation.value * 0.4,
                    ),
                    blurRadius: 24,
                    spreadRadius: 4,
                  ),
                  // Inner glow
                  BoxShadow(
                    color: widget.glowColor.withOpacity(
                      _pulseAnimation.value * 0.2,
                    ),
                    blurRadius: 12,
                    spreadRadius: -2,
                  ),
                  // Intense center glow
                  BoxShadow(
                    color: widget.glowColor.withOpacity(
                      _pulseAnimation.value * 0.6,
                    ),
                    blurRadius: 8,
                    spreadRadius: 0,
                  ),
                ],
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: widget.onPressed,
                  borderRadius: BorderRadius.circular(widget.radius),
                  splashColor: widget.glowColor.withOpacity(0.3),
                  highlightColor: widget.glowColor.withOpacity(0.1),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(widget.radius),
                      gradient: LinearGradient(
                        colors: [
                          Colors.white.withOpacity(0.15),
                          Colors.white.withOpacity(0.05),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                    ),
                    child: Center(
                      child: widget.isLoading
                          ? _buildLoadingIndicator()
                          : _buildContent(),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildContent() {
    if (widget.child != null) {
      return widget.child!;
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.icon != null) ...[
          Icon(widget.icon, color: widget.glowColor, size: 20),
          const SizedBox(width: 8),
        ],
        Text(
          widget.text ?? '',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            shadows: [
              Shadow(color: widget.glowColor.withOpacity(0.8), blurRadius: 8),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLoadingIndicator() {
    return SizedBox(
      height: 24,
      width: 24,
      child: CircularProgressIndicator(
        strokeWidth: 2.5,
        valueColor: AlwaysStoppedAnimation<Color>(widget.glowColor),
      ),
    );
  }
}
