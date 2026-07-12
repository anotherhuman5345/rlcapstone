"""Build a combined training set from HAM10000 (dermatoscopic) + PAD-UFES-20
(smartphone), so the model learns both image types.

Only train/ and val/ are merged. The two test sets are kept separate on purpose:
we evaluate on the HAM test set (dermatoscopic) and the PAD test set (phone)
independently, to see the effect on each domain rather than blurring them.

Run prepare_dataset.py and prepare_pad.py first.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAM = ROOT / "data" / "ham10000" / "split"
PAD = ROOT / "data" / "pad_ufes_20" / "split"
OUT = ROOT / "data" / "combined" / "split"


def link_all(src_split: Path, tag: str) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for split in ("train", "val"):
        counts.setdefault(split, {"benign": 0, "malignant": 0})
        for label in ("benign", "malignant"):
            src_dir = src_split / split / label
            if not src_dir.exists():
                continue
            dst_dir = OUT / split / label
            dst_dir.mkdir(parents=True, exist_ok=True)
            for img in src_dir.iterdir():
                # Prefix with tag to avoid name collisions between datasets.
                dst = dst_dir / f"{tag}_{img.name}"
                if dst.exists():
                    continue
                try:
                    dst.hardlink_to(img)
                except OSError:
                    shutil.copy2(img, dst)
                counts[split][label] += 1
    return counts


def main() -> None:
    if not HAM.exists():
        raise SystemExit(f"{HAM} missing - run src/prepare_dataset.py")
    if not PAD.exists():
        raise SystemExit(f"{PAD} missing - run src/prepare_pad.py")
    if OUT.exists():
        shutil.rmtree(OUT)

    ch = link_all(HAM, "ham")
    cp = link_all(PAD, "pad")

    print("Combined training set (train/val merged; test sets kept separate):")
    for split in ("train", "val"):
        b = ch[split]["benign"] + cp[split]["benign"]
        m = ch[split]["malignant"] + cp[split]["malignant"]
        tot = b + m
        pct = 100 * m / tot if tot else 0
        print(f"  {split:5s}: {tot:5d}  (benign {b}, malignant {m} = {pct:.1f}%)"
              f"   [HAM {ch[split]['benign']+ch[split]['malignant']}, "
              f"PAD {cp[split]['benign']+cp[split]['malignant']}]")
    print(f"\nDone. Combined dataset at: {OUT}")


if __name__ == "__main__":
    main()
