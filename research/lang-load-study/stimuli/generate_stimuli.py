"""Generate all study images and the manifest that records where each target is.

Every picture has its OWN target, named in its clue. Pilot testers said a fixed
target (always a red umbrella, always a monkey) became automatic after a few
pictures, so they stopped reading the clue -- and an unread clue cannot show a
language effect.

Search scenes: original cluttered scenes (no copyrighted puzzle art). Each has a
unique (object, color) target, e.g. a small green fish. Distractors share its
shape (fish in other colors) or its color (other green objects), which makes it a
"conjunction search": the target cannot pop out on color or shape alone.

Scans: a small, faint silhouette (cat, bird, key, house, ...) is planted in a
grayscale image. Object, size and contrast vary from picture to picture.

Surprise image (seen once, FIRST, before anything mentions animals): a scan
with a small white ring as the stated target and an unannounced gorilla
silhouette elsewhere in the image. This is the inattentional-blindness test
after Drew, Vo & Wolfe (2013). The gorilla appears in no other image.

By default this script makes SYNTHETIC placeholder "scans" so the platform can
be built and tested. For the real study, put de-identified images supplied by
the lab (after IRB approval) in stimuli/real_scans/ and run with --real-scans;
the targets are planted into those instead.

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


# Every picture gets its own target so people must read the clue each time.
# (Pilot testers reported that a fixed target -- always a red umbrella, always a
# monkey -- became automatic after a few pictures and they stopped reading.)
COLORS = {"red": (214, 40, 40), "blue": (40, 90, 200), "green": (40, 150, 70),
          "yellow": (235, 190, 30), "purple": (140, 70, 170), "orange": (240, 130, 40)}
EXTRA_COLORS = [(90, 90, 90), (30, 160, 170), (150, 100, 60)]  # distractor-only colors
SEARCH_OBJECTS = ["umbrella", "star", "heart", "moon", "arrow", "cross", "diamond",
                  "house", "fish", "key"]
# Scan targets: faint silhouettes. The gorilla is NOT here: it only ever appears
# in the surprise image.
SCAN_OBJECTS = ["monkey", "cat", "bird", "fish", "star", "key", "house", "heart",
                "moon", "arrow", "cross", "umbrella"]
FILLER_SHAPES = ["circle", "triangle", "square"]
OUTLINE = (30, 30, 30)


def _poly(d, pts, fill, outline):
    d.polygon(pts, fill=fill, outline=outline)


def draw_object(d, kind, cx, cy, s, fill, outline=OUTLINE):
    """Draw one object centred at (cx, cy), about 2*s across."""
    w = max(2, int(s // 6))
    line = outline or fill
    if kind == "circle":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=fill, outline=outline)
    elif kind == "triangle":
        _poly(d, [(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)], fill, outline)
    elif kind == "square":
        d.rectangle([cx - s, cy - s, cx + s, cy + s], fill=fill, outline=outline)
    elif kind == "umbrella":
        d.pieslice([cx - s, cy - s, cx + s, cy + s], 180, 360, fill=fill, outline=outline)
        d.line([cx, cy, cx, cy + s * 1.1], fill=line, width=w)
        d.arc([cx, cy + s * .8, cx + s * .5, cy + s * 1.3], 0, 180, fill=line, width=w)
    elif kind == "star":
        pts = [(cx + (s if k % 2 == 0 else s * .45) * math.sin(k * math.pi / 5),
                cy - (s if k % 2 == 0 else s * .45) * math.cos(k * math.pi / 5)) for k in range(10)]
        _poly(d, pts, fill, outline)
    elif kind == "heart":
        r = s * .52
        d.ellipse([cx - s, cy - s * .7, cx - s + 2 * r, cy - s * .7 + 2 * r], fill=fill)
        d.ellipse([cx + s - 2 * r, cy - s * .7, cx + s, cy - s * .7 + 2 * r], fill=fill)
        _poly(d, [(cx - s * .98, cy - s * .1), (cx + s * .98, cy - s * .1), (cx, cy + s)], fill, None)
    elif kind == "moon":
        outer = [(cx + s * math.cos(a), cy + s * math.sin(a))
                 for a in [math.pi / 2 + k * math.pi / 16 for k in range(17)]]
        inner = [(cx - s * .35 + s * .75 * math.cos(a), cy + s * .95 * math.sin(a))
                 for a in [3 * math.pi / 2 - k * math.pi / 16 for k in range(17)]]
        _poly(d, outer + inner, fill, outline)
    elif kind == "arrow":
        _poly(d, [(cx - s, cy - s * .3), (cx + s * .2, cy - s * .3), (cx + s * .2, cy - s * .8),
                  (cx + s, cy), (cx + s * .2, cy + s * .8), (cx + s * .2, cy + s * .3),
                  (cx - s, cy + s * .3)], fill, outline)
    elif kind == "cross":
        t = s * .35
        _poly(d, [(cx - t, cy - s), (cx + t, cy - s), (cx + t, cy - t), (cx + s, cy - t),
                  (cx + s, cy + t), (cx + t, cy + t), (cx + t, cy + s), (cx - t, cy + s),
                  (cx - t, cy + t), (cx - s, cy + t), (cx - s, cy - t), (cx - t, cy - t)], fill, outline)
    elif kind == "diamond":
        _poly(d, [(cx, cy - s), (cx + s * .7, cy), (cx, cy + s), (cx - s * .7, cy)], fill, outline)
    elif kind == "house":
        _poly(d, [(cx - s * .75, cy - s * .1), (cx, cy - s), (cx + s * .75, cy - s * .1),
                  (cx + s * .75, cy + s), (cx - s * .75, cy + s)], fill, outline)
    elif kind == "fish":
        d.ellipse([cx - s * .8, cy - s * .45, cx + s * .5, cy + s * .45], fill=fill, outline=outline)
        _poly(d, [(cx + s * .35, cy), (cx + s, cy - s * .5), (cx + s, cy + s * .5)], fill, outline)
    elif kind == "key":
        d.ellipse([cx - s, cy - s * .4, cx - s * .2, cy + s * .4], outline=fill, width=max(2, int(s // 3.5)))
        d.rectangle([cx - s * .25, cy - s * .12, cx + s, cy + s * .12], fill=fill)
        d.rectangle([cx + s * .55, cy, cx + s * .7, cy + s * .45], fill=fill)
        d.rectangle([cx + s * .8, cy, cx + s * .95, cy + s * .35], fill=fill)
    elif kind == "monkey":
        d.ellipse([cx - s * .45, cy - s, cx + s * .45, cy - s * .1], fill=fill)
        d.ellipse([cx - s * .75, cy - s * .85, cx - s * .35, cy - s * .45], fill=fill)
        d.ellipse([cx + s * .35, cy - s * .85, cx + s * .75, cy - s * .45], fill=fill)
        d.ellipse([cx - s * .5, cy - s * .2, cx + s * .5, cy + s * .9], fill=fill)
        d.arc([cx + s * .2, cy + s * .2, cx + s * 1.2, cy + s * 1.2], 270, 120, fill=fill, width=w)
    elif kind == "cat":
        d.ellipse([cx - s * .5, cy - s * .8, cx + s * .5, cy + s * .1], fill=fill)
        _poly(d, [(cx - s * .5, cy - s * .45), (cx - s * .4, cy - s * 1.05), (cx - s * .1, cy - s * .7)], fill, None)
        _poly(d, [(cx + s * .5, cy - s * .45), (cx + s * .4, cy - s * 1.05), (cx + s * .1, cy - s * .7)], fill, None)
        d.ellipse([cx - s * .55, cy - s * .1, cx + s * .55, cy + s], fill=fill)
    elif kind == "bird":
        d.ellipse([cx - s * .8, cy - s * .4, cx + s * .4, cy + s * .45], fill=fill)
        d.ellipse([cx + s * .1, cy - s * .7, cx + s * .7, cy - s * .1], fill=fill)
        _poly(d, [(cx + s * .65, cy - s * .5), (cx + s, cy - s * .38), (cx + s * .65, cy - s * .28)], fill, None)
        _poly(d, [(cx - s * .7, cy - s * .1), (cx - s, cy - s * .55), (cx - s * .9, cy + s * .1)], fill, None)
    else:
        raise ValueError(kind)


def search_scene(rng, target_kind, target_color, n_distractors=260, target_size=13):
    """Conjunction search: distractors share the target's shape OR its color, never both."""
    img = Image.new("RGB", (W, H), (236, 232, 222))
    d = ImageDraw.Draw(img)
    rgb = COLORS[target_color]
    others = [c for name, c in COLORS.items() if name != target_color] + EXTRA_COLORS
    shapes = [k for k in SEARCH_OBJECTS if k != target_kind] + FILLER_SHAPES
    margin = 40
    tx, ty = rng.randint(margin, W - margin), rng.randint(margin, H - margin)
    for _ in range(n_distractors):
        x, y = rng.randint(10, W - 10), rng.randint(10, H - 10)
        if math.hypot(x - tx, y - ty) < target_size * 3:
            continue  # keep the target unobstructed
        s = rng.randint(9, 18)
        roll = rng.random()
        if roll < 0.30:      # same shape, wrong color
            draw_object(d, target_kind, x, y, s, rng.choice(others))
        elif roll < 0.55:    # right color, wrong shape
            draw_object(d, rng.choice(shapes), x, y, s, rgb)
        else:                # everything else
            draw_object(d, rng.choice(shapes), x, y, s, rng.choice(others))
    draw_object(d, target_kind, tx, ty, target_size, rgb)
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


