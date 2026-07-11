import 'dart:io';

import 'package:flutter/material.dart';

import 'classifier.dart';

/// Shows the captured image, the model's estimate, and a prominent reminder
/// that this is not a diagnosis.
class ResultScreen extends StatelessWidget {
  const ResultScreen({
    super.key,
    required this.imageFile,
    required this.result,
  });

  final File imageFile;
  final Classification result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final concerning = result.isConcerning;
    final accent = concerning ? const Color(0xFFC62828) : const Color(0xFF2E7D32);
    final pct = (result.malignantProb * 100).round();

    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.file(
                  imageFile,
                  height: 240,
                  fit: BoxFit.cover,
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
                    Icon(
                      concerning
                          ? Icons.warning_amber_rounded
                          : Icons.check_circle_outline,
                      color: accent,
                      size: 48,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      concerning
                          ? 'Features that may warrant a check'
                          : 'Likely benign features',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.titleLarge
                          ?.copyWith(color: accent, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 16),
                    _ProbBar(malignantProb: result.malignantProb, accent: accent),
                    const SizedBox(height: 12),
                    Text(
                      'Estimated malignant likelihood: $pct%',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
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
                        concerning
                            ? 'This does NOT mean you have cancer. Many benign '
                                'moles look concerning to an AI. Please have a '
                                'dermatologist examine it.'
                            : 'A "likely benign" result does not rule out a '
                                'problem. If this mole is new, changing, itching, '
                                'or bleeding, see a dermatologist regardless.',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Educational tool only — not a medical diagnosis. '
                'The model can be wrong in both directions.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Check another'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProbBar extends StatelessWidget {
  const _ProbBar({required this.malignantProb, required this.accent});

  final double malignantProb;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: LinearProgressIndicator(
        value: malignantProb.clamp(0.0, 1.0),
        minHeight: 14,
        backgroundColor: const Color(0xFF2E7D32).withValues(alpha: 0.25),
        valueColor: AlwaysStoppedAnimation(accent),
      ),
    );
  }
}
