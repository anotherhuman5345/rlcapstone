"""Prepare the HAM10000 (ISIC collection 212) dataset for binary classification.

Reads the ISIC metadata CSV, maps each lesion to a binary label
(malignant vs benign), and organises the downloaded images into the folder
layout Ultralytics expects for classification:

    data/ham10000/split/
        train/{benign,malignant}/*.jpg
        val/{benign,malignant}/*.jpg
        test/{benign,malignant}/*.jpg

Key correctness points:
  * We split by `lesion_id`, not by image. The same physical lesion is often
    photographed several times; letting copies of one lesion fall into both
    train and test would leak information and inflate the scores.
  * Rows labelled "Indeterminate" in `diagnosis_1` are dropped.
  * Rows whose image file was not downloaded are skipped (with a count).
"""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

# --- paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ham10000"
IMAGES = DATA / "images"
METADATA = IMAGES / "metadata.csv"  # written by `isic image download` (UTF-8)
OUT = DATA / "split"

# --- label mapping -----------------------------------------------------------
# ISIC `diagnosis_1` is already a clean top-level label.
LABEL_MAP = {"Benign": "benign", "Malignant": "malignant"}
# "Indeterminate" and anything else are dropped.


def load_rows() -> list[dict]:
    with METADATA.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_index(rows: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Group (isic_id, label) tuples by lesion_id, keeping only rows whose
    image exists on disk and whose diagnosis maps to a binary label."""
    by_lesion: dict[str, list[tuple[str, str]]] = defaultdict(list)
    missing_image = 0
    dropped_label = 0
    for r in rows:
        label = LABEL_MAP.get(r.get("diagnosis_1", "").strip())
        if label is None:
            dropped_label += 1
            continue
        isic_id = r["isic_id"]
        if not (IMAGES / f"{isic_id}.jpg").exists():
            missing_image += 1
            continue
        # Some rows have no lesion_id; treat each such image as its own lesion.
        lesion = r.get("lesion_id") or f"__solo_{isic_id}"
        by_lesion[lesion].append((isic_id, label))
    print(f"  usable lesions: {len(by_lesion)}")
    print(f"  dropped (indeterminate/other label): {dropped_label}")
    print(f"  skipped (image not downloaded yet): {missing_image}")
    return by_lesion


def lesion_label(images: list[tuple[str, str]]) -> str:
    """A lesion is malignant if any of its images is labelled malignant."""
    return "malignant" if any(lbl == "malignant" for _, lbl in images) else "benign"


def split_lesions(
    by_lesion: dict[str, list[tuple[str, str]]],
    val_frac: float,
    test_frac: float,
    seed: int,
) -> dict[str, list[str]]:
    """Stratified split of *lesions* (not images) into train/val/test."""
    rng = random.Random(seed)
    strata: dict[str, list[str]] = defaultdict(list)
    for lesion, imgs in by_lesion.items():
        strata[lesion_label(imgs)].append(lesion)

    assignment: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for label, lesions in strata.items():
        rng.shuffle(lesions)
        n = len(lesions)
        n_test = int(n * test_frac)
        n_val = int(n * val_frac)
        assignment["test"] += lesions[:n_test]
        assignment["val"] += lesions[n_test : n_test + n_val]
        assignment["train"] += lesions[n_test + n_val :]
    return assignment


def materialise(
    assignment: dict[str, list[str]],
    by_lesion: dict[str, list[tuple[str, str]]],
    copy: bool,
) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    counts: dict[str, dict[str, int]] = {}
    for split, lesions in assignment.items():
        counts[split] = {"benign": 0, "malignant": 0}
        for lesion in lesions:
            for isic_id, label in by_lesion[lesion]:
                dst_dir = OUT / split / label
                dst_dir.mkdir(parents=True, exist_ok=True)
                src = IMAGES / f"{isic_id}.jpg"
                dst = dst_dir / f"{isic_id}.jpg"
                if copy:
                    shutil.copy2(src, dst)
                else:
                    # hardlink: instant, no extra disk. Falls back to copy
                    # across volumes.
                    try:
                        dst.hardlink_to(src)
                    except OSError:
                        shutil.copy2(src, dst)
                counts[split][label] += 1
    print("\n  Image counts per split:")
    for split in ("train", "val", "test"):
        b, m = counts[split]["benign"], counts[split]["malignant"]
        total = b + m
        pct = 100 * m / total if total else 0
        print(f"    {split:5s}: {total:5d}  (benign {b}, malignant {m} = {pct:.1f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of hardlinking (use if the app needs standalone files).",
    )
    args = ap.parse_args()

    print("Loading metadata...")
    rows = load_rows()
    print(f"  metadata rows: {len(rows)}")
    by_lesion = build_index(rows)
    assignment = split_lesions(by_lesion, args.val_frac, args.test_frac, args.seed)
    print(
        f"\n  Lesion split: train {len(assignment['train'])}, "
        f"val {len(assignment['val'])}, test {len(assignment['test'])}"
    )
    materialise(assignment, by_lesion, args.copy)
    print(f"\nDone. Dataset ready at: {OUT}")


if __name__ == "__main__":
    main()
