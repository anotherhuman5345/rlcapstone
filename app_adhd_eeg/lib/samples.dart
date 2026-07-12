import 'dart:convert';

import 'package:flutter/services.dart';

/// A pre-recorded 19-channel EEG window from an unseen subject, with the
/// study group it belongs to.
class EegSample {
  const EegSample({
    required this.id,
    required this.trueClass,
    required this.subject,
    required this.signal, // [channels][time] = [19][256]
  });

  final String id;
  final String trueClass;
  final String subject;
  final List<List<double>> signal;
}

const channelNames = [
  'Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2',
  'F7', 'F8', 'T7', 'T8', 'P7', 'P8', 'Fz', 'Cz', 'Pz',
];

Future<List<EegSample>> loadSamples() async {
  final raw = await rootBundle.loadString('assets/adhd_samples.json');
  final data = jsonDecode(raw) as Map<String, dynamic>;
  final list = (data['samples'] as List).cast<Map<String, dynamic>>();
  return [
    for (final s in list)
      EegSample(
        id: s['id'] as String,
        trueClass: s['trueClass'] as String,
        subject: (s['subject'] ?? '') as String,
        signal: (s['signal'] as List)
            .map((ch) => (ch as List).map((v) => (v as num).toDouble()).toList())
            .toList(),
      ),
  ];
}
