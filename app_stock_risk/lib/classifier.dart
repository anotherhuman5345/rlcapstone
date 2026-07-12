import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

class RiskResult {
  const RiskResult({required this.labels, required this.probs});
  final List<String> labels;
  final List<double> probs;

  int get topIndex {
    var best = 0;
    for (var i = 1; i < probs.length; i++) {
      if (probs[i] > probs[best]) best = i;
    }
    return best;
  }

  String get topLabel => labels[topIndex];
  double get topProb => probs[topIndex];
}

/// Wraps the on-device stock-risk classifier. The TFLite model takes a [1,12]
/// feature vector (already normalised at prep time) and emits 3 logits;
/// softmax here. Classes: [Low, Medium, High].
class RiskClassifier {
  RiskClassifier._(this._interpreter, this._labels, this._nFeat);

  final Interpreter _interpreter;
  final List<String> _labels;
  final int _nFeat;

  List<String> get labels => List.unmodifiable(_labels);

  static Future<RiskClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(
      'assets/stock_classifier.tflite',
    );
    final labelsRaw = await rootBundle.loadString('assets/labels.txt');
    final labels = labelsRaw
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    final shape = interpreter.getInputTensor(0).shape; // [1, 12]
    final n = shape.length >= 2 ? shape[1] : 12;
    return RiskClassifier._(interpreter, labels, n);
  }

  RiskResult run(List<double> features) {
    if (features.length != _nFeat) {
      throw ArgumentError('Expected $_nFeat features, got ${features.length}');
    }
    final input = [List<double>.from(features)];
    final output = List.filled(
      _labels.length,
      0.0,
    ).reshape([1, _labels.length]);
    _interpreter.run(input, output);
    return RiskResult(
      labels: _labels,
      probs: _softmax((output[0] as List).cast<double>()),
    );
  }

  List<double> _softmax(List<double> v) {
    final m = v.reduce(math.max);
    final e = v.map((x) => math.exp(x - m)).toList();
    final s = e.fold<double>(0, (a, b) => a + b);
    return e.map((x) => x / s).toList();
  }

  void close() => _interpreter.close();
}
