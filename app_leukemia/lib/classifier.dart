import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

class CellResult {
  const CellResult({required this.labels, required this.probs});
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

/// Wraps the on-device 4-class ALL cell classifier. The TFLite model takes a
/// [1,224,224,3] input, /255 normalised (onnx2tf produced NHWC). Emits 4
/// probabilities (YOLO-cls already softmaxes; we guard just in case).
/// Classes: [benign, early, pre, pro].
class CellClassifier {
  CellClassifier._(this._interpreter, this._labels, this._size);

  final Interpreter _interpreter;
  final List<String> _labels;
  final int _size;

  List<String> get labels => List.unmodifiable(_labels);

  static Future<CellClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(
      'assets/leukemia_classifier.tflite',
    );
    final labelsRaw = await rootBundle.loadString('assets/labels.txt');
    final labels = labelsRaw
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
    final shape = interpreter.getInputTensor(0).shape; // [1,224,224,3]
    final size = shape.length >= 2 ? shape[1] : 224;
    return CellClassifier._(interpreter, labels, size);
  }

  /// Classify raw image bytes (a bundled JPEG).
  CellResult run(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      throw const FormatException('Could not decode image.');
    }
    final resized = img.copyResize(decoded, width: _size, height: _size);
    final input = [
      List.generate(
        _size,
        (y) => List.generate(_size, (x) {
          final p = resized.getPixel(x, y);
          return [p.r / 255.0, p.g / 255.0, p.b / 255.0];
        }),
      ),
    ];
    final output = List.filled(
      _labels.length,
      0.0,
    ).reshape([1, _labels.length]);
    _interpreter.run(input, output);
    return CellResult(
      labels: _labels,
      probs: _softmaxIfNeeded((output[0] as List).cast<double>()),
    );
  }

  List<double> _softmaxIfNeeded(List<double> v) {
    final sum = v.fold<double>(0, (a, b) => a + b);
    final normalised =
        (sum - 1.0).abs() < 0.05 && v.every((x) => x >= 0 && x <= 1);
    if (normalised) return v;
    final maxV = v.reduce(math.max);
    final exps = v.map((x) => math.exp(x - maxV)).toList();
    final s = exps.fold<double>(0, (a, b) => a + b);
    return exps.map((x) => x / s).toList();
  }

  void close() => _interpreter.close();
}
