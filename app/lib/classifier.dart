import 'dart:math' as math;

import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

/// Result of running the model on one image.
class Classification {
  const Classification({required this.malignantProb, required this.threshold});

  /// Probability (0..1) that the lesion is malignant.
  final double malignantProb;

  /// Decision threshold chosen at evaluation time to hit the target
  /// sensitivity. At or above this, we surface a "concerning" result.
  final double threshold;

  bool get isConcerning => malignantProb >= threshold;
  double get benignProb => 1 - malignantProb;
}

/// Wraps the TFLite skin-lesion classifier. Loads the model once and reuses it.
class MoleClassifier {
  MoleClassifier._(this._interpreter, this._labels, this._inputSize, this._nchw);

  final Interpreter _interpreter;
  final List<String> _labels;
  final int _inputSize;
  final bool _nchw; // true if the model wants [1,3,H,W] rather than [1,H,W,3]

  // Decision threshold for the v2 (smartphone-trained) model, tuned for ~90%
  // sensitivity on the PAD-UFES-20 phone-photo test set (ROC-AUC 0.920;
  // specificity 0.75 at this threshold). v1 (dermoscopy) used 0.137 on ISIC.
  static const double decisionThreshold = 0.368;

  static Future<MoleClassifier> load() async {
    final interpreter = await Interpreter.fromAsset(
      'assets/mole_classifier.tflite',
    );
    final labelsRaw = await rootBundle.loadString('assets/labels.txt');
    final labels = labelsRaw
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();

    final inShape = interpreter.getInputTensor(0).shape; // e.g. [1,224,224,3]
    final nchw = inShape.length == 4 && inShape[1] == 3;
    final size = nchw ? inShape[2] : inShape[1];
    return MoleClassifier._(interpreter, labels, size, nchw);
  }

  int get _malignantIndex {
    final i = _labels.indexOf('malignant');
    return i >= 0 ? i : _labels.length - 1;
  }

  /// Run inference on raw image bytes (JPEG/PNG from the camera or gallery).
  Classification run(Uint8List imageBytes) {
    final decoded = img.decodeImage(imageBytes);
    if (decoded == null) {
      throw const FormatException('Could not decode the selected image.');
    }
    final resized = img.copyResize(
      decoded,
      width: _inputSize,
      height: _inputSize,
    );

    // Build the normalised input tensor. Training used pixels / 255.
    final input = _nchw ? _toNchw(resized) : _toNhwc(resized);
    final output = List.filled(
      _labels.length,
      0.0,
    ).reshape([1, _labels.length]);
    _interpreter.run(input, output);

    final probs = _softmaxIfNeeded(
      (output[0] as List).cast<double>(),
    );
    return Classification(
      malignantProb: probs[_malignantIndex],
      threshold: decisionThreshold,
    );
  }

  List<List<List<List<double>>>> _toNhwc(img.Image im) {
    return [
      List.generate(
        _inputSize,
        (y) => List.generate(_inputSize, (x) {
          final p = im.getPixel(x, y);
          return [p.r / 255.0, p.g / 255.0, p.b / 255.0];
        }),
      ),
    ];
  }

  List<List<List<List<double>>>> _toNchw(img.Image im) {
    List<List<double>> channel(double Function(img.Pixel) sel) => List.generate(
      _inputSize,
      (y) => List.generate(_inputSize, (x) => sel(im.getPixel(x, y))),
    );
    return [
      [
        channel((p) => p.r / 255.0),
        channel((p) => p.g / 255.0),
        channel((p) => p.b / 255.0),
      ],
    ];
  }

  /// YOLO-cls already applies softmax, but guard against a raw-logits export
  /// by re-normalising if the outputs don't look like a probability vector.
  List<double> _softmaxIfNeeded(List<double> v) {
    final sum = v.fold<double>(0, (a, b) => a + b);
    final looksNormalised =
        (sum - 1.0).abs() < 0.05 && v.every((x) => x >= 0 && x <= 1);
    if (looksNormalised) return v;
    final maxV = v.reduce(math.max);
    final exps = v.map((x) => math.exp(x - maxV)).toList();
    final expSum = exps.fold<double>(0, (a, b) => a + b);
    return exps.map((x) => x / expSum).toList();
  }

  void close() => _interpreter.close();
}
