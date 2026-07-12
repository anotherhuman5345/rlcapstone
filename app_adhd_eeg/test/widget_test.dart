// Lightweight test that avoids native plugins so it runs in the Dart test VM.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:adhd_eeg/montage.dart';

void main() {
  testWidgets('EEG montage paints without error', (tester) async {
    final signal = List.generate(
      19,
      (c) => List<double>.generate(256, (i) => ((i + c) % 40) / 40 - 0.5),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomPaint(
            painter: MontagePainter(
              signal: signal,
              trace: const Color(0xFF7C3AED),
              grid: const Color(0x33000000),
              label: const Color(0xFF888888),
            ),
            child: const SizedBox(width: 300, height: 380),
          ),
        ),
      ),
    );
    expect(find.byType(CustomPaint), findsWidgets);
  });
}
