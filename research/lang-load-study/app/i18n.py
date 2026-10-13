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
import hashlib
import json
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent / "locales"

# The 30 most widely spoken languages that have a standard written form, in
# roughly descending order of total speakers.
ORDER = ("en", "zh", "hi", "es", "fr", "ar", "bn", "pt", "ru", "ur", "id", "de", "ja", "mr", "te",
         "tr", "ha", "ta", "sw", "vi", "tl", "ko", "fa", "it", "pa", "gu", "th", "am", "kn", "pl")

LOCALES = {}
# Short hash of each file as loaded, stored on data rows as its translation version.
LOCALE_HASH = {}
for _code in ORDER:
    _path = LOCALE_DIR / f"{_code}.json"
    if _path.exists():
        _raw = _path.read_bytes()
        LOCALES[_code] = json.loads(_raw)
        LOCALE_HASH[_code] = hashlib.sha256(_raw).hexdigest()[:10]

# Interface strings added after the 30 files were translated. Until a translator adds
# them, unverified languages show the English text (see t() below). A language cannot
# be marked verified, or used for real data, while any of these is missing from it.
PENDING_UI_KEYS: set[str] = set()

LANGUAGES = tuple(c for c in ORDER if c in LOCALES)


def language_name(code: str) -> str:
    """The language's name in its own script, e.g. 'Türkçe', '日本語'."""
    return LOCALES[code]["name"]


def direction(code: str) -> str:
    return LOCALES.get(code, LOCALES["en"])["dir"]


def verified(code: str) -> bool:
    # A checked file that lacks newer interface strings would show English mid-study.
    complete = set(LOCALES["en"]["ui"]) <= set(LOCALES[code]["ui"])
    return bool(LOCALES[code].get("verified")) and complete


def t(lang: str):
    """Return a lookup function for one language, falling back to English."""
    table = LOCALES.get(lang, LOCALES["en"])["ui"]
    english = LOCALES["en"]["ui"]
    return lambda key, **kw: table.get(key, english.get(key, key)).format(**kw)
