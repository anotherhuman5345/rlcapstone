"""Reading-inference passages, one file per language in app/reading/<code>.json.

Item k carries the same meaning and the same option order in every language, and
the correct option is recorded once in the stimulus manifest. A person only gets
reading trials when BOTH of their languages have passages; otherwise the task is
left out of their rounds. Passages need a bilingual reviewer's check before use.
"""
import hashlib
import json
from pathlib import Path

READING_DIR = Path(__file__).resolve().parent / "reading"

_ITEMS = {}
_HASH = {}
for _path in sorted(READING_DIR.glob("*.json")):
    _raw = _path.read_bytes()
    _doc = json.loads(_raw)
    _ITEMS[_doc["code"]] = {i["id"]: i for i in _doc["items"]}
    _HASH[_doc["code"]] = hashlib.sha256(_raw).hexdigest()[:10]


def has_reading(code: str) -> bool:
    return code in _ITEMS


def reading_item(code: str, item_id: str) -> dict:
    return _ITEMS[code][item_id]


def reading_hash(code: str) -> str:
    return _HASH.get(code, "")
