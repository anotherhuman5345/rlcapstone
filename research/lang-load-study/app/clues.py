"""Build the written clue for a trial, in English or Turkish.

The clue must be READ to be useful: it names the region of the image and
which edge the target is nearer to. A one-word clue could be skipped, and
then language would not matter. Both languages carry exactly the same
information so the only difference between conditions is the language.
"""

REGIONS = {
    # (row, col) on a 3x3 grid
    "en": {
        (0, 0): "upper-left", (0, 1): "top-center", (0, 2): "upper-right",
        (1, 0): "middle-left", (1, 1): "center", (1, 2): "middle-right",
        (2, 0): "lower-left", (2, 1): "bottom-center", (2, 2): "lower-right",
    },
    "tr": {
        (0, 0): "sol üst", (0, 1): "üst orta", (0, 2): "sağ üst",
        (1, 0): "sol orta", (1, 1): "orta", (1, 2): "sağ orta",
        (2, 0): "sol alt", (2, 1): "alt orta", (2, 2): "sağ alt",
    },
}

EDGES = {
    "en": {"top": "top", "bottom": "bottom", "left": "left", "right": "right"},
    # Turkish dative forms: "üst kenara", "alt kenara", ...
    "tr": {"top": "üst", "bottom": "alt", "left": "sol", "right": "sağ"},
}

TARGET_NAME = {
    "search": {"en": "Find the small red umbrella.", "tr": "Küçük kırmızı şemsiyeyi bulun."},
    "scan": {"en": "Did you see the monkey?", "tr": "Maymunu gördünüz mü?"},
    # The surprise trial names only the ring. The gorilla is never mentioned.
    "surprise": {"en": "Find the small white ring.", "tr": "Küçük beyaz halkayı bulun."},
}


def nearest_two_edges(x, y, w, h):
    vertical = ("top", y) if y < h - y else ("bottom", h - y)
    horizontal = ("left", x) if x < w - x else ("right", w - x)
    # (nearer edge, farther edge)
    return (vertical[0], horizontal[0]) if vertical[1] <= horizontal[1] else (horizontal[0], vertical[0])


def region_of(x, y, w, h):
    row = min(int(3 * y / h), 2)
    col = min(int(3 * x / w), 2)
    return row, col


def make_clue(task: str, lang: str, x: float, y: float, w: int, h: int) -> str:
    region = REGIONS[lang][region_of(x, y, w, h)]
    near, far = nearest_two_edges(x, y, w, h)
    lead = TARGET_NAME[task][lang]
    if lang == "en":
        where = (f"It is in the {region} area of the image, closer to the "
                 f"{EDGES['en'][near]} edge than to the {EDGES['en'][far]} edge.")
    else:
        where = (f"Görüntünün {region} bölgesinde; {EDGES['tr'][far]} kenardan çok "
                 f"{EDGES['tr'][near]} kenara yakın.")
    return f"{lead} {where}"
