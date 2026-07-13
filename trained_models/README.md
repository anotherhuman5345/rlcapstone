# Trained models + training logs

The actual trained model for every project in this portfolio, published alongside
the training evidence so the results can be inspected and reproduced rather than
taken on faith.

Each folder contains the trained weights plus the raw output the training run
produced — the per-epoch `results.csv`, the `confusion_matrix.png`, and the
evaluation report. Those logs are the real record that the training happened, on
our own hardware (an NVIDIA RTX 5060 Ti), with the configs in `../src/`.

| Folder | Model | Weights | What the logs show |
|---|---|---|---|
| `molecheck/` | YOLO11s-cls (skin lesion, v1 — dermoscopy) | `molecheck.pt` | `results.csv`, confusion matrix |
| `molecheck-v2/` | YOLO11s-cls, v1 fine-tuned on smartphone photos | `molecheck_v2.pt` | `results.csv`, confusion, `eval.json` (0.743&rarr;0.920 ROC-AUC domain-gap recovery) |
| `ecg/` | 1D CNN (heartbeat) | `ecg.pt` | `report.json` (per-class recall, macro-recall) |
| `adhd/` | multi-channel 1D CNN (EEG) | `adhd.pt` | `report.json` (subject-level metrics) |
| `leukemia-v1/` | YOLO11s-cls, 4-class | `leukemia_v1.pt` | `results.csv`, confusion, `eval.json` (99.8% — leakage-inflated) |
| `leukemia-v2/` | YOLO11s-cls, binary, patient-split | `leukemia_v2.pt` | `results.csv`, confusion, `eval.json` (80.8% — honest) |
| `stock/` | MLP (volatility risk) | `stock.pt` | `report.json` (incl. the sentiment ablation) |

## Reproduce it

Everything here is regenerated from the scripts in [`../src/`](../src). For example:

```bash
# Leukemia v2 (the patient-level experiment)
python src/leukemia_cnmc_prepare.py     # patient-disjoint split of C-NMC 2019
python src/train.py --data data/leukemia_cnmc/split --name leukemia_cnmc_v2
python src/leukemia_cnmc_evaluate.py    # -> the eval.json in leukemia-v2/

# MoleCheck v2 (the dermoscopy -> smartphone domain-gap experiment)
python src/molecheck_pad_prepare.py --copy   # patient-level split of PAD-UFES-20 phone photos
python src/train.py --model trained_models/molecheck/molecheck.pt \
    --data data/pad_ufes_20/split --name molecheck_pad_v2   # fine-tune v1 on phone photos
python src/molecheck_pad_evaluate.py         # -> the eval.json in molecheck-v2/
```

The datasets themselves are public (see each `src/*_prepare.py` / `*_download.py`
for the source) and are not committed here.

## What this does and doesn't prove

These files show the models are real, that the reported numbers came out of an
actual training run, and that anyone can retrain them from the code. Weights on
their own don't prove *who* trained them — the honest evidence of authorship is
the combination of the training code, these per-epoch logs, the full commit
history in this repo, and the fact that it all reproduces from scratch.

The deployed inference models (ONNX for the browser demos, TensorFlow Lite for the
apps) are separately public on the live site at
[rlcapstone.ai](https://rlcapstone.ai).
