"""Generate Google Play store graphics for all five apps, in the shared icon style.

Per app, into dist/play-graphics/<app>/:
  icon-512.png        512x512   — Play "high-res icon"
  feature-graphic.png 1024x500  — Play feature graphic (gradient + glyph + name + tagline)

Run: .venv\\Scripts\\python.exe scripts/make_play_graphics.py
"""

from __future__ import annotations

import math
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SS = 3  # supersample

# app dir -> (accent, glyph, title)
APPS = {
    "app":            ("#00796B", "magnifier", "MoleCheck"),
    "app_ecg":        ("#C62828", "ecg",       "ECG Check"),
    "app_adhd_eeg":   ("#7C3AED", "eeg",       "EEG Explorer"),
    "app_leukemia":   ("#AD1457", "cell",      "Cell Explorer"),
    "app_stock_risk": ("#1565C0", "chart",     "Risk Explorer"),
}
TAGLINE = "Educational AI demo"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, f):
    return tuple(max(0, min(255, round(c * f))) for c in rgb)


def gradient(w, h, accent, horizontal=False):
    top, bot = shade(accent, 1.14), shade(accent, 0.78)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for i in range(h if not horizontal else w):
        t = i / ((h if not horizontal else w) - 1)
        col = tuple(round(top[k] + (bot[k] - top[k]) * t) for k in range(3))
        if not horizontal:
            for x in range(w):
                px[x, i] = col
        else:
            for y in range(h):
                px[i, y] = col
    return img


def thick_polyline(d, pts, width, fill):
    if len(pts) >= 2:
        d.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for (x, y) in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def draw_glyph(layer, name, cx, cy, s):
    d = ImageDraw.Draw(layer)
    white = (255, 255, 255, 255)
    lw = round(0.052 * s)

    def P(nx, ny):
        return (cx + nx * s, cy + ny * s)

    if name == "magnifier":
        rc = P(-0.07, -0.07); r = 0.30 * s
        d.ellipse([rc[0] - r, rc[1] - r, rc[0] + r, rc[1] + r], outline=white, width=lw)
        edge = (rc[0] + r * math.cos(math.radians(45)), rc[1] + r * math.sin(math.radians(45)))
        thick_polyline(d, [edge, P(0.34, 0.34)], lw, white)
        dr = 0.085 * s
        d.ellipse([rc[0] - dr, rc[1] - dr, rc[0] + dr, rc[1] + dr], fill=white)
    elif name == "ecg":
        pts = [(-0.44, 0.0), (-0.20, 0.0), (-0.13, -0.07), (-0.06, 0.0), (0.0, 0.0),
               (0.05, -0.40), (0.11, 0.34), (0.17, 0.0), (0.26, 0.0), (0.32, -0.08),
               (0.38, 0.0), (0.44, 0.0)]
        thick_polyline(d, [P(x, y) for x, y in pts], lw, white)
    elif name == "eeg":
        for yy, amp, ph in [(-0.24, 0.10, 0.0), (0.0, 0.13, 0.9), (0.24, 0.10, 1.8)]:
            pts = []
            for i in range(97):
                nx = -0.44 + 0.88 * i / 96
                ny = yy + amp * math.sin(nx / 0.44 * math.pi * 2.2 + ph)
                pts.append(P(nx, ny))
            thick_polyline(d, pts, round(lw * 0.9), white)
    elif name == "cell":
        r = 0.40 * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=white, width=lw)
        nr = 0.16 * s; nc = P(0.02, 0.03)
        d.ellipse([nc[0] - nr, nc[1] - nr, nc[0] + nr, nc[1] + nr], fill=white)
        for gx, gy in [(-0.17, -0.14), (0.18, -0.10), (-0.10, 0.20)]:
            gr = 0.055 * s; gc = P(gx, gy)
            d.ellipse([gc[0] - gr, gc[1] - gr, gc[0] + gr, gc[1] + gr], fill=white)
    elif name == "chart":
        pts = [(-0.42, 0.26), (-0.26, -0.04), (-0.12, 0.14), (0.03, -0.16),
               (0.20, 0.06), (0.40, -0.30)]
        thick_polyline(d, [P(x, y) for x, y in pts], lw, white)
        tip = P(0.40, -0.30)
        thick_polyline(d, [P(0.24, -0.28), tip], round(lw * 0.9), white)
        thick_polyline(d, [P(0.42, -0.13), tip], round(lw * 0.9), white)


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "Arial_Bold.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build(app_dir, accent_hex, glyph, title):
    accent = hex_rgb(accent_hex)
    outdir = os.path.join(ROOT, "dist", "play-graphics", app_dir)
    os.makedirs(outdir, exist_ok=True)

    # --- 512 icon ---
    w = 512 * SS
    icon = gradient(w, w, accent).convert("RGBA")
    layer = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    draw_glyph(layer, glyph, w / 2, w / 2, 0.62 * w)
    icon.alpha_composite(layer)
    icon.convert("RGB").resize((512, 512), Image.LANCZOS).save(os.path.join(outdir, "icon-512.png"))

    # --- 1024x500 feature graphic ---
    fw, fh = 1024 * SS, 500 * SS
    fg = gradient(fw, fh, accent, horizontal=True).convert("RGBA")
    # glyph in a soft badge on the left
    gcx, gcy, gs = fh * 0.5, fh * 0.5, fh * 0.30
    badge = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    br = gs * 1.55
    bd.ellipse([gcx - br, gcy - br, gcx + br, gcy + br], fill=(255, 255, 255, 28))
    fg.alpha_composite(badge)
    glayer = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    draw_glyph(glayer, glyph, gcx, gcy, gs)
    fg.alpha_composite(glayer)
    # title + tagline text on the right
    d = ImageDraw.Draw(fg)
    tx = fh * 1.15
    d.text((tx, fh * 0.34), title, font=font(int(fh * 0.16)), fill=(255, 255, 255, 255), anchor="lm")
    d.text((tx, fh * 0.56), TAGLINE, font=font(int(fh * 0.075)),
           fill=(255, 255, 255, 220), anchor="lm")
    fg.convert("RGB").resize((1024, 500), Image.LANCZOS).save(os.path.join(outdir, "feature-graphic.png"))
    print(f"{app_dir}: icon-512.png + feature-graphic.png ({title})")


def main():
    for app_dir, (accent, glyph, title) in APPS.items():
        build(app_dir, accent, glyph, title)
    print("\nDone -> dist/play-graphics/")


if __name__ == "__main__":
    main()
