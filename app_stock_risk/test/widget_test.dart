// Lightweight test that avoids native plugins so it runs in the Dart test VM.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:stock_risk/sparkline.dart';

void main() {
  testWidgets('sparkline paints without error', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomPaint(
            painter: SparklinePainter(
              closes: List<double>.generate(21, (i) => 100 + (i % 5).toDouble()),
              color: const Color(0xFF1565C0),
            ),
            child: const SizedBox(width: 300, height: 60),
          ),
        ),
      ),
    );
    expect(find.byType(CustomPaint), findsWidgets);
  });
}