def plant_object(img, rng, kind, size=None, contrast=None):
    """Draw a small, faint silhouette, only slightly brighter than its surroundings.
    Size and contrast vary from picture to picture so no target pops out the same way."""
    img = img.convert("L")
    size = size or rng.randint(15, 22)
    # Brightness above the local background, in gray levels (0-255). The first
    # version used a fixed +38, which testers found too obvious; this is half of
    # that on average (16-22, mean 19), varied per picture.
    contrast = contrast or rng.randint(16, 22)
    w, h = img.size
    margin = size * 3
    mx, my = rng.randint(margin, w - margin), rng.randint(margin, h - margin)
    arr = np.asarray(img)
    local = int(arr[my - size:my + size, mx - size:mx + size].mean())
    tone = min(255, local + contrast)
    draw_object(ImageDraw.Draw(img), kind, mx, my, size, tone, outline=None)
    return img.filter(ImageFilter.GaussianBlur(0.8)), mx, my, size * 1.3


def plant_ring(img, rng, avoid=None, r=9):
    """The stated target of the surprise trial: a small bright ring."""
    img = img.convert("L")
    w, h = img.size
    while True:
        x, y = rng.randint(80, w - 80), rng.randint(80, h - 80)
        if avoid is None or math.hypot(x - avoid[0], y - avoid[1]) > min(w, h) * 0.35:
            break
    d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], outline=235, width=3)
    return img, x, y, r * 1.5


