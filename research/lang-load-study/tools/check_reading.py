"""Check reading-passage files against English.

Usage:
    python tools/check_reading.py            # every app/reading/*.json
    python tools/check_reading.py de ja      # only these languages

Each file must have the same item ids in the same order as en.json, the same number of
options per item, the same correct option ("answer"), its own language code, and no
empty or broken text. Exits non-zero and lists the problems.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READING = ROOT / "app" / "reading"


def check(code, en):
    path = READING / f"{code}.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{code}: cannot read: {exc}"]
    problems = []
    if doc.get("code") != code:
        problems.append(f"{code}: code is {doc.get('code')!r}")
    if code != "en" and doc.get("verified") is not False:
        problems.append(f"{code}: verified must be false until a native speaker checks it")
    items = doc.get("items") or []
    if [i.get("id") for i in items] != [i["id"] for i in en["items"]]:
        problems.append(f"{code}: item ids differ from en.json (same ids, same order)")
        return problems
    for mine, ref in zip(items, en["items"]):
        tag = f"{code} {ref['id']}"
        if mine.get("answer") != ref["answer"]:
            problems.append(f"{tag}: answer {mine.get('answer')} != {ref['answer']}")
        opts = mine.get("options")
        if not isinstance(opts, list) or len(opts) != len(ref["options"]):
            problems.append(f"{tag}: needs {len(ref['options'])} options")
            continue
        texts = [mine.get("passage"), mine.get("question"), *opts]
        if not all(isinstance(t, str) and t.strip() for t in texts):
            problems.append(f"{tag}: empty text")
        if any("�" in (t or "") for t in texts):
            problems.append(f"{tag}: broken character (U+FFFD)")
        if len(set(opts)) != len(opts):
            problems.append(f"{tag}: two options are identical")
    return problems


def main():
    en = json.loads((READING / "en.json").read_text(encoding="utf-8"))
    codes = sys.argv[1:] or sorted(p.stem for p in READING.glob("*.json"))
    problems = [p for code in codes for p in check(code, en)]
    for p in problems:
        print(p)
    print(f"{len(codes)} language(s) checked, {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
