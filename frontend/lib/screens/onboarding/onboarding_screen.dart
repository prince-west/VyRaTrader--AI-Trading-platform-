// lib/screens/onboarding/onboarding_screen.dart
// ONLY FIX: Added SingleChildScrollView to prevent overflow
// NO OTHER CHANGES

import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../../routes/app_routes.dart';
import '../../widgets/glow_button.dart';

class OnboardingScreen extends StatefulWidget {
  static const routeName = '/onboarding';
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>
    with TickerProviderStateMixin {
  bool accepted = false;
  late AnimationController _fadeController;
  late AnimationController _pulseController;
  late AnimationController _particleController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    // Fade in animation
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeInOut,
    );

    // Pulse animation for logo
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Particle animation
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();

    _fadeController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _pulseController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Animated gradient background
          AnimatedContainer(
            duration: const Duration(seconds: 3),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF000814),
                  const Color(0xFF001219),
                  const Color(0xFF001F3F),
                  const Color(0xFF000C1F),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                stops: const [0.0, 0.3, 0.7, 1.0],
              ),
            ),
          ),

          // Animated particles
          AnimatedBuilder(
            animation: _particleController,
            builder: (context, child) {
              return CustomPaint(
                painter: ParticlePainter(_particleController.value),
                size: Size.infinite,
              );
            },
          ),

          // Grid overlay effect
          CustomPaint(painter: GridPainter(), size: Size.infinite),

          // Main content - ONLY FIX: Wrapped in SingleChildScrollView
          SafeArea(
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 24,
                    vertical: 20,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 20),

                      // Logo with glow effect
                      ScaleTransition(
                        scale: _pulseAnimation,
                        child: ShaderMask(
                          shaderCallback: (bounds) => const LinearGradient(
                            colors: [
                              Color(0xFF00FFFF),
                              Color(0xFF00D4FF),
                              Color(0xFF0099FF),
                            ],
                          ).createShader(bounds),
                          child: const Text(
                            'VyRaTrader',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 42,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 2,
                              shadows: [
                                Shadow(
                                    color: Color(0xFF00FFFF), blurRadius: 20),
                                Shadow(
                                    color: Color(0xFF00FFFF), blurRadius: 40),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 8),

                      // AI Badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF00FFFF), Color(0xFF0099FF)],
                          ),
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF00FFFF).withOpacity(0.5),
                              blurRadius: 10,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.auto_awesome,
                              size: 16,
                              color: Colors.black,
                            ),
                            SizedBox(width: 6),
                            Text(
                              'AI-Powered by Prince',
                              style: TextStyle(
                                color: Colors.black,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Tagline with typing effect
                      const Text(
                        'Autonomous trading intelligence.\nSecure. Adaptive. Professional.',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 16,
                          height: 1.5,
                          letterSpacing: 0.5,
                        ),
                      ),

                      const SizedBox(height: 40),

                      // Hero image with holographic effect
                      SizedBox(
                        height: 300,
                        child: Center(
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              // Holographic rings
                              ...List.generate(3, (index) {
                                return AnimatedBuilder(
                                  animation: _particleController,
                                  builder: (context, child) {
                                    return Transform.scale(
                                      scale: 1 +
                                          (index * 0.3) +
                                          (math.sin(
                                                _particleController.value *
                                                        2 *
                                                        math.pi +
                                                    index,
                                              ) *
                                              0.1),
                                      child: Container(
                                        width: 200 + (index * 40),
                                        height: 200 + (index * 40),
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            color: Color(
                                              0xFF00FFFF,
                                            ).withOpacity(0.2 - (index * 0.05)),
                                            width: 2,
                                          ),
                                        ),
                                      ),
                                    );
                                  },
                                );
                              }),

                              // Central icon
                              Container(
                                width: 160,
                                height: 160,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      const Color(0xFF00FFFF).withOpacity(0.3),
                                      const Color(0xFF001F3F).withOpacity(0.1),
                                    ],
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(
                                        0xFF00FFFF,
                                      ).withOpacity(0.5),
                                      blurRadius: 60,
                                      spreadRadius: 10,
                                    ),
                                  ],
                                ),
                                child: const Icon(
                                  Icons.trending_up,
                                  size: 80,
                                  color: Color(0xFF00FFFF),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 40),

                      // Feature highlights
                      _buildFeatureRow(Icons.security, 'Bank-grade security'),
                      const SizedBox(height: 12),
                      _buildFeatureRow(Icons.insights, 'AI-driven strategies'),
                      const SizedBox(height: 12),
                      _buildFeatureRow(Icons.speed, 'Real-time execution'),

                      const SizedBox(height: 32),

                      // Terms acceptance with futuristic checkbox
                      GestureDetector(
                        onTap: () => setState(() => accepted = !accepted),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.05),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: accepted
                                  ? const Color(0xFF00FFFF)
                                  : Colors.white.withOpacity(0.2),
                              width: 2,
                            ),
                            boxShadow: accepted
                                ? [
                                    BoxShadow(
                                      color: const Color(
                                        0xFF00FFFF,
                                      ).withOpacity(0.3),
                                      blurRadius: 15,
                                      spreadRadius: 2,
                                    ),
                                  ]
                                : null,
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 24,
                                height: 24,
                                decoration: BoxDecoration(
                                  color: accepted
                                      ? const Color(0xFF00FFFF)
                                      : Colors.transparent,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: accepted
                                        ? const Color(0xFF00FFFF)
                                        : Colors.white54,
                                    width: 2,
                                  ),
                                ),
                                child: accepted
                                    ? const Icon(
                                        Icons.check,
                                        size: 16,
                                        color: Colors.black,
                                      )
                                    : null,
                              ),
                              const SizedBox(width: 12),
                              const Expanded(
                                child: Text(
                                  'I accept the Terms & Conditions',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 20),

                      // Get Started button
                      GlowButton(
                        text: 'Get Started',
                        onPressed: accepted
                            ? () => Navigator.pushReplacementNamed(
                                  context,
                                  AppRoutes.signup,
                                )
                            : null,
                      ),

                      const SizedBox(height: 16),

                      // Read Terms link
                      Center(
                        child: TextButton(
                          onPressed: () =>
                              Navigator.pushNamed(context, AppRoutes.terms),
                          child: const Text(
                            'Read Full Terms & Conditions',
                            style: TextStyle(
                              color: Color(0xFF00FFFF),
                              fontSize: 14,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureRow(IconData icon, String text) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFF00FFFF).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF00FFFF).withOpacity(0.3)),
          ),
          child: Icon(icon, size: 20, color: const Color(0xFF00FFFF)),
        ),
        const SizedBox(width: 12),
        Text(
          text,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 15,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

// Particle painter for background effect
class ParticlePainter extends CustomPainter {
  final double animationValue;
  final math.Random random = math.Random(42);

  ParticlePainter(this.animationValue);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..strokeWidth = 1
      ..style = PaintingStyle.fill;

    for (int i = 0; i < 50; i++) {
      final x =
          (random.nextDouble() * size.width + animationValue * 50) % size.width;
      final y =
          (random.nextDouble() * size.height + animationValue * 30 * (i % 3)) %
              size.height;
      final opacity = (math.sin(animationValue * 2 * math.pi + i) + 1) / 2;

      paint.color = Color(0xFF00FFFF).withOpacity(opacity * 0.3);
      canvas.drawCircle(Offset(x, y), random.nextDouble() * 2 + 1, paint);
    }
  }

  @override
  bool shouldRepaint(ParticlePainter oldDelegate) => true;
}

// Grid painter for cyber effect
class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF00FFFF).withOpacity(0.03)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    const spacing = 40.0;

    // Vertical lines
    for (double i = 0; i < size.width; i += spacing) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), paint);
    }

    // Horizontal lines
    for (double i = 0; i < size.height; i += spacing) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), paint);
    }
  }

  @override
  bool shouldRepaint(GridPainter oldDelegate) => false;
}
