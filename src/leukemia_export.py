"""Verify the leukemia YOLO ONNX export against PyTorch and stage web/app assets.

Produces, under runs/classify/leukemia_cls/export/:
  * leukemia.onnx        - the YOLO cls ONNX (input [1,3,224,224], /255, softmax
                           already applied), copied for the browser demo
  * samples/             - a few real test cell images, 2 per class
  * leukemia_samples.json- {file, trueClass} manifest for the demo picker
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "classify" / "leukemia_cls"
TEST = ROOT / "data" / "leukemia" / "split" / "test"
EXPORT = RUN / "export"
CLASSES = ["benign", "early", "pre", "pro"]
PER_CLASS = 2


def preprocess(path, size=224):
    im = Image.open(path).convert("RGB").resize((size, size), Image.BILINEAR)
    x = np.asarray(im, dtype=np.float32) / 255.0
    return np.transpose(x, (2, 0, 1))[None]  # [1,3,224,224]


def main() -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    onnx_src = RUN / "weights" / "best.onnx"
    onnx_dst = EXPORT / "leukemia.onnx"
    shutil.copy(onnx_src, onnx_dst)

    model = YOLO(str(RUN / "weights" / "best.pt"))
    order = [{v: k for k, v in model.names.items()}[c] for c in CLASSES]
    sess = ort.InferenceSession(str(onnx_dst), providers=["CPUExecutionProvider"])

    # parity + sample selection
    samples_dir = EXPORT / "samples"
    if samples_dir.exists():
        shutil.rmtree(samples_dir)
    samples_dir.mkdir()
    # The browser demo uses the same plain resize+/255 as preprocess() here, so
    # the check that matters is whether the ONNX path predicts the same class as
    # the reference YOLO model (small logit diffs come from YOLO's internal
    # resize differing from a plain resize, not from the export).
    manifest, agree, checked = [], 0, 0
    for ci, cls in enumerate(CLASSES):
        files = sorted((TEST / cls).glob("*.jpg"))
        for j, f in enumerate(files):
            yolo = model.predict(Image.open(f).convert("RGB"), imgsz=224,
                                 verbose=False)[0].probs.data.cpu().numpy()[order]
            onnx = sess.run(None, {sess.get_inputs()[0].name: preprocess(f)})[0][0][order]
            agree += int(int(np.argmax(yolo)) == int(np.argmax(onnx)))
            checked += 1
            if j < PER_CLASS:
                name = f"{cls}{j+1}.jpg"
                shutil.copy(f, samples_dir / name)
                manifest.append({"file": name, "trueClass": cls})
            if checked >= 40 and j >= PER_CLASS:
                break
    print(f"ONNX vs YOLO argmax agreement: {agree}/{checked}")
    if agree < checked:
        raise SystemExit("Parity FAILED — predictions disagree")

    (EXPORT / "leukemia_samples.json").write_text(
        json.dumps({"classes": CLASSES, "samples": manifest}))
    print(f"Staged {len(manifest)} sample images + manifest in {EXPORT}")


if __name__ == "__main__":
    main()
