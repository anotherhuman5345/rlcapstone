import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

class EegResult {
  const EegResult({required this.labels, required this.probs});
  final List<String> labels;
  final List<double> probs;

  int get topIndex => probs[1] >= probs[0] ? 1 : 0;
  String get topLabel => labels[topIndex];
  double get topProb => probs[topIndex];
}

/// Wraps the on-device ADHD/Control EEG classifier. The TFLite model expects a
/// [1, 256, 19] input (onnx2tf makes it channels-last), so a [19][256] window
/// is transposed to [time][channel] before inference. Emits 2 logits; softmax
/// is applied here. Classes: [Control, ADHD].
class EegClassifier {
  EegClassifier._(this._interpreter, this._labels, this._time, this._ch);

  final Interpreter _interpreter;
  final List<String> _labels;
  final int _time; // 256
  final int _ch;   // 19

  List<String> get labels => List.unmodifiable(_labels);

  static Future<EegClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(
      'assets/adhd_classifier.tflite',
    );
    final labelsRaw = await rootBundle.loadString('assets/labels.txt');
    final labels = labelsRaw
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    final shape = interpreter.getInputTensor(0).shape; // [1, 256, 19]
    final time = shape.length >= 2 ? shape[1] : 256;
    final ch = shape.length >= 3 ? shape[2] : 19;
    return EegClassifier._(interpreter, labels, time, ch);
  }

  /// signal: [channels][time] (19 x 256), already z-normalised per channel.
  EegResult run(List<List<double>> signal) {
    // Build [1, time, ch] by transposing.
    final input = [
      [
        for (var t = 0; t < _time; t++)
          [for (var c = 0; c < _ch; c++) signal[c][t]],
      ],
    ];
    final output = List.filled(
      _labels.length,
      0.0,
    ).reshape([1, _labels.length]);
    _interpreter.run(input, output);
    return EegResult(
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
