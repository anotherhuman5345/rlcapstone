"""Cross-check the exported TFLite model against the PyTorch model, and copy the
chosen model into the Flutter app's assets.

Run after onnx2tf has produced the TFLite files. Confirms that conversion did
not silently break the model (layout / normalisation mismatches are the usual
culprits) by comparing malignant probabilities on real test images.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "data" / "ham10000" / "split" / "test"
WEIGHTS_DIR = ROOT / "runs" / "classify" / "mole_cls" / "weights"
APP_ASSETS = ROOT / "app" / "assets"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pt", default=str(WEIGHTS_DIR / "best.pt"))
    ap.add_argument(
        "--tflite",
        default=str(WEIGHTS_DIR / "tflite_out" / "best_float32.tflite"),
        help="TFLite file to verify and ship (float32 is the canonical export)",
    )
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--n", type=int, default=16, help="images per class to check")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="threshold used only for the parity decision-agreement report")
    args = ap.parse_args()

    model = YOLO(args.pt)
    mal_matches = [i for i, n in model.names.items() if n == "malignant"]
    if not mal_matches:
        raise SystemExit(f"'malignant' not found in model classes: {model.names}")
    mal_idx = mal_matches[0]

    interp = Interpreter(model_path=args.tflite)
    interp.allocate_tensors()
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]
    nchw = inp["shape"][1] == 3
    print(f"TFLite input shape: {inp['shape']}  ({'NCHW' if nchw else 'NHWC'})")

    paths = (
        list((TEST / "malignant").glob("*.jpg"))[: args.n]
        + list((TEST / "benign").glob("*.jpg"))[: args.n]
    )
    max_diff = 0.0
    agree = 0
    for p in paths:
        img = Image.open(p).convert("RGB").resize((args.imgsz, args.imgsz))
        arr = np.asarray(img, dtype=np.float32)[None] / 255.0
        if nchw:
            arr = arr.transpose(0, 3, 1, 2)
        interp.set_tensor(inp["index"], arr.astype(inp["dtype"]))
        interp.invoke()
        tfl = float(interp.get_tensor(out["index"]).flatten()[mal_idx])
        pt = float(model.predict(img, imgsz=args.imgsz, verbose=False)[0].probs.data[mal_idx])
        max_diff = max(max_diff, abs(tfl - pt))
        if (tfl >= args.threshold) == (pt >= args.threshold):
            agree += 1
    print(f"Checked {len(paths)} images")
    print(f"Max abs prob difference (PyTorch vs TFLite): {max_diff:.4f}")
    print(f"Decision agreement @{args.threshold:g}: {agree}/{len(paths)}")

    if max_diff > 0.05:
        raise SystemExit("Parity check FAILED — difference too large, do not ship this model.")

    # Copy into the app.
    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    dst = APP_ASSETS / "mole_classifier.tflite"
    dst.write_bytes(Path(args.tflite).read_bytes())
    labels = [model.names[i] for i in sorted(model.names)]
    (APP_ASSETS / "labels.txt").write_text("\n".join(labels), encoding="utf-8")
    print(f"\nParity OK. Copied model -> {dst}")
    print(f"Labels: {labels}")


if __name__ == "__main__":
    main()
