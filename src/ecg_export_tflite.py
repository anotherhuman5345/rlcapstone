"""Export the ECG 1D CNN to TensorFlow Lite for the Flutter app.

Mirrors the mole pipeline (PyTorch -> ONNX -> onnx2tf -> float32 TFLite). We
re-export a clean, static-batch ONNX with the classic exporter (opset 13,
dynamo off) because onnx2tf handles that graph more reliably than the newer
dynamo export. onnx2tf converts NCW -> NWC, so the resulting TFLite input is
[1, 260, 1] (the Flutter classifier feeds it that way).

Writes app_ecg/assets/ecg_classifier.tflite after verifying parity.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import torch

from ecg_train import CLASSES, ECGNet, PREP, OUT

APP_ASSETS = Path(__file__).resolve().parents[1] / "app_ecg" / "assets"


def main() -> None:
    model = ECGNet(len(CLASSES))
    model.load_state_dict(torch.load(OUT / "ecg_best.pt", map_location="cpu"))
    model.eval()

    clean_onnx = OUT / "ecg_for_tflite.onnx"
    print("[1/3] PyTorch -> ONNX (opset 13, static batch) ...")
    torch.onnx.export(
        model, torch.zeros(1, 1, 260), str(clean_onnx),
        input_names=["beat"], output_names=["logits"],
        opset_version=13, dynamo=False,
    )

    tfl_dir = OUT / "ecg_tflite_out"
    print("[2/3] ONNX -> TFLite (onnx2tf) ...")
    subprocess.run(
        [sys.executable, "-m", "onnx2tf", "-i", str(clean_onnx),
         "-o", str(tfl_dir), "-osd"],
        check=True,
    )
    tflite_path = tfl_dir / "ecg_for_tflite_float32.tflite"

    print("[3/3] Parity check TFLite vs PyTorch ...")
    interp = tf.lite.Interpreter(model_path=str(tflite_path))
    interp.allocate_tensors()
    inp = interp.get_input_details()[0]
    outp = interp.get_output_details()[0]
    print(f"      TFLite input shape: {inp['shape'].tolist()}")

    d = np.load(PREP / "test.npz")
    X = d["X"][:200].astype(np.float32)
    agree, max_diff = 0, 0.0
    for i in range(len(X)):
        beat = X[i]
        # feed in whatever layout the TFLite model expects
        shape = list(inp["shape"])
        tfl_in = beat.reshape(shape).astype(np.float32)
        interp.set_tensor(inp["index"], tfl_in)
        interp.invoke()
        tfl_out = interp.get_tensor(outp["index"]).ravel()
        with torch.no_grad():
            pt_out = model(torch.from_numpy(beat).reshape(1, 1, 260)).numpy().ravel()
        max_diff = max(max_diff, float(np.abs(tfl_out - pt_out).max()))
        agree += int(tfl_out.argmax() == pt_out.argmax())
    print(f"      max logit diff {max_diff:.2e}, argmax agreement {agree}/{len(X)}")
    if max_diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity FAILED — not copying to app")

    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite_path, APP_ASSETS / "ecg_classifier.tflite")
    (APP_ASSETS / "labels.txt").write_text("\n".join(CLASSES) + "\n")
    print(f"Parity OK. Copied model + labels to {APP_ASSETS}")


if __name__ == "__main__":
    main()
