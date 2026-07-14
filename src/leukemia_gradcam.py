"""Grad-CAM for the leukemia YOLO11s-cls model.

Overlays a heatmap of where the model looks when it calls a cell leukemic. This is
the interpretability check that the whole project's honesty thesis needs: it shows
whether the model attends to the cell's nucleus/cytoplasm (real morphology) or to
the slide background / stain (the artifact that made v1's 99.8% a lie).

Hooks the last backbone feature map (model.model[-2], a 7x7x512 map at 224 input),
takes the gradient of the leukemic logit w.r.t. that map, and forms the standard
Grad-CAM weighting. Saves side-by-side original|overlay PNGs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "trained_models" / "leukemia-v3" / "gradcam"


def preprocess(path: Path, imgsz: int) -> tuple[torch.Tensor, np.ndarray]:
    im = Image.open(path).convert("RGB").resize((imgsz, imgsz))
    arr = np.asarray(im, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # 1,3,H,W
    return t, np.asarray(im)


def gradcam_for(net, target_layer, x: torch.Tensor, class_idx: int) -> np.ndarray:
    acts, grads = {}, {}

    def fwd(_m, _i, o):
        acts["a"] = o.detach()

    def bwd(_m, gin, gout):
        grads["g"] = gout[0].detach()

    for p in net.parameters():
        p.requires_grad_(True)
    h1 = target_layer.register_forward_hook(fwd)
    h2 = target_layer.register_full_backward_hook(bwd)
    try:
        with torch.enable_grad():
            x = x.clone().to(next(net.parameters()).device).requires_grad_(True)
            net.zero_grad()
            logits = net(x)
            if isinstance(logits, (list, tuple)):
                logits = logits[0]
            logits = logits.reshape(logits.shape[0], -1)
            logits[0, class_idx].backward()
        a, g = acts["a"][0], grads["g"][0]           # C,h,w
        weights = g.mean(dim=(1, 2))                  # C
        cam = F.relu((weights[:, None, None] * a).sum(0))  # h,w
        cam = cam / (cam.max() + 1e-8)
        cam = F.interpolate(cam[None, None], size=(x.shape[2], x.shape[3]),
                            mode="bilinear", align_corners=False)[0, 0]
        return cam.cpu().numpy()
    finally:
        h1.remove()
        h2.remove()


def overlay(rgb: np.ndarray, cam: np.ndarray) -> np.ndarray:
    # simple red heatmap over a dimmed grayscale base
    heat = np.stack([cam, np.zeros_like(cam), 1 - cam], axis=-1)  # red=high, blue=low
    heat = (heat * 255).astype(np.uint8)
    base = (rgb * 0.5).astype(np.uint8)
    return np.clip(base + (heat * 0.5), 0, 255).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", default=str(ROOT / "runs/classify/leukemia_v3/weights/best.pt"))
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--images", nargs="*", help="specific image paths; default picks a few examples")
    args = ap.parse_args()

    model = YOLO(args.weights)
    net = model.model.eval()
    mal_idx = [i for i, n in model.names.items() if n == "all"][0]
    target = net.model[-2]  # last backbone block before the classify head

    if args.images:
        paths = [Path(p) for p in args.images]
    else:
        # a couple of leukemic + normal cells from the C-NMC test set, if present
        base = ROOT / "data" / "leukemia_cnmc" / "split" / "test"
        paths = (list((base / "all").glob("*.bmp"))[:3] + list((base / "hem").glob("*.bmp"))[:3])

    OUT.mkdir(parents=True, exist_ok=True)
    for p in paths:
        x, rgb = preprocess(p, args.imgsz)
        cam = gradcam_for(net, target, x, mal_idx)
        combo = np.concatenate([rgb, overlay(rgb, cam)], axis=1)
        dst = OUT / f"{p.stem}_gradcam.png"
        Image.fromarray(combo).save(dst)
        with torch.no_grad():
            p_leuk = float(model.predict(Image.open(p).convert("RGB"), imgsz=args.imgsz,
                                         verbose=False)[0].probs.data[mal_idx])
        print(f"  {p.name:28s} P(leukemic)={p_leuk:.3f}  -> {dst.name}")
    print(f"\nWrote {len(paths)} Grad-CAM overlays to {OUT}")


if __name__ == "__main__":
    main()
