"""Pick a handful of real MIT-BIH test beats for the website demo's sample picker.

Beats come from the DS2 test set (patients the model never trained on). We keep
the model-input window (260 samples, z-normalised) plus the cardiologist's true
label and the source record id. The demo draws the waveform and runs the ONNX
model live, so we deliberately include the hard classes (S, F) too — the demo
should show honest results, including the misses.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ecg_train import CLASSES, PREP

OUT = Path(__file__).resolve().parents[1] / "runs" / "ecg" / "ecg_samples.json"
PER_CLASS = 3
SEED = 3


def main() -> None:
    d = np.load(PREP / "test.npz")
    X, y = d["X"], d["y"]
    rng = np.random.default_rng(SEED)

    samples = []
    for ci, cname in enumerate(CLASSES):
        idx = np.where(y == ci)[0]
        pick = rng.choice(idx, size=min(PER_CLASS, len(idx)), replace=False)
        for j, k in enumerate(pick):
            samples.append({
                "id": f"{cname}{j + 1}",
                "trueClass": cname,
                "signal": [round(float(v), 4) for v in X[k]],
            })

    OUT.write_text(json.dumps({"classes": CLASSES, "samples": samples}))
    print(f"Wrote {len(samples)} sample beats to {OUT}")
    for s in samples:
        print(f"  {s['id']}: true={s['trueClass']}  {len(s['signal'])} samples")


if __name__ == "__main__":
    main()
