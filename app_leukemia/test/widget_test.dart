// Lightweight test that avoids native plugins so it runs in the Dart test VM.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:leukemia_check/samples.dart';

void main() {
  test('cell class display names cover all four classes', () {
    for (final c in ['benign', 'early', 'pre', 'pro']) {
      expect(cellClassName.containsKey(c), isTrue);
    }
  });

  testWidgets('a plain scaffold builds', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: Center(child: Text('ok')))),
    );
    expect(find.text('ok'), findsOneWidget);
  });
}
