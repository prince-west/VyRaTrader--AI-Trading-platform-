// lib/widgets/risk_meter.dart
import 'package:flutter/material.dart';
import 'dart:math' as math;

class RiskMeter extends StatefulWidget {
  final ValueChanged<String>? onRiskChanged;
  final double initialValue;
  final bool showExpectedReturn;

  const RiskMeter({
    super.key,
    this.onRiskChanged,
    this.initialValue = 1.0,
    this.showExpectedReturn = true,
  });

  @override
  State<RiskMeter> createState() => _RiskMeterState();
}

class _RiskMeterState extends State<RiskMeter> with TickerProviderStateMixin {
  late double _val;
  late AnimationController _pulseController;
  late AnimationController _particleController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _val = widget.initialValue;

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();

    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  String get _label {
    if (_val < 0.5) return 'Low';
    if (_val < 1.5) return 'Medium';
    return 'High';
  }

  Color get _riskColor {
    if (_val < 0.5) return const Color(0xFF00FF88); // Green
    if (_val < 1.5) return const Color(0xFF00FFFF); // Cyan
    return const Color(0xFFFF0080); // Pink/Red
  }

  String get _expectedReturn {
    if (_val < 0.5) return '0.5% - 2%';
    if (_val < 1.5) return '2% - 4%';
    return '5%+';
  }

  String get _volatility {
    if (_val < 0.5) return '10%';
    if (_val < 1.5) return '25%';
    return '60%';
  }

  String get _stopLoss {
    if (_val < 0.5) return '2-3%';
    if (_val < 1.5) return '5-8%';
    return '10-20%';
  }

