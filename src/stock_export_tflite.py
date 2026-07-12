"""Export the stock risk MLP to TFLite for the Flutter app (input [1, 12])."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import torch

from stock_train import RiskMLP, PREP, OUT, CLASSES

APP_ASSETS = Path(__file__).resolve().parents[1] / "app_stock_risk" / "assets"
N_FEAT = 12


def main() -> None:
    model = RiskMLP(N_FEAT)
    model.load_state_dict(torch.load(OUT / "stock_best.pt", map_location="cpu"))
    model.eval()

    clean = OUT / "stock_for_tflite.onnx"
    torch.onnx.export(model, torch.zeros(1, N_FEAT), str(clean),
                      input_names=["features"], output_names=["logits"],
                      opset_version=13, dynamo=False)
    tfl_dir = OUT / "stock_tflite_out"
    subprocess.run([sys.executable, "-m", "onnx2tf", "-i", str(clean),
                    "-o", str(tfl_dir), "-osd"], check=True)
    tflite = tfl_dir / "stock_for_tflite_float32.tflite"

    interp = tf.lite.Interpreter(model_path=str(tflite))
    interp.allocate_tensors()
    inp, outp = interp.get_input_details()[0], interp.get_output_details()[0]
    print(f"TFLite input shape: {inp['shape'].tolist()}")
    d = np.load(PREP / "test.npz")
    X = d["X"][:300].astype(np.float32)
    agree, max_diff = 0, 0.0
    for i in range(len(X)):
        interp.set_tensor(inp["index"], X[i:i + 1])
        interp.invoke()
        tfl = interp.get_tensor(outp["index"]).ravel()
        with torch.no_grad():
            pt = model(torch.from_numpy(X[i:i + 1])).numpy().ravel()
        max_diff = max(max_diff, float(np.abs(tfl - pt).max()))
        agree += int(tfl.argmax() == pt.argmax())
    print(f"Parity: max diff {max_diff:.2e}, argmax {agree}/{len(X)}")
    if max_diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity FAILED")

    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite, APP_ASSETS / "stock_classifier.tflite")
    (APP_ASSETS / "labels.txt").write_text("\n".join(CLASSES) + "\n")
    print(f"Parity OK. Copied model + labels to {APP_ASSETS}")


if __name__ == "__main__":
    main()
