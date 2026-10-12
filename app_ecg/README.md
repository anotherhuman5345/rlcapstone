# ECG Check

Classifies bundled MIT-BIH heartbeat samples into the N, S, V, and F beat classes.
Inference runs on the device; the app does not record ECG signals.

Educational demonstration only. Results are not medical or financial advice.

## Assets

`assets/` must contain `ecg_classifier.tflite`, `labels.txt`, and `ecg_samples.json`.
The model is ignored by Git. From the repository root, after preparing the dataset
and training the corresponding model:

```powershell
python src/ecg_export_tflite.py
```

The export script checks predictions against PyTorch before copying the model and
labels into this app. The sample JSON must also be available before building.
The TFLite input shape is `[1, 260, 1]`.

## Run

With Flutter installed and a device or emulator connected:

```sh
cd app_ecg
flutter pub get
flutter run
```

Android builds use the Android SDK; iOS builds require macOS and Xcode.

## Code

- `lib/classifier.dart`: TFLite inference and output probabilities.
- `lib/samples.dart`: bundled sample loading.
- `lib/result_screen.dart`: prediction, reference label, and limitations.
- `lib/onboarding_screen.dart`: first-run explanation and disclaimer.
