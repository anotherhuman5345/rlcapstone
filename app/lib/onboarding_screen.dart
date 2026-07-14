import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _seenKey = 'onboarding_seen_v1';

/// Returns true if onboarding has already been completed.
Future<bool> onboardingSeen() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getBool(_seenKey) ?? false;
}

Future<void> _markSeen() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool(_seenKey, true);
}

/// Three-slide first-run flow: welcome, photo tips, and an explicit medical
/// disclaimer the user must acknowledge before using the app.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key, required this.onDone});

  final VoidCallback onDone;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  static const _slides = [
    _Slide(
      icon: Icons.health_and_safety_outlined,
      title: 'Welcome to MoleCheck',
      body: 'Take a photo of a mole and an AI model estimates whether it looks '
          'benign or worth getting checked — running entirely on your phone, '
          'so your photo never leaves the device.',
    ),
    _Slide(
      icon: Icons.center_focus_strong_outlined,
      title: 'Take a good photo',
      body: 'Fill the frame with one mole. Use bright, even lighting and avoid '
          'shadows. Hold steady and keep the mole in sharp focus. Better photos '
          'give more reliable estimates.',
    ),
    _Slide(
      icon: Icons.info_outline,
      title: 'This is not a diagnosis',
      body: 'MoleCheck is an educational tool, not a medical device. It can be '
          'wrong in both directions. Always consult a dermatologist about any '
          'new, changing, or concerning skin lesion.',
      accent: true,
    ),
  ];

  Future<void> _finish() async {
    await _markSeen();
    widget.onDone();
  }

  // "Skip" jumps to the final slide (the medical disclaimer) rather than
  // finishing — the disclaimer must still be acknowledged before the app opens.
  void _skipToDisclaimer() {
    _controller.animateToPage(
      _slides.length - 1,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _page == _slides.length - 1;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: isLast ? null : _skipToDisclaimer,
                child: Opacity(opacity: isLast ? 0 : 1, child: const Text('Skip')),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _slides.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) => _slides[i],
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _slides.length,
                (i) => AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.all(4),
                  width: i == _page ? 22 : 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: i == _page
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.outlineVariant,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  onPressed: () {
                    if (isLast) {
                      _finish();
                    } else {
                      _controller.nextPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeOut,
                      );
                    }
                  },
                  child: Text(isLast ? 'I understand — get started' : 'Next'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Slide extends StatelessWidget {
  const _Slide({
    required this.icon,
    required this.title,
    required this.body,
    this.accent = false,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = accent ? const Color(0xFFC62828) : theme.colorScheme.primary;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 96, color: color),
          const SizedBox(height: 32),
          Text(
            title,
            textAlign: TextAlign.center,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: accent ? color : null,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            body,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
