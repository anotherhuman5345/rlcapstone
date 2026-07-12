import 'package:flutter/material.dart';

import 'classifier.dart';
import 'montage.dart';
import 'samples.dart';

/// Shows the EEG montage, the model's call vs. the subject's study group, and
/// per-class confidence with an honest caveat.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.sample, required this.result});

  final EegSample sample;
  final EegResult result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final predClass = result.topLabel;
    final correct = predClass == sample.trueClass;
    final accent = correct ? const Color(0xFF2E7D32) : const Color(0xFFC62828);

    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AspectRatio(
                aspectRatio: 0.9,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: theme.colorScheme.outlineVariant),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(6),
                    child: CustomPaint(
                      painter: MontagePainter(
                        signal: sample.signal,
                        trace: theme.colorScheme.primary,
                        grid: theme.colorScheme.outlineVariant.withValues(alpha: 0.4),
                        label: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: accent.withValues(alpha: 0.5)),
                ),
                child: Column(
                  children: [
                    Icon(correct ? Icons.check_circle_outline : Icons.cancel_outlined,
                        color: accent, size: 44),
                    const SizedBox(height: 12),
                    Text('Model says: $predClass',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleLarge
                            ?.copyWith(color: accent, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(
                      'This recording is from a subject in the '
                      '${sample.trueClass} group  —  '
                      '${correct ? 'model agrees' : 'model is wrong'}',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text('Confidence per group', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              for (var i = 0; i < result.labels.length; i++)
                _ProbRow(
                  label: result.labels[i],
                  prob: result.probs[i],
                  highlight: i == result.topIndex,
                ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline,
                        color: theme.colorScheme.onSurfaceVariant),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'ADHD is diagnosed by clinicians, never from a short EEG. '
                        'This classifies which research group a recording came from, '
                        'on a small cohort — a teaching example, not a diagnosis.',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Try another recording'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProbRow extends StatelessWidget {
  const _ProbRow({
    required this.label,
    required this.prob,
    required this.highlight,
  });

  final String label;
  final double prob;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = highlight
        ? theme.colorScheme.primary
        : theme.colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 64,
            child: Text(label,
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: prob.clamp(0.0, 1.0),
                minHeight: 12,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
                valueColor: AlwaysStoppedAnimation(color),
              ),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 44,
            child: Text('${(prob * 100).round()}%',
                textAlign: TextAlign.right, style: theme.textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}
