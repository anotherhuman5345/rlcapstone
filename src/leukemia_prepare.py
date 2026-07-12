"""Organize the ALL (Acute Lymphoblastic Leukemia) blood-smear images into a
YOLO-classification folder split.

Dataset: mehradaria/leukemia (Aria et al., 2021) — peripheral blood smear
images of a single white blood cell each, in four classes:
    Benign        - hematogones (non-cancerous look-alikes)
    Early / Pre / Pro - three maturation stages of B-cell ALL (malignant)

Honest limitation: this public release does not expose patient IDs (filenames
are just sequential per class), so we cannot guarantee that cells from one
patient stay within one split. The reported accuracy is therefore likely
optimistic — the C-NMC dataset (v2), which has patient IDs, is where we do the
rigorous patient-level split.

Output: data/leukemia/split/{train,val,test}/{benign,early,pre,pro}/
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "leukemia" / "Original"
DEST = ROOT / "data" / "leukemia" / "split"

# source subfolder -> our class name
CLASS_MAP = {"Benign": "benign", "Early": "early", "Pre": "pre", "Pro": "pro"}
VAL_FRAC, TEST_FRAC = 0.15, 0.15
SEED = 0


def main() -> None:
    rng = np.random.default_rng(SEED)
    if DEST.exists():
        shutil.rmtree(DEST)
    counts = {}
    for src_name, cls in CLASS_MAP.items():
        files = sorted((SRC / src_name).glob("*.jpg"))
        files = list(rng.permutation(files))
        n = len(files)
        n_val = round(n * VAL_FRAC)
        n_test = round(n * TEST_FRAC)
        parts = {
            "val": files[:n_val],
            "test": files[n_val:n_val + n_test],
            "train": files[n_val + n_test:],
        }
        for split, items in parts.items():
            out = DEST / split / cls
            out.mkdir(parents=True, exist_ok=True)
            for f in items:
                shutil.copy(f, out / f.name)
            counts[f"{split}/{cls}"] = len(items)

    print("Split complete:")
    for split in ("train", "val", "test"):
        row = {cls: counts[f"{split}/{cls}"] for cls in CLASS_MAP.values()}
        print(f"  {split}: {row}  total {sum(row.values())}")
    print(f"Saved to {DEST}")


if __name__ == "__main__":
    main()
