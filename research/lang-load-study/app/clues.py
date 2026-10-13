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
Each language's words and sentence patterns live in app/locales/<code>.json.
"""
import zlib

from .i18n import LOCALES

# Kinds of object, for checking that every language file covers them all.
TARGET_OBJECTS = ("umbrella", "star", "heart", "moon", "arrow", "cross", "diamond", "house",
                  "fish", "key", "monkey", "cat", "bird")
# Used only as wrong answers in the attention check; never a target.
DECOY_OBJECTS = ("car", "tree", "guitar", "elephant")
COLOR_NAMES = ("red", "blue", "green", "yellow", "purple", "orange")
N_SEARCH_LEADS, N_SCAN_LEADS, N_WHERE, N_DICE_LEADS = 4, 4, 3, 3
DIRECTIONS = ("up", "down", "left", "right")


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


def upper_first(text: str, lang: str) -> str:
    if not text:
        return text
    first = text[0]
    if lang == "tr" and first == "i":
        first = "İ"  # Turkish dotted capital I
    return first.upper() + text[1:]


def _agree(table: dict, gender: str) -> str:
    """Pick the form that agrees with the noun's gender or class ('*' = any)."""
    return table.get(gender, table.get("*", ""))


def noun_phrase(lang: str, kind: str, color: str | None, form: str = "nom") -> str:
    """'small green fish' in the language's own word order and agreement."""
    spec = LOCALES[lang]["clue"]
    obj = spec["objects"][kind]
    gender = obj.get("g", "*")
    noun = obj.get(form, obj["nom"])
    color_word = _agree(spec["colors"][color], gender) if color else ""
    phrase = spec["np"].format(small=_agree(spec["small"], gender), color=color_word, noun=noun)
    return " ".join(phrase.split()) if " " in spec["np"] else phrase


def object_name(kind: str, lang: str) -> str:
    return LOCALES[lang]["clue"]["objects"][kind]["nom"]


def make_clue(task: str, lang: str, image_id: str, target: dict, w: int, h: int) -> str:
    spec = LOCALES[lang]["clue"]
    if task == "corsi":
        # Only the clue says whether to click in the same or the reverse order.
        return upper_first(spec["corsi"][target["direction"]], lang)
    if task == "reading":
        return ""  # passage and question are shown in full; see app/reading.py
    if task == "dice":
        # The moves ARE the instruction, so there is no separate "where" sentence.
        # Directions are in words; the numbers are only on the dice in the picture.
        template = spec["dice_leads"][variant(image_id, N_DICE_LEADS, "dice")]
        dirs = spec["directions"]
        return upper_first(template.format(dir_a=dirs[target["dir_a"]], dir_b=dirs[target["dir_b"]]), lang)
    x, y = target["x"], target["y"]
    if task == "surprise":
        lead = spec["surprise_lead"]
    elif task == "scan":
        lead = spec["scan_leads"][variant(image_id, N_SCAN_LEADS, "lead")]
    else:
        template = spec["search_leads"][variant(image_id, N_SEARCH_LEADS, "lead")]
        lead = template.format(np=noun_phrase(lang, target["object"], target["color"]),
                               np_acc=noun_phrase(lang, target["object"], target["color"], "acc"))
        lead = upper_first(lead, lang)
    row, col = region_of(x, y, w, h)
    region = spec["regions"][f"{row},{col}"]
    near, far = nearest_two_edges(x, y, w, h)
    where = spec["where"][variant(image_id, N_WHERE, "where")].format(
        region=region, Region=upper_first(region, lang),
        near=spec["edges"][near], far=spec["edges"][far])
    # Chinese and Japanese do not put a space after a full stop.
    sep = "" if lead.endswith(("。", "！", "？")) else " "
    return f"{lead}{sep}{where}"
