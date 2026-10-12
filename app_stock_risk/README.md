# Risk Explorer

Predicts Low, Medium, or High next-week volatility for bundled stock-week examples.
The result screen compares each prediction with the observed class.

Educational demonstration only. Results are not medical or financial advice.

## Assets

`assets/` must contain `stock_classifier.tflite`, `labels.txt`, and `stock_samples.json`.
The model is ignored by Git. From the repository root, after preparing the dataset
and training the corresponding model:

```powershell
python src/stock_export_tflite.py
```

The export script checks predictions against PyTorch before copying the model and
labels into this app. The sample JSON must also be available before building.
The TFLite input shape is `[1, 12]`.

## Run

With Flutter installed and a device or emulator connected:

```sh
cd app_stock_risk
flutter pub get
flutter run
```

Android builds use the Android SDK; iOS builds require macOS and Xcode.

## Code

- `lib/classifier.dart`: TFLite inference and output probabilities.
- `lib/samples.dart`: bundled sample loading.
- `lib/result_screen.dart`: prediction, reference label, and limitations.
- `lib/onboarding_screen.dart`: first-run explanation and disclaimer.
