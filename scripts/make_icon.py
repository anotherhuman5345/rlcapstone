"""Generate the MoleCheck app icon: a magnifying glass examining a mole, on the
app's teal background. Writes a 1024x1024 PNG used by flutter_launcher_icons.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "assets" / "icon"
SIZE = 1024
SS = 4  # supersample for smooth edges

TEAL = (0, 121, 107)
TEAL_DARK = (0, 90, 79)
WHITE = (255, 255, 255)
SKIN = (233, 190, 158)
MOLE = (74, 44, 30)


def main() -> None:
    s = SIZE * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded-square teal background with a subtle vertical gradient.
    radius = int(s * 0.22)
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bgd = ImageDraw.Draw(bg)
    for y in range(s):
        t = y / s
        r = int(TEAL[0] * (1 - t) + TEAL_DARK[0] * t)
        g = int(TEAL[1] * (1 - t) + TEAL_DARK[1] * t)
        b = int(TEAL[2] * (1 - t) + TEAL_DARK[2] * t)
        bgd.line([(0, y), (s, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s, s], radius=radius, fill=255)
    img.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # Magnifying glass: lens centred slightly up-left, handle to lower-right.
    cx, cy = int(s * 0.44), int(s * 0.42)
    lens_r = int(s * 0.24)
    ring = int(s * 0.055)

    # Handle (rounded thick line at 45 degrees), drawn under the ring.
    ang = math.radians(45)
    h_start = (cx + math.cos(ang) * (lens_r + ring * 0.2),
               cy + math.sin(ang) * (lens_r + ring * 0.2))
    h_end = (cx + math.cos(ang) * (lens_r + int(s * 0.20)),
             cy + math.sin(ang) * (lens_r + int(s * 0.20)))
    d.line([h_start, h_end], fill=WHITE, width=int(ring * 1.5))
    d.ellipse([h_end[0] - ring * 0.75, h_end[1] - ring * 0.75,
               h_end[0] + ring * 0.75, h_end[1] + ring * 0.75], fill=WHITE)

    # Lens interior: skin patch with an irregular mole.
    d.ellipse([cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r], fill=SKIN)
    # Irregular mole: overlapping blobs off-centre.
    for dx, dy, rr in [(-0.02, 0.0, 0.13), (0.06, 0.05, 0.09),
                       (-0.08, 0.06, 0.07), (0.02, -0.07, 0.06)]:
        mx, my = cx + int(s * dx), cy + int(s * dy)
        mr = int(s * rr)
        d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=MOLE)

    # White ring around the lens.
    d.ellipse([cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r],
              outline=WHITE, width=ring)

    out = img.resize((SIZE, SIZE), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    icon_path = OUT / "icon.png"
    out.convert("RGBA").save(icon_path)

    # A version with padding for adaptive icons (Android foreground layer).
    fg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    inner = out.resize((int(SIZE * 0.62), int(SIZE * 0.62)), Image.LANCZOS)
    off = (SIZE - inner.width) // 2
    fg.paste(inner, (off, off), inner)
    fg.save(OUT / "icon_foreground.png")

    print(f"Wrote {icon_path} and icon_foreground.png")


if __name__ == "__main__":
    main()
