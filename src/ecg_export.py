"""Export the trained ECG 1D CNN to ONNX and verify parity with PyTorch.

The web demo runs this ONNX model in the browser via onnxruntime-web, so the
exported graph must match the PyTorch model's outputs. The model emits raw
logits (no softmax layer); the demo applies softmax in JS.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from ecg_train import CLASSES, ECGNet, PREP, OUT


def main() -> None:
    device = "cpu"
    model = ECGNet(len(CLASSES))
    model.load_state_dict(torch.load(OUT / "ecg_best.pt", map_location=device))
    model.eval()

    dummy = torch.zeros(1, 1, 260, dtype=torch.float32)
    onnx_path = OUT / "ecg_model.onnx"
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["beat"], output_names=["logits"],
        dynamic_axes={"beat": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=18,
        verbose=False,
    )
    # The dynamo exporter writes weights to a sidecar .data file, which
    # onnxruntime-web can't fetch. Re-save as a single self-contained file.
    model_onnx = onnx.load(str(onnx_path))  # loads external data alongside
    onnx.save(model_onnx, str(onnx_path), save_as_external_data=False)
    sidecar = onnx_path.with_suffix(".onnx.data")
    if sidecar.exists():
        sidecar.unlink()
    print(f"Exported {onnx_path} (self-contained, "
          f"{onnx_path.stat().st_size / 1024:.0f} KB)")

    # Parity check on real test beats.
    d = np.load(PREP / "test.npz")
    X = d["X"][:200].astype(np.float32)[:, None, :]  # [n,1,260]
    with torch.no_grad():
        torch_out = model(torch.from_numpy(X)).numpy()
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_out = sess.run(None, {"beat": X})[0]

    max_diff = float(np.abs(torch_out - onnx_out).max())
    agree = int((torch_out.argmax(1) == onnx_out.argmax(1)).sum())
    print(f"Parity on {len(X)} beats: max logit diff {max_diff:.2e}, "
          f"argmax agreement {agree}/{len(X)}")
    if max_diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity check FAILED")
    print("Parity OK")


if __name__ == "__main__":
    main()
