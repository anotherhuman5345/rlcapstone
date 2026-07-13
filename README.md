# RLcapstone — End-to-End AI Projects in Biomedical Computing

Source code for a portfolio of six end-to-end applied-AI projects, most at the intersection of
computer science and bioengineering. Each project is built in full — dataset preparation, model
training on local GPU hardware, rigorous evaluation, and deployment to a working application or
interactive demonstration — and documented with an emphasis on reproducibility and the honest
reporting of limitations.

**Live site and interactive demos:** https://rlcapstone.ai

> **Educational use only.** These are learning projects, not certified products or medical devices,
> and nothing here constitutes medical, financial, or professional advice.

## Projects

| Project | Method | Headline result | Live write-up |
|---|---|---|---|
| **MoleCheck** — privacy-preserving skin-lesion analysis | YOLO11s-cls (transfer learning), on-device TFLite | ROC-AUC 0.914; 90% sensitivity at 75% specificity | [molecheck](https://rlcapstone.ai/projects/molecheck.html) |
| **ECG Arrhythmia Classification** | 1D CNN on MIT-BIH, inter-patient split | ~96% validation collapses to **44% macro-recall** on unseen patients — a study of the generalization gap | [ecg](https://rlcapstone.ai/projects/ecg.html) |
| **ADHD Classification from EEG** | Multi-channel 1D CNN, strict subject-level split | 91.7% subject-level accuracy, ROC-AUC 0.965 on 24 unseen children | [adhd-eeg](https://rlcapstone.ai/projects/adhd-eeg.html) |
| **Leukemia Cell Subtyping** | YOLO11s-cls on blood smears | 99.8% — presented as a **case study in data leakage**, not an achievement | [leukemia](https://rlcapstone.ai/projects/leukemia.html) |
| **Stock Volatility & Sentiment** | Compact MLP, controlled ablation | 56% on 3 classes; ablation shows **sentiment did not improve** the model | [stock-risk](https://rlcapstone.ai/projects/stock-risk.html) |
| **Autonomous Pentest Agent** | Tabular Q-learning over a sandboxed web app | Finds all 3 planted vulnerabilities in 4 actions vs. ~25 for random; plus the JADEPUFFER defensive detector | [pentest-agent](https://rlcapstone.ai/projects/pentest-agent.html) |

A recurring theme across the portfolio is rigorous, honest evaluation: leakage-aware and
subject-level train/test splits, metrics chosen to suit the task (sensitivity/specificity, ROC-AUC,
macro-recall over raw accuracy), and negative results reported rather than hidden.

## Trained models

The actual trained weights and the raw training logs for every project are published under
[`trained_models/`](trained_models) — per-epoch `results.csv`, confusion matrices, and evaluation
reports alongside each checkpoint — so the numbers can be inspected and reproduced, not just taken
on faith. Everything regenerates from the scripts in [`src/`](src).

## Repository layout

- `src/` — training, export, and inference code for all six projects, plus the pentest app/agent and the JADEPUFFER detector
- `app/`, `app_ecg/`, `app_adhd_eeg/`, `app_leukemia/`, `app_stock_risk/` — Flutter applications (Android/iOS) running the exported models on-device
- `scripts/` — PDF capstone-report generators
- `samples/` — sample logs for the JADEPUFFER detector
- `notebooks/` — experiment notebooks
- `docs/` — written reports

Datasets, trained weights, build artifacts, and APKs are intentionally **not** committed
(`data/`, `*.pt/*.pth/*.onnx/*.tflite`, `runs/`, `dist/`, `*.apk` — see `.gitignore`). Models are
regenerated from the training and export scripts in `src/`.

## Security note (Autonomous Pentest Agent)

`src/pentest_app.py` is a **deliberately vulnerable** practice application. It binds to `127.0.0.1`
only, is meant purely for education, and must never be deployed or exposed to a network. The
vulnerabilities are standard OWASP Top 10 teaching examples, and the agent must only be run against
this sandbox or systems you own or are explicitly authorized to test.

## Development environment

Trained on an NVIDIA GeForce RTX 5060 Ti (Blackwell) under Windows 11, Python 3.12.

```powershell
# Create the environment (PyTorch CUDA 12.8 build is required for Blackwell GPUs)
python -m venv .venv
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
