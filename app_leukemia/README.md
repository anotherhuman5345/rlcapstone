# Cell Explorer

Classifies bundled blood-cell images as `all` (leukemic) or `hem` (normal).
The current app uses a binary classifier; the original four-class experiment
is documented separately in the project write-up.

Educational demonstration only. This app cannot diagnose leukemia.

## Assets

Before building, provide these files under `assets/`:

- `leukemia_classifier.tflite`: binary model with input `[1, 224, 224, 3]`.
- `labels.txt`: model label order (`all`, `hem`).
- `leukemia_samples.json`: sample manifest.
- `cells/`: images referenced by the manifest.

Model and sample-image files are ignored by Git. Use assets from the matching
model export; the older four-class ONNX export is not a drop-in replacement.

## Run

With Flutter installed and a device or emulator connected:

```sh
cd app_leukemia
flutter pub get
flutter run
```

Android builds use the Android SDK; iOS builds require macOS and Xcode.

## Code

- `lib/classifier.dart`: image preprocessing and TFLite inference.
- `lib/samples.dart`: sample manifest loading.
- `lib/result_screen.dart`: image, prediction, reference label, and limitations.
- `lib/onboarding_screen.dart`: first-run explanation and disclaimer.
