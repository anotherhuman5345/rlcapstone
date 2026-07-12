"""Evaluate the 4-class ALL classifier on the held-out test split.

Multi-class metrics: overall accuracy, a 4x4 confusion matrix, and per-class
precision / recall / F1, plus macro-F1 (unweighted mean, so the smaller Benign
class counts as much as the larger ones). The clinically important signal is how
often a malignant subtype is missed as Benign, which the confusion matrix shows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST = ROOT / "data" / "leukemia" / "split" / "test"
CLASSES = ["benign", "early", "pre", "pro"]


def load_test(test_dir: Path):
    paths, labels = [], []
    for i, cls in enumerate(CLASSES):
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for p in (test_dir / cls).glob(ext):
                paths.append(p)
                labels.append(i)
    return paths, np.array(labels)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(ROOT / "runs/classify/leukemia_cls/weights/best.pt"))
    ap.add_argument("--test-dir", default=str(DEFAULT_TEST))
    ap.add_argument("--imgsz", type=int, default=224)
    args = ap.parse_args()

    model = YOLO(args.weights)
    # map model class indices to our CLASSES order
    name_to_idx = {v: k for k, v in model.names.items()}
    order = [name_to_idx[c] for c in CLASSES]

    paths, y_true = load_test(Path(args.test_dir))
    print(f"Test images: {len(paths)}")

    y_pred = np.zeros(len(paths), dtype=int)
    for i, p in enumerate(paths):
        probs = model.predict(Image.open(p).convert("RGB"), imgsz=args.imgsz,
                              verbose=False)[0].probs.data.cpu().numpy()
        # reorder to CLASSES, take argmax
        y_pred[i] = int(np.argmax(probs[order]))

    n = len(CLASSES)
    cm = np.zeros((n, n), dtype=int)
    for t, pr in zip(y_true, y_pred):
        cm[t, pr] += 1
    acc = float(cm.trace() / cm.sum())

    per_class = {}
    f1s = []
    for i, c in enumerate(CLASSES):
        tp = cm[i, i]
        recall = tp / cm[i].sum() if cm[i].sum() else 0.0
        precision = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_class[c] = {"precision": round(precision, 4),
                        "recall": round(recall, 4), "f1": round(f1, 4)}
    macro_f1 = float(np.mean(f1s))

    print(f"\nAccuracy: {acc:.4f}   macro-F1: {macro_f1:.4f}")
    for c, m in per_class.items():
        print(f"  {c:7s} precision {m['precision']:.3f}  recall {m['recall']:.3f}  f1 {m['f1']:.3f}")
    print("\nConfusion matrix (rows=true, cols=pred):")
    print("          " + "  ".join(f"{c:>7}" for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print(f"  {c:7s} " + "  ".join(f"{cm[i,j]:7d}" for j in range(n)))

    report = {"classes": CLASSES, "accuracy": acc, "macro_f1": macro_f1,
              "per_class": per_class, "confusion_matrix": cm.tolist()}
    out = ROOT / "runs" / "classify" / "leukemia_cls" / "leukemia_eval.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nSaved report to {out}")


if __name__ == "__main__":
    main()
