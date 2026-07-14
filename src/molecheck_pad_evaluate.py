"""Evaluate the MoleCheck domain-gap experiment (v2) and write a JSON report.

Runs two models on the SAME PAD-UFES-20 smartphone test split:
  * v1  — trained on ISIC/HAM10000 dermatoscopic images (the original app model)
  * v2  — v1 fine-tuned on PAD-UFES smartphone photos

The comparison isolates one variable: the training domain. v1's headline on its
own dermatoscopic test set was ROC-AUC 0.914; this script measures how far that
falls on real smartphone photos, and how much fine-tuning recovers.

Metrics per model: accuracy @0.5, ROC-AUC (threshold-independent, the fair
cross-prevalence headline), and the sensitivity/specificity trade-off at the
threshold that reaches a target sensitivity (default 90%, the app's operating
point). Writes trained_models/molecheck-v2/eval.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "data" / "pad_ufes_20" / "split" / "test"
OUT = ROOT / "trained_models" / "molecheck-v2" / "eval.json"

V1 = ROOT / "trained_models" / "molecheck" / "molecheck.pt"
V2 = ROOT / "runs" / "classify" / "molecheck_pad_v2" / "weights" / "best.pt"

# v1's reported ROC-AUC on its OWN in-domain (dermatoscopic) test set, for reference.
V1_OWN_DOMAIN_ROC_AUC = 0.914


def load_test_set(test_dir: Path):
    paths, labels = [], []
    for label_idx, label in enumerate(("benign", "malignant")):
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            for p in (test_dir / label).glob(ext):
                paths.append(p)
                labels.append(label_idx)
    return paths, np.array(labels)


def malignant_index(model: YOLO) -> int:
    for idx, name in model.names.items():
        if name == "malignant":
            return idx
    raise SystemExit(f"'malignant' not in classes: {model.names}")


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    pos = y_true == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def score_model(weights: Path, paths, y_true, imgsz, target_sens):
    model = YOLO(str(weights))
    mal_idx = malignant_index(model)
    scores = np.zeros(len(paths))
    for i, p in enumerate(paths):
        with Image.open(p) as im:
            rgb = im.convert("RGB")
        r = model.predict(rgb, imgsz=imgsz, verbose=False)[0]
        scores[i] = float(r.probs.data[mal_idx])

    acc = float(((scores >= 0.5).astype(int) == y_true).mean())
    auc = roc_auc(y_true, scores)

    mal_scores = np.sort(scores[y_true == 1])
    if len(mal_scores) == 0:
        raise SystemExit("No malignant images in the test set — cannot pick a threshold.")
    k = int(np.floor((1 - target_sens) * len(mal_scores)))
    thr = float(mal_scores[min(k, len(mal_scores) - 1)])
    pred = (scores >= thr).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    return {
        "accuracy_at_0.5": round(acc, 4),
        "roc_auc": round(auc, 4),
        "operating_threshold": round(thr, 4),
        "sensitivity": round(tp / (tp + fn), 4) if tp + fn else None,
        "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--target-sensitivity", type=float, default=0.90)
    args = ap.parse_args()

    paths, y_true = load_test_set(TEST)
    if not len(paths):
        raise SystemExit(f"No test images under {TEST}")
    n_mal = int(y_true.sum())
    print(f"PAD-UFES smartphone test set: {len(paths)} images ({n_mal} malignant)")

    print("Scoring v1 (dermoscopy-trained) on smartphone photos...")
    v1 = score_model(V1, paths, y_true, args.imgsz, args.target_sensitivity)
    print("Scoring v2 (fine-tuned on smartphone photos)...")
    v2 = score_model(V2, paths, y_true, args.imgsz, args.target_sensitivity)

    report = {
        "experiment": "MoleCheck v2 — dermoscopy->smartphone domain gap",
        "test_set": "PAD-UFES-20, patient-level test split (ACK excluded to match v1 label space)",
        "n_test_images": len(paths),
        "n_malignant": n_mal,
        "target_sensitivity": args.target_sensitivity,
        "reference_v1_on_own_dermoscopy_test_roc_auc": V1_OWN_DOMAIN_ROC_AUC,
        "v1_dermoscopy_on_smartphone": v1,
        "v2_finetuned_on_smartphone": v2,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
