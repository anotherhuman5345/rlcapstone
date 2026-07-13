"""Fairness audit for MoleCheck v2 — performance broken out by Fitzpatrick skin type.

Runs the v2 (smartphone-trained) model on the PAD-UFES-20 test split and reports
sensitivity/specificity per Fitzpatrick group, applying a SINGLE global decision
threshold to every group (the correct way to test for disparate outcomes: one
decision rule, measure whether the errors fall unevenly).

Two structural limitations of this dataset shape what can honestly be claimed,
and the script reports them rather than papering over them:
  * PAD-UFES-20 is a Brazilian cohort with almost no darker skin (Fitzpatrick V/VI
    are nearly absent), so dark-skin performance cannot be evaluated here — which is
    itself the equity gap dermatology AI is criticised for.
  * Skin type was recorded mainly for biopsied (mostly malignant) lesions; the
    benign cases largely have no Fitzpatrick label. Per-skin-type SPECIFICITY is
    therefore barely measurable, while sensitivity (recall on malignant) is.

Writes trained_models/molecheck-v2/fairness.json.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "pad_ufes_20" / "split" / "manifest.csv"
TEST_DIR = ROOT / "data" / "pad_ufes_20" / "split" / "test"
V2 = ROOT / "runs" / "classify" / "molecheck_pad_v2" / "weights" / "best.pt"
OUT = ROOT / "trained_models" / "molecheck-v2" / "fairness.json"

# Fitzpatrick value -> reporting bucket. PAD stores types as "1.0".."6.0".
BUCKETS = {
    "1.0": "I–II (lighter)", "2.0": "I–II (lighter)",
    "3.0": "III–IV (medium)", "4.0": "III–IV (medium)",
    "5.0": "V–VI (darker)", "6.0": "V–VI (darker)",
    "NA": "Unknown (unrecorded)", "": "Unknown (unrecorded)",
}
BUCKET_ORDER = ["I–II (lighter)", "III–IV (medium)", "V–VI (darker)", "Unknown (unrecorded)"]
MIN_FOR_METRIC = 10  # below this a rate is reported but flagged as unreliable


def malignant_index(model: YOLO) -> int:
    for idx, name in model.names.items():
        if name == "malignant":
            return idx
    raise SystemExit(f"'malignant' not in classes: {model.names}")


def rate(num: int, den: int):
    return round(num / den, 4) if den else None


def summarise(scores, y_true, thr):
    pred = (scores >= thr).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    n_mal, n_ben = tp + fn, tn + fp
    return {
        "n": int(len(y_true)), "n_malignant": n_mal, "n_benign": n_ben,
        "sensitivity": rate(tp, n_mal), "specificity": rate(tn, n_ben),
        "sensitivity_reliable": n_mal >= MIN_FOR_METRIC,
        "specificity_reliable": n_ben >= MIN_FOR_METRIC,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--target-sensitivity", type=float, default=0.90)
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(open(MANIFEST, encoding="utf-8")) if r["split"] == "test"]
    model = YOLO(str(V2))
    mal_idx = malignant_index(model)

    scores, y_true, buckets = [], [], []
    for r in rows:
        label = r["label"]
        img = TEST_DIR / label / r["img_id"]
        res = model.predict(Image.open(img).convert("RGB"), imgsz=args.imgsz, verbose=False)[0]
        scores.append(float(res.probs.data[mal_idx]))
        y_true.append(1 if label == "malignant" else 0)
        buckets.append(BUCKETS.get(r["fitspatrick"], "Unknown (unrecorded)"))
    scores, y_true, buckets = np.array(scores), np.array(y_true), np.array(buckets)

    # Single global threshold reaching the target sensitivity over the whole test set.
    mal_scores = np.sort(scores[y_true == 1])
    k = int(np.floor((1 - args.target_sensitivity) * len(mal_scores)))
    thr = float(mal_scores[min(k, len(mal_scores) - 1)])

    groups = {}
    for b in BUCKET_ORDER:
        m = buckets == b
        if m.sum() == 0:
            continue
        groups[b] = summarise(scores[m], y_true[m], thr)

    report = {
        "model": "molecheck-v2 (smartphone-fine-tuned)",
        "test_set": "PAD-UFES-20 patient-level test split",
        "global_threshold": round(thr, 4),
        "note_threshold": "One global threshold (targeting 90% sensitivity overall) applied to every group.",
        "overall": summarise(scores, y_true, thr),
        "by_skin_type": groups,
        "limitations": [
            "Fitzpatrick V–VI (darker skin) is nearly absent from this Brazilian cohort, so dark-skin "
            "performance cannot be evaluated here — the central equity gap in dermatology AI.",
            "Skin type was recorded mainly for biopsied (mostly malignant) lesions; most benign cases "
            "have no Fitzpatrick label. Per-skin-type specificity is therefore unreliable (few benign "
            "samples per group), while per-skin-type sensitivity is the meaningful comparison.",
            f"Any rate over fewer than {MIN_FOR_METRIC} cases is flagged unreliable in the JSON.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT}\n")

    print(f"Global threshold: {thr:.4f}  (targets {args.target_sensitivity:.0%} sensitivity overall)")
    print(f"{'Skin type':<24} {'n':>4} {'mal':>4} {'ben':>4} {'sens':>7} {'spec':>7}")
    for b in BUCKET_ORDER:
        g = groups.get(b)
        if not g:
            continue
        s = f"{g['sensitivity']:.3f}" if g["sensitivity"] is not None else "  —  "
        sp = f"{g['specificity']:.3f}" if g["specificity"] is not None else "  —  "
        sflag = "" if g["sensitivity_reliable"] else "*"
        spflag = "" if g["specificity_reliable"] else "*"
        print(f"{b:<24} {g['n']:>4} {g['n_malignant']:>4} {g['n_benign']:>4} "
              f"{s:>6}{sflag:<1} {sp:>6}{spflag:<1}")
    print("\n* = fewer than 10 cases in that cell; rate is not reliable.")


if __name__ == "__main__":
    main()
