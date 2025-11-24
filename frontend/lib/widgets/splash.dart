// lib/screens/splash_screen.dart
import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:math' as math;

class Splash extends StatefulWidget {
  final VoidCallback? onDone;
  const Splash({super.key, this.onDone});

  @override
  State<Splash> createState() => _SplashState();
}

class _SplashState extends State<Splash> with TickerProviderStateMixin {
  late AnimationController _fadeController;
  late AnimationController _orbitController;
  late AnimationController _glowController;
  late AnimationController _particleController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();

    // Fade in animation
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    // Orbit animation for rings
    _orbitController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    // Glow pulse animation
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    // Particle animation
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _fadeController, curve: Curves.easeIn));

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _fadeController, curve: Curves.easeOutBack),
    );

    _glowAnimation = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    _fadeController.forward();

    // Navigate after splash duration
    Timer(const Duration(milliseconds: 3500), () {
      widget.onDone?.call();
    });
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _orbitController.dispose();
    _glowController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isSmallScreen = size.width < 360;
    final logoSize = isSmallScreen ? 120.0 : 160.0;
    final fontSize = isSmallScreen ? 32.0 : 42.0;

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF000C1F), Color(0xFF001028), Color(0xFF001F3F)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: Stack(
          children: [
            // Animated particles background
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _particleController,
                builder: (context, child) {
                  return CustomPaint(
                    painter: _ParticlesPainter(
                      progress: _particleController.value,
                      color: const Color(0xFF00FFFF),
                    ),
                  );
                },
              ),
            ),

            // Circuit board pattern overlay
            Positioned.fill(
              child: CustomPaint(
                painter: _CircuitPainter(
                  color: const Color(0xFF00FFFF).withOpacity(0.1),
                ),
              ),
            ),

            // Main content
            Center(
              child: AnimatedBuilder(
                animation: Listenable.merge([
                  _fadeController,
                  _orbitController,
                  _glowController,
                ]),
                builder: (context, child) {
                  return FadeTransition(
                    opacity: _fadeAnimation,
                    child: ScaleTransition(
                      scale: _scaleAnimation,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Logo with orbiting rings
                          SizedBox(
                            width: logoSize,
                            height: logoSize,
                            child: Stack(
                              alignment: Alignment.center,
                              children: [
                                // Outer orbiting ring
                                Transform.rotate(
                                  angle: _orbitController.value * 2 * math.pi,
                                  child: CustomPaint(
                                    size: Size(logoSize, logoSize),
                                    painter: _OrbitRingPainter(
                                      color: const Color(0xFF00FFFF),
                                      glowIntensity: _glowAnimation.value,
                                      thickness: 2.0,
                                    ),
                                  ),
                                ),

                                // Middle orbiting ring (opposite direction)
                                Transform.rotate(
                                  angle:
                                      -_orbitController.value * 1.5 * math.pi,
                                  child: CustomPaint(
                                    size: Size(
                                      logoSize * 0.75,
                                      logoSize * 0.75,
                                    ),
                                    painter: _OrbitRingPainter(
                                      color: const Color(0xFF00FFFF),
                                      glowIntensity: _glowAnimation.value,
                                      thickness: 2.5,
                                    ),
                                  ),
                                ),

                                // Inner orbiting ring
                                Transform.rotate(
                                  angle: _orbitController.value * 2.5 * math.pi,
                                  child: CustomPaint(
                                    size: Size(logoSize * 0.5, logoSize * 0.5),
                                    painter: _OrbitRingPainter(
                                      color: const Color(0xFF00FFFF),
                                      glowIntensity: _glowAnimation.value,
                                      thickness: 3.0,
                                    ),
                                  ),
                                ),

                                // Orbiting particle
                                Transform.rotate(
                                  angle: _orbitController.value * 2 * math.pi,
                                  child: Transform.translate(
                                    offset: Offset(logoSize / 2, 0),
                                    child: Container(
                                      width: 8,
                                      height: 8,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF00FFFF),
                                        shape: BoxShape.circle,
                                        boxShadow: [
                                          BoxShadow(
                                            color: const Color(0xFF00FFFF),
                                            blurRadius: 12,
                                            spreadRadius: 3,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),

                                // Center VR logo
                                Container(
                                  width: logoSize * 0.4,
                                  height: logoSize * 0.4,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: const Color(0xFF001F3F),
                                    border: Border.all(
                                      color: const Color(0xFF00FFFF),
                                      width: 3,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFF00FFFF)
                                            .withOpacity(
                                              _glowAnimation.value * 0.6,
                                            ),
                                        blurRadius: 24,
                                        spreadRadius: 4,
                                      ),
                                    ],
                                  ),
                                  child: Center(
                                    child: Text(
                                      'VR',
                                      style: TextStyle(
                                        fontSize: logoSize * 0.15,
                                        fontWeight: FontWeight.w900,
                                        color: const Color(0xFF00FFFF),
                                        letterSpacing: 2,
                                        shadows: [
                                          Shadow(
                                            color: const Color(0xFF00FFFF),
                                            blurRadius: 12,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          SizedBox(height: size.height * 0.04),

                          // App name with glow effect
                          Text(
                            'VyRaTrader',
                            style: TextStyle(
                              fontSize: fontSize,
                              fontWeight: FontWeight.w900,
                              color: const Color(0xFF00FFFF),
                              letterSpacing: 3,
                              shadows: [
                                Shadow(
                                  color: const Color(
                                    0xFF00FFFF,
                                  ).withOpacity(_glowAnimation.value),
                                  blurRadius: 20,
                                ),
                                Shadow(
                                  color: const Color(
                                    0xFF00FFFF,
                                  ).withOpacity(_glowAnimation.value * 0.5),
                                  blurRadius: 40,
                                ),
                              ],
                            ),
                          ),

                          SizedBox(height: size.height * 0.02),

                          // Subtitle
                          Text(
                            'AI-Powered Trading',
                            style: TextStyle(
                              fontSize: isSmallScreen ? 12 : 14,
                              fontWeight: FontWeight.w500,
                              color: const Color(0xFF00FFFF).withOpacity(0.6),
                              letterSpacing: 2,
                            ),
                          ),

                          SizedBox(height: size.height * 0.06),

                          // Loading indicator
                          SizedBox(
                            width: isSmallScreen ? 40 : 50,
                            height: isSmallScreen ? 40 : 50,
                            child: CircularProgressIndicator(
                              strokeWidth: 3,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                const Color(
                                  0xFF00FFFF,
                                ).withOpacity(_glowAnimation.value),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            // Bottom text
            Positioned(
              bottom: size.height * 0.05,
              left: 0,
              right: 0,
              child: FadeTransition(
                opacity: _fadeAnimation,
                child: Text(
                  'Powered by Prince AI',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: isSmallScreen ? 11 : 12,
                    color: const Color(0xFF00FFFF).withOpacity(0.4),
                    letterSpacing: 1.5,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Orbit ring painter
class _OrbitRingPainter extends CustomPainter {
  final Color color;
  final double glowIntensity;
  final double thickness;

  _OrbitRingPainter({
    required this.color,
    required this.glowIntensity,
    required this.thickness,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Glow
    final glowPaint = Paint()
      ..color = color.withOpacity(glowIntensity * 0.4)
      ..style = PaintingStyle.stroke
      ..strokeWidth = thickness + 4
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    canvas.drawOval(Rect.fromCircle(center: center, radius: radius), glowPaint);

    // Main ring
    final paint = Paint()
      ..color = color.withOpacity(glowIntensity * 0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = thickness;

    canvas.drawOval(Rect.fromCircle(center: center, radius: radius), paint);
  }

  @override
  bool shouldRepaint(_OrbitRingPainter oldDelegate) =>
      oldDelegate.glowIntensity != glowIntensity;
}

// Particles painter
class _ParticlesPainter extends CustomPainter {
  final double progress;
  final Color color;

  _ParticlesPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final random = math.Random(42);
    final paint = Paint()
      ..color = color.withOpacity(0.3)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);

    for (int i = 0; i < 50; i++) {
      final x = random.nextDouble() * size.width;
      final baseY = random.nextDouble() * size.height;
      final y = (baseY + progress * 100) % size.height;
      final radius = random.nextDouble() * 2 + 0.5;

      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(_ParticlesPainter oldDelegate) =>
      oldDelegate.progress != progress;
}

// Circuit board pattern painter
class _CircuitPainter extends CustomPainter {
  final Color color;

  _CircuitPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final random = math.Random(123);

    // Draw random circuit lines
    for (int i = 0; i < 15; i++) {
      final startX = random.nextDouble() * size.width;
      final startY = random.nextDouble() * size.height;
      final endX = startX + (random.nextDouble() - 0.5) * 200;
      final endY = startY + (random.nextDouble() - 0.5) * 200;

      canvas.drawLine(Offset(startX, startY), Offset(endX, endY), paint);

      // Draw nodes
      canvas.drawCircle(Offset(startX, startY), 3, paint);
      canvas.drawCircle(Offset(endX, endY), 3, paint);
    }

    // Draw corner decorations
    _drawCornerDecoration(canvas, size, Offset(20, 20), paint);
    _drawCornerDecoration(canvas, size, Offset(size.width - 20, 20), paint);
    _drawCornerDecoration(canvas, size, Offset(20, size.height - 20), paint);
    _drawCornerDecoration(
      canvas,
      size,
      Offset(size.width - 20, size.height - 20),
      paint,
    );
  }

  void _drawCornerDecoration(
    Canvas canvas,
    Size size,
    Offset position,
    Paint paint,
  ) {
    canvas.drawLine(position, Offset(position.dx + 30, position.dy), paint);
    canvas.drawLine(position, Offset(position.dx, position.dy + 30), paint);
  }

  @override
  bool shouldRepaint(_CircuitPainter oldDelegate) => false;
}
