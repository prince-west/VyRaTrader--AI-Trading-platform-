// lib/widgets/performance_chart.dart
import 'package:flutter/material.dart';
import 'dart:math' as math;

class PerformanceChart extends StatefulWidget {
  final double height;
  final List<double>? data;
  final Color glowColor;
  final String title;
  final String subtitle;

  const PerformanceChart({
    super.key,
    this.height = 140,
    this.data,
    this.glowColor = const Color(0xFF00FFFF),
    this.title = 'Portfolio Growth',
    this.subtitle = '30 Days',
  });

  @override
  State<PerformanceChart> createState() => _PerformanceChartState();
}

class _PerformanceChartState extends State<PerformanceChart>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  List<double> _chartData = [];
  int? _hoveredIndex;

  @override
  void initState() {
    super.initState();

    // Generate sample data if none provided
    _chartData = widget.data ?? _generateSampleData();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  List<double> _generateSampleData() {
    final random = math.Random();
    double value = 100.0;
    return List.generate(30, (index) {
      value += (random.nextDouble() - 0.45) * 8;
      return math.max(85, math.min(125, value));
    });
  }

  @override
  Widget build(BuildContext context) {
    final minValue = _chartData.reduce(math.min);
    final maxValue = _chartData.reduce(math.max);
    final range = maxValue - minValue;
    final currentValue = _chartData.last;
    final previousValue = _chartData[_chartData.length - 2];
    final change = currentValue - previousValue;
    final changePercent = (change / previousValue) * 100;
    final isPositive = change >= 0;

    return Container(
      height: widget.height,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [widget.glowColor.withOpacity(0.08), Colors.transparent],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: widget.glowColor.withOpacity(0.3), width: 1),
        boxShadow: [
          BoxShadow(
            color: widget.glowColor.withOpacity(0.15),
            blurRadius: 12,
            spreadRadius: 0,
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with title and stats
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.title,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.9),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    widget.subtitle,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 11,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: (isPositive ? Colors.green : Colors.red).withOpacity(
                    0.15,
                  ),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: (isPositive ? Colors.green : Colors.red).withOpacity(
                      0.4,
                    ),
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isPositive ? Icons.trending_up : Icons.trending_down,
                      color: isPositive ? Colors.green : Colors.red,
                      size: 14,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${isPositive ? '+' : ''}${changePercent.toStringAsFixed(2)}%',
                      style: TextStyle(
                        color: isPositive ? Colors.green : Colors.red,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Chart area
          Expanded(
            child: AnimatedBuilder(
              animation: _animation,
              builder: (context, child) {
                return CustomPaint(
                  size: Size.infinite,
                  painter: _ChartPainter(
                    data: _chartData,
                    minValue: minValue,
                    maxValue: maxValue,
                    range: range,
                    glowColor: widget.glowColor,
                    progress: _animation.value,
                    hoveredIndex: _hoveredIndex,
                  ),
                );
              },
            ),
          ),

          // Optional: Add touch detection
          Positioned.fill(
            child: GestureDetector(
              onPanUpdate: (details) {
                final RenderBox box = context.findRenderObject() as RenderBox;
                final localPosition = box.globalToLocal(details.globalPosition);
                final chartWidth = box.size.width - 32; // padding
                final segmentWidth = chartWidth / (_chartData.length - 1);
                final index = (localPosition.dx - 16) ~/ segmentWidth;

                if (index >= 0 && index < _chartData.length) {
                  setState(() => _hoveredIndex = index);
                }
              },
              onPanEnd: (_) => setState(() => _hoveredIndex = null),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartPainter extends CustomPainter {
  final List<double> data;
  final double minValue;
  final double maxValue;
  final double range;
  final Color glowColor;
  final double progress;
  final int? hoveredIndex;

  _ChartPainter({
    required this.data,
    required this.minValue,
    required this.maxValue,
    required this.range,
    required this.glowColor,
    required this.progress,
    this.hoveredIndex,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty || range == 0) return;

    final paint = Paint()
      ..color = glowColor
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final glowPaint = Paint()
      ..color = glowColor.withOpacity(0.3)
      ..strokeWidth = 6
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    final fillPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          glowColor.withOpacity(0.3),
          glowColor.withOpacity(0.05),
          Colors.transparent,
        ],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    // Calculate points
    final points = <Offset>[];
    final segmentWidth = size.width / (data.length - 1);

    for (int i = 0; i < data.length; i++) {
      final normalizedValue = (data[i] - minValue) / range;
      final x = i * segmentWidth;
      final y = size.height - (normalizedValue * size.height);
      points.add(Offset(x, y));
    }

    // Draw with animation
    final animatedLength = (points.length * progress).round();
    if (animatedLength < 2) return;

    final animatedPoints = points.sublist(0, animatedLength);

    // Draw gradient fill
    final fillPath = Path();
    fillPath.moveTo(animatedPoints.first.dx, size.height);
    for (final point in animatedPoints) {
      fillPath.lineTo(point.dx, point.dy);
    }
    fillPath.lineTo(animatedPoints.last.dx, size.height);
    fillPath.close();
    canvas.drawPath(fillPath, fillPaint);

    // Draw glow line
    final glowPath = Path();
    glowPath.moveTo(animatedPoints.first.dx, animatedPoints.first.dy);
    for (int i = 1; i < animatedPoints.length; i++) {
      glowPath.lineTo(animatedPoints[i].dx, animatedPoints[i].dy);
    }
    canvas.drawPath(glowPath, glowPaint);

    // Draw main line
    final linePath = Path();
    linePath.moveTo(animatedPoints.first.dx, animatedPoints.first.dy);
    for (int i = 1; i < animatedPoints.length; i++) {
      linePath.lineTo(animatedPoints[i].dx, animatedPoints[i].dy);
    }
    canvas.drawPath(linePath, paint);

    // Draw data points
    final dotPaint = Paint()
      ..color = glowColor
      ..style = PaintingStyle.fill;

    final dotGlowPaint = Paint()
      ..color = glowColor.withOpacity(0.5)
      ..style = PaintingStyle.fill
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

    for (int i = 0; i < animatedPoints.length; i++) {
      if (i == animatedPoints.length - 1 || i == hoveredIndex) {
        // Draw glow
        canvas.drawCircle(animatedPoints[i], 6, dotGlowPaint);
        // Draw dot
        canvas.drawCircle(animatedPoints[i], 4, dotPaint);
        // Draw center
        canvas.drawCircle(animatedPoints[i], 2, Paint()..color = Colors.white);
      }
    }

    // Draw hovered value indicator
    if (hoveredIndex != null && hoveredIndex! < animatedPoints.length) {
      final point = animatedPoints[hoveredIndex!];
      final value = data[hoveredIndex!];

      final textPainter = TextPainter(
        text: TextSpan(
          text: value.toStringAsFixed(2),
          style: TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.bold,
            shadows: [Shadow(color: Colors.black54, blurRadius: 4)],
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      final tooltipPadding = 6.0;
      final tooltipRect = Rect.fromLTWH(
        point.dx - textPainter.width / 2 - tooltipPadding,
        point.dy - textPainter.height - tooltipPadding - 10,
        textPainter.width + tooltipPadding * 2,
        textPainter.height + tooltipPadding * 2,
      );

      canvas.drawRRect(
        RRect.fromRectAndRadius(tooltipRect, const Radius.circular(6)),
        Paint()..color = glowColor.withOpacity(0.9),
      );

      textPainter.paint(
        canvas,
        Offset(
          point.dx - textPainter.width / 2,
          point.dy - textPainter.height - 10,
        ),
      );
    }
  }

  @override
  bool shouldRepaint(_ChartPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.hoveredIndex != hoveredIndex ||
      oldDelegate.data != data;
}
