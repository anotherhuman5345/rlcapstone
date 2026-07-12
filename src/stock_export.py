"""Export the stock risk MLP to self-contained ONNX (web) and verify parity."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from stock_train import RiskMLP, PREP, OUT

N_FEAT = 12


def main() -> None:
    model = RiskMLP(N_FEAT)
    model.load_state_dict(torch.load(OUT / "stock_best.pt", map_location="cpu"))
    model.eval()

    path = OUT / "stock_model.onnx"
    torch.onnx.export(model, torch.zeros(1, N_FEAT), str(path),
                      input_names=["features"], output_names=["logits"],
                      dynamic_axes={"features": {0: "batch"}, "logits": {0: "batch"}},
                      opset_version=18, verbose=False)
    m = onnx.load(str(path))
    onnx.save(m, str(path), save_as_external_data=False)
    sidecar = path.with_suffix(".onnx.data")
    if sidecar.exists():
        sidecar.unlink()
    print(f"Exported {path} ({path.stat().st_size/1024:.1f} KB)")

    d = np.load(PREP / "test.npz")
    X = d["X"][:300].astype(np.float32)
    with torch.no_grad():
        pt = model(torch.from_numpy(X)).numpy()
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    on = sess.run(None, {"features": X})[0]
    diff = float(np.abs(pt - on).max())
    agree = int((pt.argmax(1) == on.argmax(1)).sum())
    print(f"Parity: max diff {diff:.2e}, argmax {agree}/{len(X)}")
    if diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity FAILED")


if __name__ == "__main__":
    main()
