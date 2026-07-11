"""Train a binary skin-lesion classifier (benign vs malignant) on the prepared
HAM10000 split using Ultralytics YOLO classification.

Run `src/prepare_dataset.py` first to build data/ham10000/split/.

Why YOLO-cls for a capstone:
  * Transfer-learns from ImageNet, trains in minutes on an RTX 5060 Ti.
  * Exports straight to TensorFlow Lite (one line) for the Flutter app.

Class imbalance: malignant is ~19% of images. Ultralytics does not expose a
class-weight knob for classification, so we lean on augmentation + a decision
threshold tuned for sensitivity at evaluation time (see evaluate.py), which is
the metric that matters most for a cancer-screening aid.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ham10000" / "split"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="yolo11s-cls.pt", help="pretrained cls checkpoint")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--name", default="mole_cls")
    args = ap.parse_args()

    if not DATA.exists():
        raise SystemExit(
            f"{DATA} not found. Run: .venv\\Scripts\\python.exe src\\prepare_dataset.py"
        )

    model = YOLO(args.model)
    model.train(
        data=str(DATA),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=0,  # RTX 5060 Ti
        project=str(ROOT / "runs" / "classify"),
        name=args.name,
        # Augmentation to fight imbalance + generalise to phone photos.
        fliplr=0.5,
        flipud=0.5,
        degrees=180,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        erasing=0.2,
    )
    print("\nTraining complete. Best weights:")
    print(f"  {ROOT / 'runs' / 'classify' / args.name / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
