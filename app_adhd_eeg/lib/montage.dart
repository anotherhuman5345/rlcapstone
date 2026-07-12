import 'package:flutter/material.dart';

import 'samples.dart';

/// Draws all 19 EEG channels stacked, like a clinical montage.
class MontagePainter extends CustomPainter {
  MontagePainter({
    required this.signal,
    required this.trace,
    required this.grid,
    required this.label,
  });

  final List<List<double>> signal; // [19][256]
  final Color trace;
  final Color grid;
  final Color label;

  @override
  void paint(Canvas canvas, Size size) {
    final n = signal.length;
    if (n == 0) return;
    final rowH = size.height / n;
    const leftPad = 30.0;
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    final tracePaint = Paint()
      ..color = trace
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final tp = TextPainter(textDirection: TextDirection.ltr);
    for (var c = 0; c < n; c++) {
      final yMid = rowH * (c + 0.5);
      canvas.drawLine(Offset(leftPad, yMid), Offset(size.width, yMid), gridPaint);

      tp.text = TextSpan(
        text: c < channelNames.length ? channelNames[c] : '',
        style: TextStyle(color: label, fontSize: 9),
      );
      tp.layout();
      tp.paint(canvas, Offset(2, yMid - tp.height / 2));

      final ch = signal[c];
      var min = ch.first, max = ch.first;
      for (final v in ch) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
      final range = (max - min).abs() < 1e-6 ? 1.0 : max - min;
      final amp = rowH * 0.42;
      final path = Path();
      for (var i = 0; i < ch.length; i++) {
        final x = leftPad + (i / (ch.length - 1)) * (size.width - leftPad);
        final y = yMid - ((ch[i] - min) / range - 0.5) * 2 * amp;
        i == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }
      canvas.drawPath(path, tracePaint);
    }
  }

  @override
  bool shouldRepaint(covariant MontagePainter old) =>
      old.signal != signal || old.trace != trace;
}
