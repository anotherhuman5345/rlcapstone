// Smoke tests for MoleCheck.
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mole_check/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Shows home screen once onboarding is seen',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({'onboarding_seen_v1': true});
    await tester.pumpWidget(const MoleCheckApp());
    await tester.pumpAndSettle();

    expect(find.text('Take a photo'), findsOneWidget);
    expect(find.text('Choose from gallery'), findsOneWidget);
  });

  testWidgets('Shows onboarding on first run', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const MoleCheckApp());
    await tester.pumpAndSettle();

    expect(find.text('Welcome to MoleCheck'), findsOneWidget);
  });
}
