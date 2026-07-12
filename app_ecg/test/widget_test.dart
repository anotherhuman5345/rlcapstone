// Lightweight tests that don't depend on native plugins (TFLite /
// shared_preferences), so they run in the pure-Dart test VM.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ecg_check/waveform.dart';

void main() {
  testWidgets('waveform paints without error', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomPaint(
            painter: WaveformPainter(
              signal: List<double>.generate(260, (i) => (i % 20) / 20 - 0.5),
              color: const Color(0xFFC62828),
              grid: const Color(0x33000000),
            ),
            child: const SizedBox(width: 300, height: 100),
          ),
        ),
      ),
    );
    expect(find.byType(CustomPaint), findsWidgets);
  });
}
