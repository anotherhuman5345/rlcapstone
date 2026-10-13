"""Build the written clue for a trial, in English or Turkish.

The clue must be READ to be useful, every single time:
  - Search scenes name a different target in every picture ("a small green
    fish", "a small purple key"), so nobody can search on autopilot.
  - Scans never name what to look for. The clue says something in the image is
    out of the ordinary, the way a reader of a real scan looks for an
    abnormality without being told what it is.
  - The wording itself rotates through several equivalent sentence patterns.
  - The location part names the region and the nearer edge.
Both languages of a given picture use the same pattern and carry exactly the
same information, so the only difference between conditions is the language.
Have a native speaker proofread all Turkish text before real data collection.
"""
import zlib

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
    "tr": {"top": "üst", "bottom": "alt", "left": "sol", "right": "sağ"},
}

COLORS = {
    "en": {"red": "red", "blue": "blue", "green": "green", "yellow": "yellow",
           "purple": "purple", "orange": "orange"},
    "tr": {"red": "kırmızı", "blue": "mavi", "green": "yeşil", "yellow": "sarı",
           "purple": "mor", "orange": "turuncu"},
}

# English noun; Turkish (nominative, accusative).
OBJECTS = {
    "umbrella": ("umbrella", "şemsiye", "şemsiyeyi"),
    "star": ("star", "yıldız", "yıldızı"),
    "heart": ("heart", "kalp", "kalbi"),
    "moon": ("crescent moon", "hilal", "hilali"),
    "arrow": ("arrow", "ok", "oku"),
    "cross": ("plus sign", "artı işareti", "artı işaretini"),
    "diamond": ("diamond", "karo", "karoyu"),
    "house": ("house", "ev", "evi"),
    "fish": ("fish", "balık", "balığı"),
    "key": ("key", "anahtar", "anahtarı"),
    "monkey": ("monkey", "maymun", "maymunu"),
    "cat": ("cat", "kedi", "kediyi"),
    "bird": ("bird", "kuş", "kuşu"),
    # Used only as wrong answers in the attention check; never a target.
    "car": ("car", "araba", "arabayı"),
    "tree": ("tree", "ağaç", "ağacı"),
    "guitar": ("guitar", "gitar", "gitarı"),
    "elephant": ("elephant", "fil", "fili"),
}
DECOY_OBJECTS = ("car", "tree", "guitar", "elephant")

SEARCH_LEADS = {
    "en": ["Find the small {color} {obj}.",
           "Look for a small {color} {obj}.",
           "Your target: a small {color} {obj}.",
           "Somewhere there is a small {color} {obj}. Click it."],
    "tr": ["Küçük {color} {acc} bulun.",
           "Küçük bir {color} {nom} arayın.",
           "Hedefiniz: küçük bir {color} {nom}.",
           "Bir yerde küçük bir {color} {nom} var. Üzerine tıklayın."],
}

SCAN_LEADS = {
    "en": ["Something in this image is out of the ordinary. Find it.",
           "One thing here does not belong. Click on it.",
           "Look for anything that does not match the rest of the image.",
           "There is something unusual in this image."],
    "tr": ["Bu görüntüde olağan dışı bir şey var. Onu bulun.",
           "Burada bir şey yerine ait değil. Üzerine tıklayın.",
           "Görüntünün geri kalanıyla uyuşmayan bir şey arayın.",
           "Bu görüntüde alışılmadık bir şey var."],
}

SURPRISE_LEAD = {"en": "Find the small white ring.", "tr": "Küçük beyaz halkayı bulun."}

WHERE = {
    "en": ["It is in the {region} area of the image, closer to the {near} edge than to the {far} edge.",
           "Check the {region} part, nearer the {near} edge than the {far} edge.",
           "Search the {region} area; it sits closer to the {near} edge than to the {far} edge."],
    "tr": ["Görüntünün {region} bölgesinde; {far} kenardan çok {near} kenara yakın.",
           "{Region} kısma bakın; {far} kenardan çok {near} kenara yakın.",
           "{Region} bölgeyi arayın; {near} kenara, {far} kenardan daha yakın."],
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


def variant(image_id: str, n: int, salt: str = "") -> int:
    """Stable choice of sentence pattern per image (same in both languages)."""
    return zlib.crc32((salt + image_id).encode()) % n


def object_name(kind: str, lang: str) -> str:
    en, nom, _ = OBJECTS[kind]
    return en if lang == "en" else nom


def make_clue(task: str, lang: str, image_id: str, target: dict, w: int, h: int) -> str:
    x, y = target["x"], target["y"]
    if task == "surprise":
        lead = SURPRISE_LEAD[lang]
    elif task == "scan":
        leads = SCAN_LEADS[lang]
        lead = leads[variant(image_id, len(leads), "lead")]
    else:
        en, nom, acc = OBJECTS[target["object"]]
        leads = SEARCH_LEADS[lang]
        lead = leads[variant(image_id, len(leads), "lead")].format(
            color=COLORS[lang][target["color"]], obj=en, nom=nom, acc=acc)
    region = REGIONS[lang][region_of(x, y, w, h)]
    near, far = nearest_two_edges(x, y, w, h)
    templates = WHERE[lang]
    where = templates[variant(image_id, len(templates), "where")].format(
        region=region, Region=region[0].upper() + region[1:],
        near=EDGES[lang][near], far=EDGES[lang][far])
    return f"{lead} {where}"
