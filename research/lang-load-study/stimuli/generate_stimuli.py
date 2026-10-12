"""Generate all study images and the manifest that records where each target is.

Part A, search scenes: original cluttered scenes (no copyrighted puzzle art).
  The target is a small RED UMBRELLA. Distractors share its color (red circles,
  red triangles) or its shape (umbrellas in other colors), which makes this a
  "conjunction search": the target cannot pop out on color or shape alone.

Part B, scans: a small, low-contrast monkey is planted in a grayscale image.
  By default this script makes SYNTHETIC placeholder "scans" so the platform
  can be built and tested. For the real study, put de-identified images
  supplied by the lab (after IRB approval) in stimuli/real_scans/ and run with
  --real-scans; the monkey is planted into those instead.

Usage:
    python stimuli/generate_stimuli.py               # placeholders
    python stimuli/generate_stimuli.py --real-scans  # lab images
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
REAL = HERE / "real_scans"

W, H = 1200, 800
SEARCH_COLORS = [(214, 40, 40), (40, 90, 200), (40, 150, 70), (235, 190, 30),
                 (140, 70, 170), (240, 130, 40), (90, 90, 90), (30, 160, 170)]
RED = (214, 40, 40)


def draw_umbrella(d, cx, cy, s, color):
    d.pieslice([cx - s, cy - s, cx + s, cy + s], 180, 360, fill=color, outline=(30, 30, 30))
    d.line([cx, cy, cx, cy + s * 1.1], fill=(30, 30, 30), width=max(2, s // 6))
    d.arc([cx, cy + s * 0.8, cx + s * 0.5, cy + s * 1.3], 0, 180, fill=(30, 30, 30), width=max(2, s // 6))


def draw_shape(d, kind, cx, cy, s, color):
    if kind == "circle":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=color, outline=(30, 30, 30))
    elif kind == "triangle":
        d.polygon([(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)], fill=color, outline=(30, 30, 30))
    elif kind == "square":
        d.rectangle([cx - s, cy - s, cx + s, cy + s], fill=color, outline=(30, 30, 30))
    elif kind == "umbrella":
        draw_umbrella(d, cx, cy, s, color)


def search_scene(rng, n_distractors=260, target_size=13):
    img = Image.new("RGB", (W, H), (236, 232, 222))
    d = ImageDraw.Draw(img)
    margin = 40
    tx, ty = rng.randint(margin, W - margin), rng.randint(margin, H - margin)
    for _ in range(n_distractors):
        x, y = rng.randint(10, W - 10), rng.randint(10, H - 10)
        if math.hypot(x - tx, y - ty) < target_size * 3:
            continue  # keep the target unobstructed
        s = rng.randint(9, 18)
        roll = rng.random()
        if roll < 0.30:      # same shape, wrong color
            draw_shape(d, "umbrella", x, y, s, rng.choice([c for c in SEARCH_COLORS if c != RED]))
        elif roll < 0.55:    # right color, wrong shape
            draw_shape(d, rng.choice(["circle", "triangle", "square"]), x, y, s, RED)
        else:                # everything else
            draw_shape(d, rng.choice(["circle", "triangle", "square"]), x, y, s,
                       rng.choice([c for c in SEARCH_COLORS if c != RED]))
    draw_umbrella(d, tx, ty, target_size, RED)
    return img, tx, ty, target_size * 1.4


def synthetic_scan(rng):
    """A placeholder that looks vaguely like a chest image. Not a real scan."""
    nrng = np.random.default_rng(rng.randint(0, 2**31))
    base = nrng.normal(60, 25, (H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    for cx in (W * 0.33, W * 0.67):  # two "lung fields"
        mask = ((xx - cx) / (W * 0.17)) ** 2 + ((yy - H * 0.5) / (H * 0.38)) ** 2 < 1
        base[mask] += 70
    for _ in range(25):  # soft structures
        bx, by, r = nrng.integers(0, W), nrng.integers(0, H), nrng.integers(10, 60)
        base[((xx - bx) ** 2 + (yy - by) ** 2) < r ** 2] += nrng.normal(25, 10)
    img = Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "L")
    return img.filter(ImageFilter.GaussianBlur(4))


def plant_monkey(img, rng, size=22, contrast=38):
    """Draw a small original monkey silhouette, slightly brighter than its surroundings."""
    img = img.convert("L")
    w, h = img.size
    margin = size * 3
    mx, my = rng.randint(margin, w - margin), rng.randint(margin, h - margin)
    arr = np.asarray(img)
    local = int(arr[my - size:my + size, mx - size:mx + size].mean())
    tone = min(255, local + contrast)
    d = ImageDraw.Draw(img)
    s = size
    d.ellipse([mx - s * .45, my - s * 1.0, mx + s * .45, my - s * .1], fill=tone)        # head
    d.ellipse([mx - s * .75, my - s * .85, mx - s * .35, my - s * .45], fill=tone)       # left ear
    d.ellipse([mx + s * .35, my - s * .85, mx + s * .75, my - s * .45], fill=tone)       # right ear
    d.ellipse([mx - s * .5, my - s * .2, mx + s * .5, my + s * .9], fill=tone)           # body
    d.arc([mx + s * .2, my + s * .2, mx + s * 1.2, my + s * 1.2], 270, 120, fill=tone, width=max(2, s // 6))  # tail
    return img.filter(ImageFilter.GaussianBlur(0.8)), mx, my, size * 1.3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="scored images per task")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--real-scans", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    images = []

    for k in range(args.n + 1):  # last one is practice
        img, x, y, r = search_scene(rng)
        practice = k == args.n
        iid = "search_practice" if practice else f"search_{k:02d}"
        img.save(OUT / f"{iid}.png")
        images.append({"id": iid, "task": "search", "file": f"{iid}.png", "width": W, "height": H,
                       "target": {"x": x, "y": y, "r": r}, "practice": practice})

    sources = sorted(REAL.glob("*.png")) + sorted(REAL.glob("*.jpg")) if args.real_scans else []
    if args.real_scans and len(sources) < args.n + 1:
        raise SystemExit(f"Need {args.n + 1} images in {REAL}, found {len(sources)}.")
    for k in range(args.n + 1):
        base = Image.open(sources[k]) if args.real_scans else synthetic_scan(rng)
        img, x, y, r = plant_monkey(base, rng)
        practice = k == args.n
        iid = "scan_practice" if practice else f"scan_{k:02d}"
        img.save(OUT / f"{iid}.png")
        images.append({"id": iid, "task": "scan", "file": f"{iid}.png", "width": img.width,
                       "height": img.height, "target": {"x": x, "y": y, "r": r}, "practice": practice})

    manifest = {"seed": args.seed, "real_scans": args.real_scans, "images": images}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(images)} images and manifest.json to {OUT}")


if __name__ == "__main__":
    main()
