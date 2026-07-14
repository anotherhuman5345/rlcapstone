"""Prepare PAD-UFES-20 (smartphone clinical lesion photos) for binary
benign/malignant classification, split by patient.

Why this dataset: our HAM10000 model was trained only on dermatoscopic images
(specialist contact optics). The app receives ordinary smartphone photos, which
look different. PAD-UFES-20 is ~2,300 real smartphone clinical photos, so it lets
us (a) measure the domain gap and (b) train the model to handle phone photos.

Label mapping (6 classes -> binary):
    Malignant : BCC (basal cell carcinoma), SCC (squamous cell carcinoma),
                MEL (melanoma), ACK (actinic keratosis - pre-cancerous;
                grouped as malignant to match HAM's akiec label and to err
                toward caution in a screening tool)
    Benign    : NEV (nevus), SEK (seborrheic keratosis)

Split is by patient_id so no patient appears in more than one split (a patient
can have several lesions / images; leakage across splits would inflate scores).
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "pad_ufes_20"
HF = DATA / "hf"
IMAGES_ROOT = HF / "all_images"
METADATA = HF / "metadata.csv"
OUT = DATA / "split"

MALIGNANT = {"BCC", "SCC", "MEL", "ACK"}
BENIGN = {"NEV", "SEK"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--copy", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(METADATA.open(encoding="utf-8")))
    print(f"metadata rows: {len(rows)}")

    # Index images once (rglob per id is slow for 2k files).
    index = {p.name: p for p in IMAGES_ROOT.rglob("*.png")}
    print(f"images on disk: {len(index)}")

    by_patient: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    dropped = 0
    for r in rows:
        dx = r["diagnostic"].strip().upper()
        if dx in MALIGNANT:
            label = "malignant"
        elif dx in BENIGN:
            label = "benign"
        else:
            dropped += 1
            continue
        img = index.get(r["img_id"])
        if img is None:
            dropped += 1
            continue
        by_patient[r["patient_id"]].append((img, label))
    print(f"usable patients: {len(by_patient)}   dropped rows: {dropped}")

    # Stratify patients by whether they have any malignant lesion.
    rng = random.Random(args.seed)
    strata: dict[str, list[str]] = defaultdict(list)
    for pid, imgs in by_patient.items():
        key = "malignant" if any(l == "malignant" for _, l in imgs) else "benign"
        strata[key].append(pid)

    assign: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for key, pids in strata.items():
        rng.shuffle(pids)
        n = len(pids)
        n_test = int(n * args.test_frac)
        n_val = int(n * args.val_frac)
        assign["test"] += pids[:n_test]
        assign["val"] += pids[n_test:n_test + n_val]
        assign["train"] += pids[n_test + n_val:]

    if OUT.exists():
        shutil.rmtree(OUT)
    counts: dict[str, dict[str, int]] = {}
    for split, pids in assign.items():
        counts[split] = {"benign": 0, "malignant": 0}
        for pid in pids:
            for img, label in by_patient[pid]:
                dst_dir = OUT / split / label
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / img.name
                if args.copy:
                    shutil.copy2(img, dst)
                else:
                    try:
                        dst.hardlink_to(img)
                    except OSError:
                        shutil.copy2(img, dst)
                counts[split][label] += 1

    print("\nImage counts per split (PAD-UFES-20, smartphone photos):")
    for split in ("train", "val", "test"):
        b, m = counts[split]["benign"], counts[split]["malignant"]
        tot = b + m
        pct = 100 * m / tot if tot else 0
        print(f"  {split:5s}: {tot:4d}  (benign {b}, malignant {m} = {pct:.1f}%)")
    print(f"\nDone. PAD split at: {OUT}")


if __name__ == "__main__":
    main()
