import 'package:flutter/material.dart';

import 'classifier.dart';
import 'montage.dart';
import 'onboarding_screen.dart';
import 'result_screen.dart';
import 'samples.dart';

void main() => runApp(const EegApp());

class EegApp extends StatelessWidget {
  const EegApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EEG Explorer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF7C3AED),
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF7C3AED),
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
  Future<EegClassifier>? _classifierFuture;
  List<EegSample> _samples = [];
  EegSample? _selected;
  bool _busy = false;

  Future<EegClassifier> _classifier() =>
      _classifierFuture ??= EegClassifier.load();

  @override
  void initState() {
    super.initState();
    loadSamples().then((s) {
      if (mounted) setState(() => _samples = s);
    });
  }

  Future<void> _analyse(EegSample sample) async {
    if (_busy) return;
    setState(() {
      _selected = sample;
      _busy = true;
    });
    try {
      final classifier = await _classifier();
      final result = classifier.run(sample.signal);
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
        SnackBar(content: Text('Could not analyse recording: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final counts = <String, int>{};
    return Scaffold(
      appBar: AppBar(title: const Text('EEG Explorer'), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.psychology_outlined,
                  size: 56, color: theme.colorScheme.primary),
              const SizedBox(height: 12),
              Text('Pick a recording',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(
                'Each is a real 19-channel EEG window from a child the model '
                'never trained on. Tap one to classify it on your device.',
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
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.center,
                  children: [
                    for (final s in _samples)
                      ChoiceChip(
                        label: Text('${s.trueClass} · rec '
                            '${counts[s.trueClass] = (counts[s.trueClass] ?? 0) + 1}'),
                        selected: identical(_selected, s),
                        onSelected: _busy ? null : (_) => _analyse(s),
                      ),
                  ],
                ),
              const SizedBox(height: 20),
              if (_selected != null)
                AspectRatio(
                  aspectRatio: 0.9,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      border:
                          Border.all(color: theme.colorScheme.outlineVariant),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(6),
                      child: CustomPaint(
                        painter: MontagePainter(
                          signal: _selected!.signal,
                          trace: theme.colorScheme.primary,
                          grid: theme.colorScheme.outlineVariant
                              .withValues(alpha: 0.4),
                          label: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ),
                ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: LinearProgressIndicator(),
                ),
              const SizedBox(height: 20),
              Text(
                'Educational tool only — not a medical device and not a diagnosis. '
                'It classifies pre-recorded research EEG and cannot read your brain.',
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
