import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

/// One classification of a single heartbeat.
class BeatResult {
  const BeatResult({required this.labels, required this.probs});

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

/// Wraps the on-device ECG beat classifier. The TFLite model expects a
/// [1, 260, 1] input (onnx2tf converts the 1-D signal to channels-last) and
/// emits 4 logits; we apply softmax here. Classes: N, S, V, F.
class EcgClassifier {
  EcgClassifier._(this._interpreter, this._labels, this._window);

  final Interpreter _interpreter;
  final List<String> _labels;
  final int _window;

  List<String> get labels => List.unmodifiable(_labels);

  static Future<EcgClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(
      'assets/ecg_classifier.tflite',
    );
    final labelsRaw = await rootBundle.loadString('assets/labels.txt');
    final labels = labelsRaw
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();

    final inShape = interpreter.getInputTensor(0).shape; // [1, 260, 1]
    final window = inShape.length >= 2 ? inShape[1] : 260;
    return EcgClassifier._(interpreter, labels, window);
  }

  int get windowSize => _window;

  /// Classify one beat window (length == windowSize, already z-normalised).
  BeatResult run(List<double> signal) {
    if (signal.length != _window) {
      throw ArgumentError(
        'Expected $_window samples, got ${signal.length}',
      );
    }
    // [1, window, 1]
    final input = [
      [for (final v in signal) [v]],
    ];
    final output = List.filled(
      _labels.length,
      0.0,
    ).reshape([1, _labels.length]);
    _interpreter.run(input, output);

    return BeatResult(
      labels: _labels,
      probs: _softmax((output[0] as List).cast<double>()),
    );
  }

  List<double> _softmax(List<double> v) {
    final maxV = v.reduce(math.max);
    final exps = v.map((x) => math.exp(x - maxV)).toList();
    final sum = exps.fold<double>(0, (a, b) => a + b);
    return exps.map((x) => x / sum).toList();
  }

  void close() => _interpreter.close();
}
