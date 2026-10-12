# EEG Explorer

Classifies bundled 19-channel EEG windows as Control or ADHD study group.
The samples come from held-out subjects; the app does not record EEG signals.

Educational demonstration only. Results are not medical or financial advice.

## Assets

`assets/` must contain `adhd_classifier.tflite`, `labels.txt`, and `adhd_samples.json`.
The model is ignored by Git. From the repository root, after preparing the dataset
and training the corresponding model:

```powershell
python src/adhd_export_tflite.py
```

The export script checks predictions against PyTorch before copying the model and
labels into this app. The sample JSON must also be available before building.
The TFLite input shape is `[1, 256, 19]`.

## Run

With Flutter installed and a device or emulator connected:

```sh
cd app_adhd_eeg
flutter pub get
flutter run
```

Android builds use the Android SDK; iOS builds require macOS and Xcode.

## Code

- `lib/classifier.dart`: TFLite inference and output probabilities.
- `lib/samples.dart`: bundled sample loading.
- `lib/result_screen.dart`: prediction, reference label, and limitations.
- `lib/onboarding_screen.dart`: first-run explanation and disclaimer.