  IconData get _riskIcon {
    if (_val < 0.5) return Icons.shield_outlined;
    if (_val < 1.5) return Icons.show_chart;
    return Icons.bolt;
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_pulseController, _particleController]),
      builder: (context, child) {
        return Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [_riskColor.withOpacity(0.1), Colors.transparent],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: _riskColor.withOpacity(_pulseAnimation.value * 0.6),
              width: 2,
            ),
            boxShadow: [
              BoxShadow(
                color: _riskColor.withOpacity(_pulseAnimation.value * 0.3),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with icon and label
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              _riskColor.withOpacity(0.4),
                              _riskColor.withOpacity(0.1),
                            ],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: _riskColor.withOpacity(0.5),
                              blurRadius: 12,
                              spreadRadius: 2,
                            ),
                          ],
                        ),
                        child: Icon(_riskIcon, color: _riskColor, size: 24),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'RISK LEVEL',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.5),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _label.toUpperCase(),
                            style: TextStyle(
                              color: _riskColor,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.2,
                              shadows: [
                                Shadow(
                                  color: _riskColor.withOpacity(0.8),
                                  blurRadius: 12,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  // Risk indicator badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: _riskColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _riskColor.withOpacity(0.5),
                        width: 1,
                      ),
                    ),
                    child: Text(
                      '${(_val / 2 * 100).toInt()}%',
                      style: TextStyle(
                        color: _riskColor,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // Custom animated slider
              SizedBox(
                height: 60,
                child: Stack(
                  children: [
                    // Background track with particles
                    Positioned.fill(
                      child: CustomPaint(
                        painter: _SliderTrackPainter(
                          progress: _val / 2,
                          color: _riskColor,
                          pulseValue: _pulseAnimation.value,
                          particleProgress: _particleController.value,
                        ),
                      ),
                    ),

                    // Slider
                    SliderTheme(
                      data: SliderThemeData(
                        trackHeight: 8,
                        activeTrackColor: _riskColor.withOpacity(0.8),
                        inactiveTrackColor: Colors.white.withOpacity(0.1),
                        thumbColor: _riskColor,
                        overlayColor: _riskColor.withOpacity(0.3),
                        thumbShape: _GlowingThumbShape(
                          glowColor: _riskColor,
                          pulseValue: _pulseAnimation.value,
                        ),
                        overlayShape: const RoundSliderOverlayShape(
                          overlayRadius: 24,
                        ),
                      ),
                      child: Slider(
                        value: _val,
                        min: 0,
                        max: 2,
                        divisions: 2,
                        onChanged: (v) {
                          setState(() => _val = v);
                          widget.onRiskChanged?.call(_label.toLowerCase());
                        },
                      ),
                    ),
                  ],
                ),
              ),

              // Risk level indicators
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildLevelIndicator('LOW', 0, const Color(0xFF00FF88)),
                    _buildLevelIndicator('MEDIUM', 1, const Color(0xFF00FFFF)),
                    _buildLevelIndicator('HIGH', 2, const Color(0xFFFF0080)),
                  ],
                ),
              ),

              if (widget.showExpectedReturn) ...[
                const SizedBox(height: 20),
                const Divider(color: Colors.white12, height: 1),
                const SizedBox(height: 16),

                // Expected metrics
                _buildMetricRow(
                  'Expected Monthly Return',
                  _expectedReturn,
                  Icons.trending_up,
                ),
                const SizedBox(height: 12),
                _buildMetricRow(
                  'Max Volatile Allocation',
                  _volatility,
                  Icons.show_chart,
                ),
                const SizedBox(height: 12),
                _buildMetricRow('Stop-Loss Range', _stopLoss, Icons.shield),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildLevelIndicator(String label, int level, Color color) {
    final isActive = (_val >= level - 0.5 && _val <= level + 0.5);

    return Column(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: isActive ? color : Colors.white24,
            shape: BoxShape.circle,
            boxShadow: isActive
                ? [BoxShadow(color: color, blurRadius: 8, spreadRadius: 2)]
                : null,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: TextStyle(
            color: isActive ? color : Colors.white24,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: _riskColor.withOpacity(0.7), size: 16),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 12,
            ),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: _riskColor,
            fontSize: 13,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

class _SliderTrackPainter extends CustomPainter {
  final double progress;
  final Color color;
  final double pulseValue;
  final double particleProgress;

  _SliderTrackPainter({
    required this.progress,
    required this.color,
    required this.pulseValue,
    required this.particleProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Draw glow line
    final glowPaint = Paint()
      ..color = color.withOpacity(pulseValue * 0.3)
      ..strokeWidth = 12
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    final trackY = size.height / 2;
    final activeWidth = size.width * progress;

    canvas.drawLine(Offset(0, trackY), Offset(activeWidth, trackY), glowPaint);

    // Draw particles
    final random = math.Random(42);
    for (int i = 0; i < 5; i++) {
      final particleX = (particleProgress + i * 0.2) % 1.0;
      if (particleX < progress) {
        final x = size.width * particleX;
        final offsetY =
            math.sin(particleProgress * math.pi * 2 + i + random.nextDouble()) *
                10;

        final particlePaint = Paint()
          ..color = color.withOpacity(0.6)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

        canvas.drawCircle(Offset(x, trackY + offsetY), 3, particlePaint);
      }
    }
  }

  @override
  bool shouldRepaint(_SliderTrackPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.pulseValue != pulseValue ||
      oldDelegate.particleProgress != particleProgress;
}

class _GlowingThumbShape extends SliderComponentShape {
  final Color glowColor;
  final double pulseValue;

  const _GlowingThumbShape({required this.glowColor, required this.pulseValue});

  @override
  Size getPreferredSize(bool isEnabled, bool isDiscrete) {
    return const Size(32, 32);
  }

  @override
  void paint(
    PaintingContext context,
    Offset center, {
    required Animation<double> activationAnimation,
    required Animation<double> enableAnimation,
    required bool isDiscrete,
    required TextPainter labelPainter,
    required RenderBox parentBox,
    required SliderThemeData sliderTheme,
    required TextDirection textDirection,
    required double value,
    required double textScaleFactor,
    required Size sizeWithOverflow,
  }) {
    final canvas = context.canvas;

    // Outer glow
    final glowPaint = Paint()
      ..color = glowColor.withOpacity(pulseValue * 0.4)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    canvas.drawCircle(center, 20, glowPaint);

    // Middle ring
    final ringPaint = Paint()
      ..color = glowColor.withOpacity(0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawCircle(center, 14, ringPaint);

    // Inner circle
    final innerPaint = Paint()
      ..shader = RadialGradient(
        colors: [glowColor, glowColor.withOpacity(0.6)],
      ).createShader(Rect.fromCircle(center: center, radius: 12));
    canvas.drawCircle(center, 12, innerPaint);

    // Center dot
    final centerPaint = Paint()..color = Colors.white;
    canvas.drawCircle(center, 4, centerPaint);
  }
}
