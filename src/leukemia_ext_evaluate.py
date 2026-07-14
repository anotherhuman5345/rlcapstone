"""External (cross-source) validation of the leukemia v2 model.

v2 was trained + tested on C-NMC 2019 (an Indian lab; single cells segmented onto
a BLACK background). v3 asks the real-world question: does it survive a DIFFERENT
lab's microscope? We score the unchanged v2 model on two independent datasets:

  * Aria et al. 2021 (Tehran) — same binary task (B-ALL blast vs benign). It ships
    an Original (real smear background) AND a Segmented (black background, matching
    C-NMC's style) version, so we run BOTH:
      - Original  -> tests robustness to background/domain shift
      - Segmented -> matched style, isolates whether the model learned the CELL
    The gap between them answers v1's question: cell morphology, or background?

  * Acevedo 2020 (Barcelona) — 8 types of NORMAL cells from healthy people. No
    blasts, so this is a SPECIFICITY probe: how often does the model false-alarm
    on another lab's normal cells? The `lymphocyte` class is the key hard-negative
    (normal lymphocytes are what leukemic lymphoblasts most resemble).

Model output: P(leukemic) = probs[index of class "all"]. Decision at 0.5.
Writes trained_models/leukemia-v3/ext_eval.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "leukemia_ext"
V2 = ROOT / "trained_models" / "leukemia-v2" / "leukemia_v2.pt"
OUT = ROOT / "trained_models" / "leukemia-v3" / "ext_eval.json"

ARIA_BLAST = {"Early", "Pre", "Pro"}   # 3 B-ALL maturation stages -> leukemic
ARIA_NORMAL = {"Benign"}                # hematogones / reactive -> normal (hard negative)


def leukemic_index(model: YOLO) -> int:
    for idx, name in model.names.items():
        if name == "all":
            return idx
    raise SystemExit(f"class 'all' (leukemic) not in model: {model.names}")


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    pos = y_true == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def score_dir(model: YOLO, mal_idx: int, directory: Path, imgsz: int) -> np.ndarray:
    scores = []
    for p in sorted(directory.glob("*.*")):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
            continue
        with Image.open(p) as im:
            rgb = im.convert("RGB")
        r = model.predict(rgb, imgsz=imgsz, verbose=False)[0]
        scores.append(float(r.probs.data[mal_idx]))
    return np.array(scores)


def binary_metrics(p_leuk: np.ndarray, y: np.ndarray) -> dict:
    pred = (p_leuk >= 0.5).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    return {
        "n": int(len(y)), "n_blast": int((y == 1).sum()), "n_normal": int((y == 0).sum()),
        "accuracy": round(float((pred == y).mean()), 4),
        "roc_auc": round(roc_auc(y, p_leuk), 4),
        "sensitivity": round(tp / (tp + fn), 4) if tp + fn else None,
        "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def eval_aria(model, mal_idx, variant: str, imgsz: int) -> dict:
    root = EXT / "aria" / variant
    p_all, y_all = [], []
    for cls_dir in sorted(root.iterdir()):
        if not cls_dir.is_dir():
            continue
        label = 1 if cls_dir.name in ARIA_BLAST else (0 if cls_dir.name in ARIA_NORMAL else None)
        if label is None:
            continue
        s = score_dir(model, mal_idx, cls_dir, imgsz)
        p_all.append(s)
        y_all.append(np.full(len(s), label))
    p_all = np.concatenate(p_all)
    y_all = np.concatenate(y_all)
    m = binary_metrics(p_all, y_all)
    return m


def eval_acevedo(model, mal_idx, imgsz: int) -> dict:
    root = EXT / "acevedo" / "bloodcells_dataset"
    per_class = {}
    total_fp = total_n = 0
    for cls_dir in sorted(root.iterdir()):
        if not cls_dir.is_dir():
            continue
        s = score_dir(model, mal_idx, cls_dir, imgsz)
        flagged = int((s >= 0.5).sum())
        per_class[cls_dir.name] = {"n": int(len(s)),
                                   "false_positive_rate": round(flagged / len(s), 4) if len(s) else None,
                                   "mean_p_leukemic": round(float(s.mean()), 4) if len(s) else None}
        total_fp += flagged
        total_n += len(s)
    return {"n": total_n, "overall_false_positive_rate": round(total_fp / total_n, 4),
            "overall_specificity": round(1 - total_fp / total_n, 4), "by_cell_type": per_class}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", default=str(V2))
    ap.add_argument("--imgsz", type=int, default=224)
    args = ap.parse_args()

    model = YOLO(args.weights)
    mal_idx = leukemic_index(model)

    print("Scoring Aria (Original — real background)...")
    aria_orig = eval_aria(model, mal_idx, "Original", args.imgsz)
    print("Scoring Aria (Segmented — black background, matches C-NMC)...")
    aria_seg = eval_aria(model, mal_idx, "Segmented", args.imgsz)
    print("Scoring Acevedo (normal cells — specificity probe)...")
    acevedo = eval_acevedo(model, mal_idx, args.imgsz)

    report = {
        "model": "leukemia-v2 (C-NMC-trained), evaluated externally without any retraining",
        "reference_cnmc_internal": {"roc_auc": 0.857, "accuracy": 0.808,
                                    "sensitivity": 0.936, "specificity": 0.534},
        "aria_original": aria_orig,
        "aria_segmented": aria_seg,
        "acevedo_specificity": acevedo,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {OUT}\n")

    def line(tag, m):
        print(f"  {tag:22s} n={m['n']:5d}  acc={m['accuracy']:.3f}  AUC={m['roc_auc']:.3f}  "
              f"sens={m['sensitivity']:.3f}  spec={m['specificity']:.3f}")
    print("=== Aria (same-task external, blast vs benign) ===")
    line("Original (real bg)", aria_orig)
    line("Segmented (black bg)", aria_seg)
    print(f"\n=== Acevedo (normal-only specificity) ===")
    print(f"  overall specificity on {acevedo['n']} normal cells: {acevedo['overall_specificity']:.3f} "
          f"(false-alarm {acevedo['overall_false_positive_rate']:.3f})")
    print("  by cell type (false-positive rate):")
    for k, v in acevedo["by_cell_type"].items():
        flag = "  <- hard negative" if k == "lymphocyte" else ""
        print(f"    {k:14s} n={v['n']:5d}  FPR={v['false_positive_rate']:.3f}{flag}")


if __name__ == "__main__":
    main()
