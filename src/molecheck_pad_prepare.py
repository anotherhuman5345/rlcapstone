"""Prepare PAD-UFES-20 (smartphone clinical photos) for the MoleCheck v2
domain-gap experiment.

v1 was trained on ISIC/HAM10000 *dermatoscopic* images (a clinical lens pressed
to the skin). The app, however, receives an ordinary *smartphone* photo. This
script prepares PAD-UFES-20 — 2,298 real smartphone photos of skin lesions from
a Brazilian screening program — so we can (a) measure how far the v1 model drops
on that out-of-domain data and (b) fine-tune to recover.

Label space is kept identical to v1:
  * malignant = BCC, SCC, MEL   (basal / squamous cell carcinoma, melanoma)
  * benign    = NEV, SEK        (nevus, seborrheic keratosis)
  * ACK (actinic keratosis) is EXCLUDED, because v1's ISIC labels marked actinic
    keratosis as "Indeterminate" and dropped it — the v1 model never learned it,
    so scoring it here would not be a fair test of the same model.

Correctness points:
  * We split by `patient_id`, not by image or lesion. A patient may have several
    lesions and several photos; letting one patient's photos fall into both train
    and test would leak identity and inflate scores (the same principle used in
    the ECG and leukemia-v2 projects).
  * A manifest CSV records each image's split, label, diagnosis, and Fitzpatrick
    skin type, so a later fairness audit (per-skin-tone metrics) needs no re-prep.

Output layout (what Ultralytics classification expects):
    data/pad_ufes_20/split/
        train/{benign,malignant}/*.png
        val/{benign,malignant}/*.png
        test/{benign,malignant}/*.png
        manifest.csv
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
METADATA = DATA / "metadata.csv"
IMAGE_ROOT = DATA / "hf" / "all_images"  # images live in imgs_part_{1,2,3}/ under here
OUT = DATA / "split"

# Diagnosis -> binary label. Anything absent here (i.e. ACK) is excluded.
LABEL_MAP = {
    "BCC": "malignant",  # basal cell carcinoma
    "SCC": "malignant",  # squamous cell carcinoma
    "MEL": "malignant",  # melanoma
    "NEV": "benign",     # nevus
    "SEK": "benign",     # seborrheic keratosis
}


def load_rows() -> list[dict]:
    with METADATA.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def index_images() -> dict[str, Path]:
    """Map img_id (filename) -> full path (images are nested in imgs_part_*/)."""
    return {p.name: p for p in IMAGE_ROOT.rglob("*.png")}


def build_index(rows: list[dict], img_index: dict[str, Path]):
    """Group usable images by patient. Returns:
      by_patient: patient_id -> list of (img_path, label, diagnostic, fitz)
    """
    by_patient: dict[str, list[tuple[Path, str, str, str]]] = defaultdict(list)
    dropped_label = missing_image = 0
    for r in rows:
        dx = (r.get("diagnostic") or "").strip()
        label = LABEL_MAP.get(dx)
        if label is None:  # ACK or anything unexpected
            dropped_label += 1
            continue
        img_id = r["img_id"]
        path = img_index.get(img_id)
        if path is None:
            missing_image += 1
            continue
        fitz = (r.get("fitspatrick") or "").strip() or "NA"
        by_patient[r["patient_id"]].append((path, label, dx, fitz))
    print(f"  usable patients: {len(by_patient)}")
    print(f"  dropped (ACK / unmapped diagnosis): {dropped_label}")
    print(f"  skipped (image file not found): {missing_image}")
    return by_patient


def patient_stratum(imgs: list[tuple[Path, str, str, str]]) -> str:
    """Stratify a patient by whether they have any malignant lesion, so the
    malignant rate is balanced across splits."""
    return "malignant" if any(lbl == "malignant" for _, lbl, _, _ in imgs) else "benign"


def split_patients(by_patient, val_frac, test_frac, seed) -> dict[str, list[str]]:
    rng = random.Random(seed)
    strata: dict[str, list[str]] = defaultdict(list)
    for pid, imgs in by_patient.items():
        strata[patient_stratum(imgs)].append(pid)

    assignment: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for _, pids in strata.items():
        rng.shuffle(pids)
        n = len(pids)
        n_test = int(n * test_frac)
        n_val = int(n * val_frac)
        assignment["test"] += pids[:n_test]
        assignment["val"] += pids[n_test : n_test + n_val]
        assignment["train"] += pids[n_test + n_val :]
    return assignment


def materialise(assignment, by_patient, copy: bool) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    counts: dict[str, dict[str, int]] = {}
    manifest_rows: list[dict] = []
    # Guard: no patient may appear in more than one split.
    seen: dict[str, str] = {}
    for split, pids in assignment.items():
        counts[split] = {"benign": 0, "malignant": 0}
        for pid in pids:
            assert seen.setdefault(pid, split) == split, f"patient {pid} in two splits!"
            for path, label, dx, fitz in by_patient[pid]:
                dst_dir = OUT / split / label
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / path.name
                if copy:
                    shutil.copy2(path, dst)
                else:
                    try:
                        dst.hardlink_to(path)
                    except OSError:
                        shutil.copy2(path, dst)
                counts[split][label] += 1
                manifest_rows.append({
                    "img_id": path.name, "split": split, "label": label,
                    "diagnostic": dx, "fitspatrick": fitz, "patient_id": pid,
                })

    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["img_id", "split", "label",
                                          "diagnostic", "fitspatrick", "patient_id"])
        w.writeheader()
        w.writerows(manifest_rows)

    print("\n  Image counts per split:")
    for split in ("train", "val", "test"):
        b, m = counts[split]["benign"], counts[split]["malignant"]
        total = b + m
        pct = 100 * m / total if total else 0
        print(f"    {split:5s}: {total:5d}  (benign {b}, malignant {m} = {pct:.1f}% malignant)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--copy", action="store_true",
                    help="Copy files instead of hardlinking.")
    args = ap.parse_args()

    print("Loading metadata...")
    rows = load_rows()
    print(f"  metadata rows: {len(rows)}")
    print("Indexing images...")
    img_index = index_images()
    print(f"  images on disk: {len(img_index)}")
    by_patient = build_index(rows, img_index)
    assignment = split_patients(by_patient, args.val_frac, args.test_frac, args.seed)
    print(f"\n  Patient split: train {len(assignment['train'])}, "
          f"val {len(assignment['val'])}, test {len(assignment['test'])}")
    materialise(assignment, by_patient, args.copy)
    print(f"\nDone. Dataset ready at: {OUT}")


if __name__ == "__main__":
    main()
