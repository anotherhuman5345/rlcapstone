import 'dart:convert';

import 'package:flutter/services.dart';

/// A pre-recorded MIT-BIH heartbeat bundled with the app, with the
/// cardiologist's true label. From patients the model never trained on.
class BeatSample {
  const BeatSample({
    required this.id,
    required this.trueClass,
    required this.signal,
  });

  final String id;
  final String trueClass;
  final List<double> signal;
}

/// Full names for the four AAMI beat classes.
const beatClassName = {
  'N': 'Normal beat',
  'S': 'Supraventricular (early) beat',
  'V': 'Ventricular ectopic beat',
  'F': 'Fusion beat',
};

Future<List<BeatSample>> loadSamples() async {
  final raw = await rootBundle.loadString('assets/ecg_samples.json');
  final data = jsonDecode(raw) as Map<String, dynamic>;
  final list = (data['samples'] as List).cast<Map<String, dynamic>>();
  return [
    for (final s in list)
      BeatSample(
        id: s['id'] as String,
        trueClass: s['trueClass'] as String,
        signal: (s['signal'] as List).map((v) => (v as num).toDouble()).toList(),
      ),
  ];
}
