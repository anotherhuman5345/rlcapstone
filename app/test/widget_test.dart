// Basic smoke test for the MoleCheck home screen.
import 'package:flutter_test/flutter_test.dart';

import 'package:mole_check/main.dart';

void main() {
  testWidgets('Home screen shows capture actions', (WidgetTester tester) async {
    await tester.pumpWidget(const MoleCheckApp());

    expect(find.text('Take a photo'), findsOneWidget);
    expect(find.text('Choose from gallery'), findsOneWidget);
  });
}
