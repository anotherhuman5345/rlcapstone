import 'package:flutter/material.dart';

import 'classifier.dart';
import 'samples.dart';

/// Shows the chosen cell, the model's call vs. the true class, per-class
/// confidence, and an honest caveat.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.sample, required this.result});

  final CellSample sample;
  final CellResult result;

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
              Center(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.asset(sample.assetPath,
                      width: 200, height: 200, fit: BoxFit.cover),
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
                    Text('Model says: ${cellClassName[predClass] ?? predClass}',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleLarge
                            ?.copyWith(color: accent, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(
                      'True label: ${cellClassName[sample.trueClass] ?? sample.trueClass}'
                      '${sample.source != null ? ' · from ${sample.source}' : ''}'
                      '  —  ${correct ? 'model agrees' : 'model is wrong'}',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text('Confidence per class', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              for (var i = 0; i < result.labels.length; i++)
                _ProbRow(
                  label: cellClassName[result.labels[i]] ?? result.labels[i],
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
                        'This v3 model is trained on cells from multiple labs, so it generalizes '
                        'across microscopes far better than a single-source model — but it is still '
                        'imperfect. It is a teaching example of image classification, never a diagnosis.',
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
                label: const Text('Try another cell'),
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
            width: 130,
            child: Text(label,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
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
            width: 40,
            child: Text('${(prob * 100).round()}%',
                textAlign: TextAlign.right, style: theme.textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}
