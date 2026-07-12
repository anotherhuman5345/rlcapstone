import 'package:flutter/material.dart';

import 'classifier.dart';
import 'samples.dart';
import 'sparkline.dart';

const _riskColor = {
  'Low': Color(0xFF2E7D32),
  'Medium': Color(0xFFB8860B),
  'High': Color(0xFFC0392B),
};

/// Shows the price line, the predicted risk vs. what actually happened, and
/// per-class confidence, with an honest note about the sentiment feature.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.sample, required this.result});

  final StockSample sample;
  final RiskResult result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final predClass = result.topLabel;
    final correct = predClass == sample.trueClass;
    final accent = _riskColor[predClass] ?? theme.colorScheme.primary;
    final senti = sample.sentiment > 0.05
        ? 'positive'
        : sample.sentiment < -0.05
            ? 'negative'
            : 'neutral';

    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('${sample.ticker} · 21 days up to ${sample.date}',
                  style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              AspectRatio(
                aspectRatio: 3.2,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: theme.colorScheme.outlineVariant),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: CustomPaint(
                    painter: SparklinePainter(
                      closes: sample.closes,
                      color: theme.colorScheme.primary,
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
                    Text('Predicted next-week risk: $predClass',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.titleLarge
                            ?.copyWith(color: accent, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(
                      'What actually happened: ${sample.trueClass} volatility  —  '
                      '${correct ? 'model agrees' : 'model was off'}',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'News sentiment that week: $senti '
                '(${sample.sentiment.toStringAsFixed(2)}, ${sample.sentCount} '
                '${sample.sentCount == 1 ? 'article' : 'articles'}). '
                'The model does slightly better without this feature.',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 20),
              Text('Confidence per class', style: theme.textTheme.titleMedium),
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
                        'Educational only — not financial advice and not a '
                        'recommendation. This predicts volatility, not direction, '
                        'and it is right only about half the time.',
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
                label: const Text('Try another'),
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
        ? (_riskColor[label] ?? theme.colorScheme.primary)
        : theme.colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 70,
            child: Text(label,
                style: const TextStyle(fontWeight: FontWeight.w600)),
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
