"""Patient-level split of the C-NMC 2019 leukemia dataset (the v2 experiment).

This is the rigorous follow-up to the v1 leukemia classifier. The v1 dataset
(Aria et al., 2021) has no patient IDs, so cells from one patient can leak across
the train/test split and inflate accuracy. C-NMC 2019 encodes the subject ID in
every filename, so here we hold out **entire patients** — the honest protocol.

Dataset: andrewmvd/leukemia-classification -> C-NMC_Leukemia/training_data/
    fold_0, fold_1, fold_2, each with:
        all/  malignant B-ALL cells   (filenames like UID_<n>_<i>_<c>_all.bmp)
        hem/  healthy 'hematogone'    (filenames like UID_H<n>_<i>_<c>_hem.bmp)

Binary task: all (malignant) vs hem (normal). The subject token after 'UID_'
identifies the patient; a patient is entirely 'all' or entirely 'hem'.

Output: data/leukemia_cnmc/split/{train,val,test}/{all,hem}/  (patient-disjoint)
"""

from __future__ import annotations

import re
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "leukemia_cnmc" / "C-NMC_Leukemia" / "training_data"
DEST = ROOT / "data" / "leukemia_cnmc" / "split"
FOLDS = ["fold_0", "fold_1", "fold_2"]
CLASSES = ["all", "hem"]
VAL_FRAC, TEST_FRAC = 0.15, 0.15
SEED = 0
SUBJECT_RE = re.compile(r"UID_([A-Za-z0-9]+)_", re.IGNORECASE)


def subject_of(name: str) -> str:
    m = SUBJECT_RE.match(name)
    if not m:
        raise ValueError(f"cannot parse subject id from {name!r}")
    return m.group(1)


def collect() -> dict:
    """{class: {subject: [paths]}} across all folds."""
    by_cls_subj = {c: defaultdict(list) for c in CLASSES}
    for fold in FOLDS:
        for cls in CLASSES:
            d = SRC / fold / cls
            for p in d.glob("*.bmp"):
                by_cls_subj[cls][subject_of(p.name)].append(p)
    return by_cls_subj


def split_subjects(subjects: list, rng) -> dict:
    subs = list(rng.permutation(subjects))
    n = len(subs)
    n_val = round(n * VAL_FRAC)
    n_test = round(n * TEST_FRAC)
    return {
        "val": subs[:n_val],
        "test": subs[n_val:n_val + n_test],
        "train": subs[n_val + n_test:],
    }


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found. Download the C-NMC dataset first.")
    rng = np.random.default_rng(SEED)
    if DEST.exists():
        shutil.rmtree(DEST)

    data = collect()
    assignment = {}   # subject -> split, per class (subjects unique within class)
    img_counts = {s: {c: 0 for c in CLASSES} for s in ("train", "val", "test")}
    subj_counts = {s: {c: 0 for c in CLASSES} for s in ("train", "val", "test")}

    for cls in CLASSES:
        subjects = sorted(data[cls].keys())
        parts = split_subjects(subjects, rng)
        for split, subs in parts.items():
            subj_counts[split][cls] = len(subs)
            for subj in subs:
                assignment[(cls, subj)] = split
                out = DEST / split / cls
                out.mkdir(parents=True, exist_ok=True)
                for p in data[cls][subj]:
                    shutil.copy(p, out / p.name)
                    img_counts[split][cls] += 1

    # integrity: no subject in more than one split (within a class)
    seen = defaultdict(set)
    for (cls, subj), split in assignment.items():
        seen[(cls, subj)].add(split)
    leaks = {k: v for k, v in seen.items() if len(v) > 1}
    assert not leaks, f"patient leak detected: {leaks}"

    print("C-NMC patient-level split (v2) — patient-disjoint train/val/test\n")
    print(f"{'split':6s}  {'all imgs':>8s} {'all pts':>7s}  {'hem imgs':>8s} {'hem pts':>7s}")
    for s in ("train", "val", "test"):
        print(f"{s:6s}  {img_counts[s]['all']:8d} {subj_counts[s]['all']:7d}  "
              f"{img_counts[s]['hem']:8d} {subj_counts[s]['hem']:7d}")
    tot_pts = sum(subj_counts[s][c] for s in subj_counts for c in CLASSES)
    tot_imgs = sum(img_counts[s][c] for s in img_counts for c in CLASSES)
    print(f"\nTotal: {tot_pts} patients, {tot_imgs} images. No patient spans splits.")
    print(f"Saved to {DEST}")


if __name__ == "__main__":
    main()
