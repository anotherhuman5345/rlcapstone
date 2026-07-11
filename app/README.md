# MoleCheck — Flutter app

On-device skin-lesion screening aid. Takes a photo of a mole and runs a
TensorFlow Lite classifier **entirely on the phone** (no server, no upload) to
estimate benign vs malignant likelihood.

> **Educational project — not a medical device.** Results are a risk indicator,
> never a diagnosis. The UI always tells the user to consult a dermatologist.

## Prerequisites
- Flutter SDK (stable)
- The trained model. From the repo root:
  ```
  .venv\Scripts\python.exe src\export_tflite.py
  ```
  This writes `app/assets/mole_classifier.tflite` and `app/assets/labels.txt`.

## Run on Android (from Windows)
```
cd app
flutter pub get
flutter run           # with a device/emulator connected
```

## Run on iOS (on the Mac)
```
cd app
flutter pub get
flutter run            # with an iPhone connected and trusted, or a simulator
```
A free Apple ID is enough for on-device testing; a paid Apple Developer
account is only needed for TestFlight / App Store distribution.

## Structure
- `lib/main.dart` — home screen (camera + gallery capture, photo tips, disclaimer)
- `lib/classifier.dart` — loads the TFLite model, preprocesses images, runs inference
- `lib/result_screen.dart` — shows the estimate, a confidence bar, and safety guidance

## Decision threshold
`MoleClassifier.decisionThreshold` in `lib/classifier.dart` controls how eagerly
the app flags a lesion as concerning. Set it to the value that `src/evaluate.py`
prints for your target sensitivity (defaults to 0.30), then rebuild.
