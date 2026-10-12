# RLcapstone

Six machine-learning projects covering skin images, ECG, EEG, blood cells, stock volatility,
and a reinforcement-learning security sandbox. This repository contains the data preparation,
training, evaluation, and model export scripts, plus five Flutter apps.

**Live site and interactive demos:** https://rlcapstone.ai

> **Educational use only.** These are learning projects, not certified products or medical devices,
> and nothing here constitutes medical, financial, or professional advice.

## Projects

| Project | Method | Result | Live write-up |
|---|---|---|---|
| **MoleCheck** — privacy-preserving skin-lesion analysis | YOLO11s-cls (transfer learning), on-device TFLite | ROC-AUC 0.914; 90% sensitivity at 75% specificity | [molecheck](https://rlcapstone.ai/projects/molecheck.html) |
| **ECG Arrhythmia Classification** | 1D CNN on MIT-BIH, inter-patient split | ~96% validation collapses to **44% macro-recall** on unseen patients — a study of the generalization gap | [ecg](https://rlcapstone.ai/projects/ecg.html) |
| **ADHD Classification from EEG** | Multi-channel 1D CNN, strict subject-level split | 91.7% subject-level accuracy, ROC-AUC 0.965 on 24 unseen children | [adhd-eeg](https://rlcapstone.ai/projects/adhd-eeg.html) |
| **Leukemia Cell Subtyping** | YOLO11s-cls on blood smears, multi-source | 99.8% with possible patient leakage; 81% with a patient split; **v3** trained on two labs and tested on a third | [leukemia](https://rlcapstone.ai/projects/leukemia.html) |
| **Stock Volatility & Sentiment** | Compact MLP, controlled ablation | 57% on 3 classes; ablation shows **sentiment did not improve** the model | [stock-risk](https://rlcapstone.ai/projects/stock-risk.html) |
| **Autonomous Pentest Agent** | Tabular Q-learning over a sandboxed web app | Finds all 3 planted vulnerabilities in 4 actions vs. ~25 for random; plus the JADEPUFFER defensive detector | [pentest-agent](https://rlcapstone.ai/projects/pentest-agent.html) |

The write-ups explain the splits and report sensitivity, specificity, ROC-AUC, or macro-recall
where accuracy alone would hide important errors. They also cover failed experiments, including
the stock sentiment ablation and the ECG model's poor recall on unseen patients.

## Trained models

[`trained_models/`](trained_models) contains checkpoints, training logs, confusion matrices, and
evaluation reports. See [`src/`](src) for the scripts that produced them; rerunning those scripts
requires the relevant datasets and dependencies.

## Repository layout

- `src/` — training, export, and inference code for all six projects, plus the pentest app/agent and the JADEPUFFER detector
- `app/`, `app_ecg/`, `app_adhd_eeg/`, `app_leukemia/`, `app_stock_risk/` — Flutter applications (Android/iOS) running the exported models on-device
- `scripts/` — PDF capstone-report generators
- `samples/` — sample logs for the JADEPUFFER detector
- `notebooks/` — experiment notebooks
- `docs/` — written reports

Raw datasets, full training runs, build artifacts, APKs, and app-bundled model files are ignored
(see `.gitignore`). Selected checkpoints and logs are tracked under `trained_models/`.
The export scripts in `src/` regenerate the apps' `*.tflite` files.

## Security note (Autonomous Pentest Agent)

`src/pentest_app.py` is a **deliberately vulnerable** practice application. It binds to `127.0.0.1`
only, is meant purely for education, and must never be deployed or exposed to a network. The
vulnerabilities are standard OWASP Top 10 teaching examples, and the agent must only be run against
this sandbox or systems you own or are explicitly authorized to test.

## Development environment

Developed on an NVIDIA GeForce RTX 5060 Ti (Blackwell) under Windows 11, Python 3.12. A GPU is used
for training; inference, export, and most scripts also run CPU-only.

```powershell
python -m venv .venv

# PyTorch first — pick your build:
#   GPU (Blackwell needs the CUDA 12.8 wheels):
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
#   CPU-only:
#   .venv\Scripts\python.exe -m pip install torch torchvision

.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Training scripts pick the device automatically (`--device` to override; defaults to GPU 0 if a CUDA
GPU is present, otherwise CPU).

## License

MIT — see [`LICENSE`](LICENSE). The license covers the source code. The public datasets used remain
under their own licenses and are not redistributed here; where a dataset is non-commercial, the
derived model weights should be treated accordingly.
