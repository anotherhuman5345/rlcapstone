"""Evaluate the C-NMC v2 binary classifier on the patient-held-out test split.

Honest metrics for the binary all-vs-hem task, reported both per image and
per patient (the test set is a small number of entirely unseen patients, so the
per-patient view is the fair one and its denominator is deliberately shown):
    accuracy, sensitivity (recall on malignant 'all'), specificity (recall on
    'hem'), ROC-AUC (rank-based, no sklearn dependency), and the confusion matrix.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST = ROOT / "data" / "leukemia_cnmc" / "split" / "test"
DEFAULT_WEIGHTS = ROOT / "runs/classify/leukemia_cnmc_v2/weights/best.pt"
CLASSES = ["all", "hem"]                # index 0 = malignant (positive), 1 = normal
SUBJECT_RE = re.compile(r"UID_([A-Za-z0-9]+)_", re.IGNORECASE)


def auc_score(y_true, scores) -> float:
    """ROC-AUC via the Mann-Whitney U statistic (rank-based)."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores, dtype=float)
    pos, neg = scores[y_true == 1], scores[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = scores.argsort()
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts)); np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    r_pos = ranks[y_true == 1].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    ap.add_argument("--test-dir", default=str(DEFAULT_TEST))
    ap.add_argument("--imgsz", type=int, default=224)
    args = ap.parse_args()

    model = YOLO(args.weights)
    idx_all = {v: k for k, v in model.names.items()}["all"]   # column for malignant prob

    paths, y_true, subj = [], [], []
    for i, cls in enumerate(CLASSES):
        for p in (Path(args.test_dir) / cls).glob("*.bmp"):
            paths.append(p)
            y_true.append(1 if cls == "all" else 0)
            m = SUBJECT_RE.match(p.name)
            if m is None:
                raise SystemExit(f"Cannot parse patient id from filename: {p.name}")
            subj.append((cls, m.group(1)))
    y_true = np.array(y_true)
    print(f"Test images: {len(paths)}  (patients: {len(set(subj))})")

    p_mal = np.zeros(len(paths))
    for i, p in enumerate(paths):
        probs = model.predict(Image.open(p).convert("RGB"), imgsz=args.imgsz,
                              verbose=False)[0].probs.data.cpu().numpy()
        p_mal[i] = float(probs[idx_all])
    y_pred = (p_mal >= 0.5).astype(int)

    def metrics(yt, yp, sc):
        tp = int(((yp == 1) & (yt == 1)).sum()); tn = int(((yp == 0) & (yt == 0)).sum())
        fp = int(((yp == 1) & (yt == 0)).sum()); fn = int(((yp == 0) & (yt == 1)).sum())
        acc = (tp + tn) / len(yt)
        sens = tp / (tp + fn) if tp + fn else 0.0
        spec = tn / (tn + fp) if tn + fp else 0.0
        return dict(accuracy=round(acc, 4), sensitivity=round(sens, 4),
                    specificity=round(spec, 4), roc_auc=round(auc_score(yt, sc), 4),
                    confusion=dict(tp=tp, tn=tn, fp=fp, fn=fn))

    per_image = metrics(y_true, y_pred, p_mal)

    # per-patient: mean malignant prob over the patient's cells
    agg = defaultdict(list); truth = {}
    for (cls, s), pm, yt in zip(subj, p_mal, y_true):
        agg[(cls, s)].append(pm); truth[(cls, s)] = yt
    keys = list(agg)
    pt_true = np.array([truth[k] for k in keys])
    pt_score = np.array([np.mean(agg[k]) for k in keys])
    pt_pred = (pt_score >= 0.5).astype(int)
    per_patient = metrics(pt_true, pt_pred, pt_score)
    per_patient["n_patients"] = len(keys)

    print("\n=== C-NMC v2 (patient-held-out) ===")
    print("Per image:  ", per_image)
    print("Per patient:", per_patient)

    out = DEFAULT_WEIGHTS.parent.parent / "leukemia_cnmc_eval.json"
    out.write_text(json.dumps({"per_image": per_image, "per_patient": per_patient,
                               "n_test_images": len(paths)}, indent=2))
    print(f"\nSaved report to {out}")


if __name__ == "__main__":
    main()
