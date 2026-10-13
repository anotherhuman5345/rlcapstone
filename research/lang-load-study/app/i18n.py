"""Interface text and clue vocabulary for every language, loaded from app/locales/*.json.

Each file holds:
  - "ui": every interface string (same keys in every language),
  - "clue": the words and sentence patterns used to build clues, including the
    grammar each language needs (word order, and gender/class agreement of
    "small" and the color with the noun),
  - "verified": whether a native speaker has checked the file. Until it is true,
    the language can be used in demo mode but not for real data collection.

Only the CLUE on each trial switches language; that switch is the experimental
manipulation. The interface stays in the language the participant picked.
"""
import json
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent / "locales"

# The 30 most widely spoken languages that have a standard written form, in
# roughly descending order of total speakers.
ORDER = ("en", "zh", "hi", "es", "fr", "ar", "bn", "pt", "ru", "ur", "id", "de", "ja", "mr", "te",
         "tr", "ha", "ta", "sw", "vi", "tl", "ko", "fa", "it", "pa", "gu", "th", "am", "kn", "pl")

LOCALES = {}
for _code in ORDER:
    _path = LOCALE_DIR / f"{_code}.json"
    if _path.exists():
        LOCALES[_code] = json.loads(_path.read_text(encoding="utf-8"))

LANGUAGES = tuple(c for c in ORDER if c in LOCALES)


def language_name(code: str) -> str:
    """The language's name in its own script, e.g. 'Türkçe', '日本語'."""
    return LOCALES[code]["name"]


def direction(code: str) -> str:
    return LOCALES.get(code, LOCALES["en"])["dir"]


def verified(code: str) -> bool:
    return bool(LOCALES[code].get("verified"))


def t(lang: str):
    """Return a lookup function for one language, falling back to English."""
    table = LOCALES.get(lang, LOCALES["en"])["ui"]
    english = LOCALES["en"]["ui"]
    return lambda key, **kw: table.get(key, english.get(key, key)).format(**kw)
