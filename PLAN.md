# Capstone Plan — Mole / Skin-Lesion Classifier

**Goal:** A mobile app (iPhone + Android) that takes a photo of a mole and uses an
on-device AI model to estimate whether it looks benign or malignant.

**Important framing:** this is an educational capstone, *not* a medical device.
The app must always present results as a risk indicator with a clear
"see a dermatologist" disclaimer — never as a diagnosis.

## Architecture decisions (2026-07-11)

| Decision      | Choice                                             |
|---------------|----------------------------------------------------|
| Inference     | On-device, TensorFlow Lite (offline, private)      |
| App framework | Flutter (one Dart codebase for iOS + Android)      |
| Training      | PyTorch / Ultralytics on local RTX 5060 Ti         |
| Dataset       | HAM10000 (10,015 dermatoscopic images, 7 classes)  |
| iOS builds    | Mac available → local Xcode builds                 |

## Status (2026-07-11)
Phases 0–4 complete and verified live on an Android emulator. Model: ROC-AUC
0.914, 90% sensitivity at threshold 0.137. App runs on-device inference and
correctly classified a known malignant image (48%, flagged) and a known benign
image (0%, cleared). Phase 5 (iOS build on the Mac, polish, writeup) remains.

## Phases

### Phase 0 — Tooling (one-time setup)
- [ ] Install Flutter SDK (Windows)
- [ ] Install Android Studio / Android SDK + platform tools
- [ ] Enable USB debugging on an Android phone (or use the emulator)

### Phase 1 — Dataset
- [ ] Download HAM10000 (~3 GB) into `data/ham10000/`
- [ ] Prep script: map 7 diagnosis classes → binary (malignant / benign),
      split train/val/test **by lesion ID** (the same lesion appears in
      multiple photos — naive splits leak data)
- [ ] Handle class imbalance (malignant ≈ 20% of images)

### Phase 2 — Model training (GPU)
- [ ] Baseline: Ultralytics YOLO classification model fine-tuned on HAM10000
      (fast to train, exports straight to TFLite)
- [ ] Evaluate: accuracy, sensitivity/specificity, ROC-AUC, confusion matrix
      — for a medical-ish task, **sensitivity (catching malignant) matters most**
- [ ] Stretch: custom PyTorch model (EfficientNet/MobileNetV3 transfer
      learning) as a comparison for the writeup

### Phase 3 — Model export
- [ ] Export to TensorFlow Lite (`.tflite`), verify accuracy parity vs PyTorch
- [ ] Quantize (float16) to shrink for mobile; re-verify accuracy

### Phase 4 — Flutter app
- [ ] Scaffold app: camera capture + gallery picker
- [ ] Integrate `tflite_flutter`, run the model on captured photos
- [ ] Results screen: benign/malignant probability, confidence bar,
      prominent medical disclaimer
- [ ] Test on Android device/emulator

### Phase 5 — iOS + polish
- [ ] On the Mac: install Xcode + Flutter, clone the repo, build and run
      the app on an iPhone (free Apple ID works for on-device testing;
      a $99/yr Apple Developer account only needed for App Store/TestFlight)
- [ ] App icon, onboarding screen with photo-taking tips
      (good lighting, close-up, ruler/coin for scale)
- [ ] Capstone writeup: dataset, methodology, metrics, limitations

## Repo layout (planned)
- `src/` — training + data prep Python code
- `scripts/` — utilities (env checks, dataset download)
- `notebooks/` — experiments
- `data/`, `models/`, `runs/` — git-ignored artifacts
- `app/` — Flutter application
