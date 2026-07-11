"""Export the trained YOLO classifier to TensorFlow Lite for the Flutter app.

Ultralytics 8.4's built-in LiteRT export only runs on Linux x86 / macOS, so on
Windows we go the portable route:

    best.pt  --(ultralytics)-->  best.onnx  --(onnx2tf)-->  *_float32.tflite

onnx2tf also converts the layout NCHW -> NHWC, so the resulting model takes a
[1, 224, 224, 3] input (what the Flutter classifier feeds it).

This script only produces the .tflite files. Run `verify_tflite.py` afterwards
to cross-check parity against the PyTorch model and copy the model into
app/assets/. (Two steps on purpose: never ship a converted model you haven't
verified.)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_DIR = ROOT / "runs" / "classify" / "mole_cls" / "weights"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", default=str(WEIGHTS_DIR / "best.pt"))
    ap.add_argument("--imgsz", type=int, default=224)
    args = ap.parse_args()

    weights = Path(args.weights)
    print("[1/2] Exporting PyTorch -> ONNX ...")
    onnx_path = YOLO(str(weights)).export(format="onnx", imgsz=args.imgsz, opset=13)
    onnx_path = Path(onnx_path)
    print(f"      wrote {onnx_path}")

    out_dir = weights.parent / "tflite_out"
    print("[2/2] Converting ONNX -> TFLite (onnx2tf) ...")
    # -osd also writes a SavedModel; the float32 .tflite is what we ship.
    subprocess.run(
        [sys.executable, "-m", "onnx2tf", "-i", str(onnx_path), "-o", str(out_dir), "-osd"],
        check=True,
    )
    tflite = out_dir / "best_float32.tflite"
    print(f"\nDone. TFLite model: {tflite}")
    print("Next: python src/verify_tflite.py   (checks parity, copies into app/assets)")


if __name__ == "__main__":
    main()
