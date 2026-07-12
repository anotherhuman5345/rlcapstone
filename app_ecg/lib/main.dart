import 'package:flutter/material.dart';

import 'classifier.dart';
import 'onboarding_screen.dart';
import 'result_screen.dart';
import 'samples.dart';
import 'waveform.dart';

void main() => runApp(const EcgApp());

class EcgApp extends StatelessWidget {
  const EcgApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ECG Check',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFFC62828),
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFFC62828),
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
  Future<EcgClassifier>? _classifierFuture;
  List<BeatSample> _samples = [];
  BeatSample? _selected;
  bool _busy = false;

  Future<EcgClassifier> _classifier() =>
      _classifierFuture ??= EcgClassifier.load();

  @override
  void initState() {
    super.initState();
    loadSamples().then((s) {
      if (mounted) setState(() => _samples = s);
    });
  }

  Future<void> _analyse(BeatSample sample) async {
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
        SnackBar(content: Text('Could not analyse beat: $e')),
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
      appBar: AppBar(title: const Text('ECG Check'), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.monitor_heart_outlined,
                  size: 56, color: theme.colorScheme.primary),
              const SizedBox(height: 12),
              Text('Pick a heartbeat',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(
                'Each beat is real ECG data from the MIT-BIH database, from '
                'patients the model never trained on. Tap one to classify it '
                'on your device.',
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
                  children: [
                    for (final s in _samples)
                      _BeatChip(
                        label: '${s.trueClass} · beat '
                            '${counts[s.trueClass] = (counts[s.trueClass] ?? 0) + 1}',
                        tooltip: beatClassName[s.trueClass] ?? s.trueClass,
                        selected: identical(_selected, s),
                        onTap: _busy ? null : () => _analyse(s),
                      ),
                  ],
                ),
              const SizedBox(height: 20),
              if (_selected != null)
                AspectRatio(
                  aspectRatio: 3,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      border:
                          Border.all(color: theme.colorScheme.outlineVariant),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: CustomPaint(
                      painter: WaveformPainter(
                        signal: _selected!.signal,
                        color: theme.colorScheme.primary,
                        grid: theme.colorScheme.outlineVariant
                            .withValues(alpha: 0.4),
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
              const _Disclaimer(),
            ],
          ),
        ),
      ),
    );
  }
}

class _BeatChip extends StatelessWidget {
  const _BeatChip({
    required this.label,
    required this.tooltip,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String tooltip;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: onTap == null ? null : (_) => onTap!(),
      ),
    );
  }
}

class _Disclaimer extends StatelessWidget {
  const _Disclaimer();

  @override
  Widget build(BuildContext context) {
    return Text(
      'Educational tool only — not a medical device and not a diagnosis. '
      'It classifies pre-recorded research beats and cannot read your own ECG.',
      textAlign: TextAlign.center,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
  }
}
