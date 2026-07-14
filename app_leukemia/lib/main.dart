import 'package:flutter/material.dart';

import 'classifier.dart';
import 'onboarding_screen.dart';
import 'result_screen.dart';
import 'samples.dart';

void main() => runApp(const LeukemiaApp());

class LeukemiaApp extends StatelessWidget {
  const LeukemiaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cell Explorer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFFAD1457),
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFFAD1457),
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const _Root(),
    );
  }
}

class _Root extends StatefulWidget {
  const _Root();

  @override
  State<_Root> createState() => _RootState();
}

class _RootState extends State<_Root> {
  bool? _seen;

  @override
  void initState() {
    super.initState();
    onboardingSeen().then((v) {
      if (mounted) setState(() => _seen = v);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_seen == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!_seen!) {
      return OnboardingScreen(onDone: () => setState(() => _seen = true));
    }
    return const HomeScreen();
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Future<CellClassifier>? _classifierFuture;
  List<CellSample> _samples = [];
  CellSample? _selected;
  bool _busy = false;

  Future<CellClassifier> _classifier() =>
      _classifierFuture ??= CellClassifier.load();

  @override
  void initState() {
    super.initState();
    loadSamples().then((s) {
      if (mounted) setState(() => _samples = s);
    });
  }

  Future<void> _analyse(CellSample sample) async {
    if (_busy) return;
    setState(() {
      _selected = sample;
      _busy = true;
    });
    try {
      final classifier = await _classifier();
      final bytes = await sample.bytes();
      final result = classifier.run(bytes);
      if (!mounted) return;
      await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ResultScreen(sample: sample, result: result),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not analyse cell: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Cell Explorer'), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.biotech_outlined,
                  size: 56, color: theme.colorScheme.primary),
              const SizedBox(height: 12),
              Text('Pick a cell',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(
                'Each is a real single-cell image from one of three labs. '
                'Tap one to classify it as leukemic or normal on your device.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 20),
              if (_samples.isEmpty)
                const Center(
                    child: Padding(
                        padding: EdgeInsets.all(24),
                        child: CircularProgressIndicator()))
              else
                GridView.count(
                  crossAxisCount: 4,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  children: [
                    for (final s in _samples)
                      GestureDetector(
                        onTap: _busy ? null : () => _analyse(s),
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: identical(_selected, s)
                                  ? theme.colorScheme.primary
                                  : theme.colorScheme.outlineVariant,
                              width: identical(_selected, s) ? 2 : 1,
                            ),
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: Image.asset(s.assetPath, fit: BoxFit.cover),
                        ),
                      ),
                  ],
                ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: LinearProgressIndicator(),
                ),
              const SizedBox(height: 20),
              Text(
                'Educational tool only — not a medical device and not a diagnosis. '
                'It classifies pre-recorded research images; even trained on multiple '
                'labs the model is imperfect.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
