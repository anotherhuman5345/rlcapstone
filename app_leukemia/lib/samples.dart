import 'dart:convert';

import 'package:flutter/services.dart';

/// A bundled blood-smear cell image with its true class.
class CellSample {
  const CellSample({required this.file, required this.trueClass, this.source});
  final String file;
  final String trueClass;
  final String? source; // which lab the cell came from (Delhi / Tehran / Barcelona)

  String get assetPath => 'assets/cells/$file';
  Future<Uint8List> bytes() async =>
      (await rootBundle.load(assetPath)).buffer.asUint8List();
}

const cellClassName = {
  'all': 'Leukemic (B-ALL blast)',
  'hem': 'Normal cell',
};

Future<List<CellSample>> loadSamples() async {
  final raw = await rootBundle.loadString('assets/leukemia_samples.json');
  final data = jsonDecode(raw) as Map<String, dynamic>;
  final list = (data['samples'] as List).cast<Map<String, dynamic>>();
  return [
    for (final s in list)
      CellSample(
        file: s['file'] as String,
        trueClass: s['trueClass'] as String,
        source: s['source'] as String?,
      ),
  ];
}
