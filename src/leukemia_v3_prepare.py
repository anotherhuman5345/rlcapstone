"""Assemble the multi-source training set for leukemia v3.

v2 (trained on C-NMC alone) collapsed on other labs' images (see
leukemia_ext_evaluate.py). The diagnosed cause: it over-fit C-NMC's black-
background / stain style. The principled fix is to train on MORE THAN ONE lab so
the model sees black AND real backgrounds and two staining pipelines.

v3 training data = C-NMC (Delhi, patient-split) + Aria (Tehran, both the Original
real-background and Segmented black-background versions). Validation and test stay
C-NMC-only and patient-disjoint, so the within-source headline is still honest and
directly comparable to v2's held-out 11 patients. Acevedo (Barcelona) is NOT added
here — it is deliberately held out as an unseen THIRD lab to test generalization.

Output: data/leukemia_v3/split/{train,val,test}/{all,hem}/
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CNMC = ROOT / "data" / "leukemia_cnmc" / "split"
ARIA = ROOT / "data" / "leukemia_ext" / "aria"
OUT = ROOT / "data" / "leukemia_v3" / "split"

# Aria class -> binary target (C-NMC label space: all=leukemic, hem=normal)
ARIA_MAP = {"Early": "all", "Pre": "all", "Pro": "all", "Benign": "hem"}


def link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        dst.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def copy_cnmc(counts: dict) -> None:
    for split in ("train", "val", "test"):
        for cls in ("all", "hem"):
            srcdir = CNMC / split / cls
            for p in srcdir.glob("*.*"):
                link(p, OUT / split / cls / p.name)
                counts[split][cls] += 1


def add_aria(counts: dict) -> None:
    # Aria goes into TRAIN only (val/test remain C-NMC patient-disjoint).
    for variant in ("Original", "Segmented"):
        for cls_dir in sorted((ARIA / variant).iterdir()):
            if not cls_dir.is_dir():
                continue
            target = ARIA_MAP.get(cls_dir.name)
            if target is None:
                continue
            for p in cls_dir.glob("*.*"):
                dst = OUT / "train" / target / f"aria_{variant}_{cls_dir.name}_{p.name}"
                link(p, dst)
                counts["train"][target] += 1


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    counts = {s: {"all": 0, "hem": 0} for s in ("train", "val", "test")}
    print("Linking C-NMC (patient-split)...")
    copy_cnmc(counts)
    print("Adding Aria (Original + Segmented) to train...")
    add_aria(counts)

    print("\n  Split (all = leukemic, hem = normal):")
    for s in ("train", "val", "test"):
        a, h = counts[s]["all"], counts[s]["hem"]
        print(f"    {s:5s}: all {a:6d}  hem {h:6d}  (total {a + h}, {100*h/(a+h):.1f}% normal)")
    print(f"\n  train sources: C-NMC (Delhi) + Aria (Tehran); val/test: C-NMC held-out patients only.")
    print(f"  Acevedo (Barcelona) deliberately NOT included — held out as an unseen 3rd lab.")
    print(f"\nDone. Dataset ready at: {OUT}")


if __name__ == "__main__":
    main()
