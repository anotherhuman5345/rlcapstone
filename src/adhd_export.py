"""Export the ADHD EEG model to self-contained ONNX (for the web demo) and emit
sample EEG windows for the demo picker. Verifies ONNX/PyTorch parity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from adhd_train import CLASSES, EEGNet1D, PREP, OUT

SITE_SAMPLES = 6  # windows to bundle for the demo (3 per class)


def export_onnx():
    model = EEGNet1D()
    model.load_state_dict(torch.load(OUT / "adhd_best.pt", map_location="cpu"))
    model.eval()

    path = OUT / "adhd_model.onnx"
    torch.onnx.export(
        model, torch.zeros(1, 19, 256), str(path),
        input_names=["eeg"], output_names=["logits"],
        dynamic_axes={"eeg": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=18, verbose=False,
    )
    m = onnx.load(str(path))
    onnx.save(m, str(path), save_as_external_data=False)
    sidecar = path.with_suffix(".onnx.data")
    if sidecar.exists():
        sidecar.unlink()
    print(f"Exported {path} ({path.stat().st_size/1024:.0f} KB)")

    # parity
    d = np.load(PREP / "test.npz", allow_pickle=True)
    X = d["X"][:200].astype(np.float32)
    with torch.no_grad():
        pt = model(torch.from_numpy(X)).numpy()
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    on = sess.run(None, {"eeg": X})[0]
    diff = float(np.abs(pt - on).max())
    agree = int((pt.argmax(1) == on.argmax(1)).sum())
    print(f"Parity: max diff {diff:.2e}, argmax {agree}/{len(X)}")
    if diff > 1e-3 or agree != len(X):
        raise SystemExit("Parity FAILED")
    return model


def emit_samples():
    d = np.load(PREP / "test.npz", allow_pickle=True)
    X, y, subj = d["X"], d["y"], d["subj"].astype(str)
    rng = np.random.default_rng(5)
    samples = []
    for ci, cname in enumerate(CLASSES):
        idx = np.where(y == ci)[0]
        pick = rng.choice(idx, size=SITE_SAMPLES // 2, replace=False)
        for j, k in enumerate(pick):
            samples.append({
                "id": f"{cname}{j+1}",
                "trueClass": cname,
                "subject": subj[k],
                # [19][256] rounded to keep the JSON small
                "signal": [[round(float(v), 3) for v in ch] for ch in X[k]],
            })
    out = OUT / "adhd_samples.json"
    out.write_text(json.dumps({"classes": CLASSES, "samples": samples}))
    print(f"Wrote {len(samples)} sample windows to {out}")


if __name__ == "__main__":
    export_onnx()
    emit_samples()
