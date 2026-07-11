"""Evaluate a trained mole classifier on the held-out test split.

For a cancer-screening aid the headline number is NOT plain accuracy — with
~80% benign, a model that always says "benign" already scores 80%. What matters
is **sensitivity** (recall on malignant: of the truly malignant lesions, how many
did we flag?) traded against **specificity** (how many benign we correctly clear).

This script reports accuracy, a confusion matrix, ROC-AUC, and picks the decision
threshold that reaches a target sensitivity, printing the specificity you pay for
it. That threshold is what the app should use, not the default 0.5.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "data" / "ham10000" / "split" / "test"


def load_test_set() -> tuple[list[Path], np.ndarray]:
    paths, labels = [], []
    for label_idx, label in enumerate(("benign", "malignant")):
        for p in (TEST / label).glob("*.jpg"):
            paths.append(p)
            labels.append(label_idx)
    return paths, np.array(labels)


def malignant_index(model: YOLO) -> int:
    for idx, name in model.names.items():
        if name == "malignant":
            return idx
    raise SystemExit(f"'malignant' not found in model classes: {model.names}")


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """AUC via the rank-sum (Mann-Whitney U) identity — no sklearn needed."""
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    pos = y_true == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return (ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", default=str(ROOT / "runs/classify/mole_cls/weights/best.pt"))
    ap.add_argument("--target-sensitivity", type=float, default=0.90)
    ap.add_argument("--imgsz", type=int, default=224)
    args = ap.parse_args()

    model = YOLO(args.weights)
    mal_idx = malignant_index(model)
    paths, y_true = load_test_set()
    if not len(paths):
        raise SystemExit(f"No test images under {TEST}")
    print(f"Test images: {len(paths)}  (malignant: {int(y_true.sum())})")

    scores = np.zeros(len(paths))
    for i, p in enumerate(paths):
        r = model.predict(Image.open(p).convert("RGB"), imgsz=args.imgsz, verbose=False)[0]
        scores[i] = float(r.probs.data[mal_idx])

    # Default-threshold accuracy.
    pred_default = (scores >= 0.5).astype(int)
    acc = (pred_default == y_true).mean()
    print(f"\nAccuracy @0.5: {acc:.3f}")
    print(f"ROC-AUC: {roc_auc(y_true, scores):.3f}")

    # Threshold for the target sensitivity.
    mal_scores = np.sort(scores[y_true == 1])
    k = int(np.floor((1 - args.target_sensitivity) * len(mal_scores)))
    thr = mal_scores[min(k, len(mal_scores) - 1)]
    pred = (scores >= thr).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    sens = tp / (tp + fn) if tp + fn else 0
    spec = tn / (tn + fp) if tn + fp else 0
    print(f"\nAt threshold {thr:.3f} (targeting {args.target_sensitivity:.0%} sensitivity):")
    print(f"  Sensitivity (malignant caught): {sens:.3f}")
    print(f"  Specificity (benign cleared):   {spec:.3f}")
    print("  Confusion matrix:")
    print(f"                 pred benign   pred malignant")
    print(f"    benign          {tn:6d}         {fp:6d}")
    print(f"    malignant       {fn:6d}         {tp:6d}")
    print(f"\n  >>> Use threshold {thr:.3f} in the Flutter app. <<<")


if __name__ == "__main__":
    main()
