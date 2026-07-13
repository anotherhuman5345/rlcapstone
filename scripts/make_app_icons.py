"""Generate a consistent app-icon set for all five Flutter apps.

Design system: one shared style — a subtle vertical gradient in the project's
site accent colour, with a bold white pictograph centred inside. Each app gets a
distinct glyph (magnifier, ECG trace, EEG waves, cell, volatility line) so the
apps read as one family while staying distinguishable on a home screen.

Outputs, per app dir:
  assets/icon/icon.png            1024x1024 opaque  (iOS + Android legacy)
  assets/icon/icon_foreground.png 1024x1024 alpha   (Android adaptive foreground)

Run: .venv\\Scripts\\python.exe scripts/make_app_icons.py
Then, per app: flutter pub get && dart run flutter_launcher_icons
"""

from __future__ import annotations

import math
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SS = 3          # supersample factor for smooth edges
OUT = 1024      # final icon size
W = OUT * SS

# app dir -> (accent hex, glyph name)
APPS = {
    "app":            ("#00796B", "magnifier"),  # MoleCheck  (teal)
    "app_ecg":        ("#C62828", "ecg"),        # ECG Check  (red)
    "app_adhd_eeg":   ("#7C3AED", "eeg"),        # EEG Explorer (purple)
    "app_leukemia":   ("#AD1457", "cell"),       # Cell Explorer (pink)
    "app_stock_risk": ("#1565C0", "chart"),      # Risk Explorer (blue)
}


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, f):
    return tuple(max(0, min(255, round(c * f))) for c in rgb)


def gradient_bg(accent) -> Image.Image:
    """Vertical gradient: slightly lighter at top, darker at bottom."""
    top = shade(accent, 1.12)
    bot = shade(accent, 0.82)
    img = Image.new("RGB", (W, W))
    px = img.load()
    for y in range(W):
        t = y / (W - 1)
        row = tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row
    return img


def thick_polyline(d, pts, width, fill):
    """Polyline with round caps and joints."""
    if len(pts) >= 2:
        d.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for (x, y) in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def draw_glyph(name, box):
    """Return an RGBA layer (W x W) with a white glyph scaled to `box` px."""
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = W / 2
    s = box
    white = (255, 255, 255, 255)
    lw = round(0.052 * s)  # main stroke width

    def P(nx, ny):
        return (c + nx * s, c + ny * s)

    if name == "magnifier":
        # lens ring, offset up-left; handle to lower-right; centre dot (the mole)
        rc = P(-0.07, -0.07)
        r = 0.30 * s
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
        d.ellipse([c - r, c - r, c + r, c + r], outline=white, width=lw)   # membrane
        nr = 0.16 * s                                                       # nucleus
        nc = P(0.02, 0.03)
        d.ellipse([nc[0] - nr, nc[1] - nr, nc[0] + nr, nc[1] + nr], fill=white)
        for gx, gy in [(-0.17, -0.14), (0.18, -0.10), (-0.10, 0.20)]:       # granules
            gr = 0.055 * s
            gc = P(gx, gy)
            d.ellipse([gc[0] - gr, gc[1] - gr, gc[0] + gr, gc[1] + gr], fill=white)

    elif name == "chart":
        pts = [(-0.42, 0.26), (-0.26, -0.04), (-0.12, 0.14), (0.03, -0.16),
               (0.20, 0.06), (0.40, -0.30)]
        thick_polyline(d, [P(x, y) for x, y in pts], lw, white)
        tip = P(0.40, -0.30)                                                # arrowhead
        thick_polyline(d, [P(0.24, -0.28), tip], round(lw * 0.9), white)
        thick_polyline(d, [P(0.42, -0.13), tip], round(lw * 0.9), white)

    return layer


def build(app_dir, accent_hex, glyph):
    accent = hex_rgb(accent_hex)

    # full opaque icon: gradient bg + glyph (generous padding)
    full = gradient_bg(accent).convert("RGBA")
    full.alpha_composite(draw_glyph(glyph, 0.62 * W))
    full = full.convert("RGB").resize((OUT, OUT), Image.LANCZOS)

    # adaptive foreground: transparent + smaller glyph (adaptive safe zone)
    fg = draw_glyph(glyph, 0.52 * W).resize((OUT, OUT), Image.LANCZOS)

    outdir = os.path.join(ROOT, app_dir, "assets", "icon")
    os.makedirs(outdir, exist_ok=True)
    full.save(os.path.join(outdir, "icon.png"))
    fg.save(os.path.join(outdir, "icon_foreground.png"))
    print(f"{app_dir}: icon.png + icon_foreground.png  ({accent_hex}, {glyph})")


def main():
    for app_dir, (accent, glyph) in APPS.items():
        build(app_dir, accent, glyph)
    print("\nDone. Now run per app: dart run flutter_launcher_icons")


if __name__ == "__main__":
    main()
