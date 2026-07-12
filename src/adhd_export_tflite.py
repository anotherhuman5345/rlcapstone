"""Export the ADHD EEG model to TensorFlow Lite for the Flutter app.

PyTorch -> ONNX (opset 13, dynamo off) -> onnx2tf -> float32 TFLite. onnx2tf
converts NCW -> NWC, so the TFLite input is [1, 256, 19]. Verifies parity, then
copies model + labels into app_adhd_eeg/assets.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import torch

from adhd_train import CLASSES, EEGNet1D, PREP, OUT

APP_ASSETS = Path(__file__).resolve().parents[1] / "app_adhd_eeg" / "assets"


def main() -> None:
    model = EEGNet1D()
    model.load_state_dict(torch.load(OUT / "adhd_best.pt", map_location="cpu"))
    model.eval()

    clean = OUT / "adhd_for_tflite.onnx"
    print("[1/3] PyTorch -> ONNX ...")
    torch.onnx.export(model, torch.zeros(1, 19, 256), str(clean),
                      input_names=["eeg"], output_names=["logits"],
                      opset_version=13, dynamo=False)

    tfl_dir = OUT / "adhd_tflite_out"
    print("[2/3] ONNX -> TFLite (onnx2tf) ...")
    subprocess.run([sys.executable, "-m", "onnx2tf", "-i", str(clean),
                    "-o", str(tfl_dir), "-osd"], check=True)
    tflite = tfl_dir / "adhd_for_tflite_float32.tflite"

    print("[3/3] Parity check ...")
    interp = tf.lite.Interpreter(model_path=str(tflite))
    interp.allocate_tensors()
    inp, outp = interp.get_input_details()[0], interp.get_output_details()[0]
    print(f"      TFLite input shape: {inp['shape'].tolist()}")

    d = np.load(PREP / "test.npz", allow_pickle=True)
    X = d["X"][:200].astype(np.float32)
    agree, max_diff = 0, 0.0
    shape = list(inp["shape"])
    for i in range(len(X)):
        w = X[i]  # [19, 256]
        tfl_in = np.transpose(w, (1, 0)).reshape(shape).astype(np.float32) \
            if shape[-1] == 19 else w.reshape(shape).astype(np.float32)
        interp.set_tensor(inp["index"], tfl_in)
        interp.invoke()
        tfl_out = interp.get_tensor(outp["index"]).ravel()
        with torch.no_grad():
            pt_out = model(torch.from_numpy(w).reshape(1, 19, 256)).numpy().ravel()
        max_diff = max(max_diff, float(np.abs(tfl_out - pt_out).max()))
        agree += int(tfl_out.argmax() == pt_out.argmax())
    print(f"      max diff {max_diff:.2e}, argmax {agree}/{len(X)}")
    if max_diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity FAILED")

    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite, APP_ASSETS / "adhd_classifier.tflite")
    (APP_ASSETS / "labels.txt").write_text("\n".join(CLASSES) + "\n")
    print(f"Parity OK. Copied model + labels to {APP_ASSETS}")


if __name__ == "__main__":
    main()