def plant_gorilla(img, rng, size=40, contrast=30):
    """An original gorilla silhouette (not copied from any study), toned to blend with the scan
    the way the original gorilla matched lung tissue. Never mentioned to the participant."""
    img = img.convert("L")
    w, h = img.size
    gx, gy = rng.randint(int(w * .2), int(w * .8)), rng.randint(int(h * .3), int(h * .7))
    arr = np.asarray(img)
    local = int(arr[gy - size:gy + size, gx - size:gx + size].mean())
    tone = min(255, local + contrast)
    d = ImageDraw.Draw(img)
    s = size
    t = max(4, int(s * .38))  # limb thickness
    d.ellipse([gx - s * .75, gy - s * .8, gx + s * .75, gy + s * .45], fill=tone)        # broad torso
    d.ellipse([gx - s * .3, gy - s * 1.25, gx + s * .3, gy - s * .6], fill=tone)         # head
    d.ellipse([gx - s * .5, gy - s * .95, gx + s * .5, gy - s * .45], fill=tone)         # shoulders/neck
    for side in (-1, 1):
        d.line([gx + side * s * .6, gy - s * .5, gx + side * s * .95, gy + s * .85], fill=tone, width=t)  # arm
        d.ellipse([gx + side * s * .95 - t * .7, gy + s * .85 - t * .6,
                   gx + side * s * .95 + t * .7, gy + s * .85 + t * .6], fill=tone)    # knuckles
        d.line([gx + side * s * .3, gy + s * .3, gx + side * s * .42, gy + s * .95], fill=tone, width=t)  # leg
    return img.filter(ImageFilter.GaussianBlur(0.8)), gx, gy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=48, help="scored images per task (12 rounds x 4)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--real-scans", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    images = []

    # Unique (object, color) pair for every search scene.
    combos = [(k, c) for k in SEARCH_OBJECTS for c in COLORS]
    rng.shuffle(combos)
    if args.n + 1 > len(combos):
        raise SystemExit(f"Only {len(combos)} distinct search targets; lower --n.")
    for k in range(args.n + 1):  # last one is practice
        kind, color = combos[k]
        img, x, y, r = search_scene(rng, kind, color)
        practice = k == args.n
        iid = "search_practice" if practice else f"search_{k:02d}"
        img.save(OUT / f"{iid}.png")
        images.append({"id": iid, "task": "search", "file": f"{iid}.png", "width": W, "height": H,
                       "target": {"x": x, "y": y, "r": r, "object": kind, "color": color},
                       "practice": practice})

    sources = sorted(REAL.glob("*.png")) + sorted(REAL.glob("*.jpg")) if args.real_scans else []
    if args.real_scans and len(sources) < args.n + 2:
        raise SystemExit(f"Need {args.n + 2} images in {REAL} (scored + practice + surprise), "
                         f"found {len(sources)}.")
    # Scan targets cycle through the object list in a shuffled order, so the same
    # object comes back only after every other one has been used.
    scan_kinds = []
    while len(scan_kinds) < args.n + 1:
        batch = SCAN_OBJECTS[:]
        rng.shuffle(batch)
        scan_kinds += batch
    for k in range(args.n + 1):
        base = Image.open(sources[k]) if args.real_scans else synthetic_scan(rng)
        img, x, y, r = plant_object(base, rng, scan_kinds[k])
        practice = k == args.n
        iid = "scan_practice" if practice else f"scan_{k:02d}"
        img.save(OUT / f"{iid}.png")
        images.append({"id": iid, "task": "scan", "file": f"{iid}.png", "width": img.width,
                       "height": img.height,
                       "target": {"x": x, "y": y, "r": r, "object": scan_kinds[k], "color": None},
                       "practice": practice})

    # Surprise image: ring target + unannounced gorilla, on its own scan.
    base = Image.open(sources[args.n + 1]) if args.real_scans else synthetic_scan(rng)
    img, gx, gy = plant_gorilla(base, rng)
    img, x, y, r = plant_ring(img, rng, avoid=(gx, gy))
    img.save(OUT / "surprise.png")
    images.append({"id": "surprise", "task": "surprise", "file": "surprise.png", "width": img.width,
                   "height": img.height, "target": {"x": x, "y": y, "r": r, "object": "ring", "color": None},
                   "gorilla": {"x": gx, "y": gy}, "practice": False})

    manifest = {"seed": args.seed, "real_scans": args.real_scans, "images": images}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(images)} images and manifest.json to {OUT}")


if __name__ == "__main__":
    main()
