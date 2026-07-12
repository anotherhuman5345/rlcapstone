import 'package:flutter/material.dart';

/// A simple price sparkline.
class SparklinePainter extends CustomPainter {
  SparklinePainter({required this.closes, required this.color});

  final List<double> closes;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (closes.length < 2) return;
    var min = closes.first, max = closes.first;
    for (final c in closes) {
      if (c < min) min = c;
      if (c > max) max = c;
    }
    final range = (max - min).abs() < 1e-9 ? 1.0 : max - min;
    const pad = 8.0;
    final path = Path();
    for (var i = 0; i < closes.length; i++) {
      final x = pad + (i / (closes.length - 1)) * (size.width - 2 * pad);
      final y = pad + (1 - (closes[i] - min) / range) * (size.height - 2 * pad);
      i == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(covariant SparklinePainter old) =>
      old.closes != closes || old.color != color;
}
