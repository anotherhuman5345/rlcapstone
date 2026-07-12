import 'dart:convert';

import 'package:flutter/services.dart';

/// A real (ticker, date) example with its normalised feature vector, recent
/// closing prices, sentiment, and the true next-week risk class.
class StockSample {
  const StockSample({
    required this.ticker,
    required this.date,
    required this.trueClass,
    required this.features,
    required this.closes,
    required this.sentiment,
    required this.sentCount,
  });

  final String ticker;
  final String date;
  final String trueClass;
  final List<double> features;
  final List<double> closes;
  final double sentiment;
  final int sentCount;
}

Future<List<StockSample>> loadSamples() async {
  final raw = await rootBundle.loadString('assets/stock_samples.json');
  final data = jsonDecode(raw) as Map<String, dynamic>;
  final list = (data['samples'] as List).cast<Map<String, dynamic>>();
  return [
    for (final s in list)
      StockSample(
        ticker: s['ticker'] as String,
        date: s['date'] as String,
        trueClass: s['trueClass'] as String,
        features: (s['features'] as List).map((v) => (v as num).toDouble()).toList(),
        closes: (s['closes'] as List).map((v) => (v as num).toDouble()).toList(),
        sentiment: (s['sentiment'] as num).toDouble(),
        sentCount: (s['sentCount'] as num).toInt(),
      ),
  ];
}
