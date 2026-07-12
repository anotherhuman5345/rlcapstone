import 'package:flutter/material.dart';

/// Draws a single ECG beat waveform on a faint grid, ECG-paper style.
class WaveformPainter extends CustomPainter {
  WaveformPainter({required this.signal, required this.color, required this.grid});

  final List<double> signal;
  final Color color;
  final Color grid;

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    const cols = 26, rows = 8;
    for (var i = 0; i <= cols; i++) {
      final x = size.width * i / cols;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (var i = 0; i <= rows; i++) {
      final y = size.height * i / rows;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    if (signal.isEmpty) return;
    var min = signal.first, max = signal.first;
    for (final v in signal) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
    final range = (max - min).abs() < 1e-6 ? 1.0 : max - min;
    const pad = 12.0;

    final path = Path();
    for (var i = 0; i < signal.length; i++) {
      final x = size.width * i / (signal.length - 1);
      final y = pad + (1 - (signal[i] - min) / range) * (size.height - 2 * pad);
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
  bool shouldRepaint(covariant WaveformPainter old) =>
      old.signal != signal || old.color != color || old.grid != grid;
}
