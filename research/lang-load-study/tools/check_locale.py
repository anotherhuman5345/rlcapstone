"""Check one language file and print sample clues for a native speaker to review.

Usage:
    python tools/check_locale.py ja          # check app/locales/ja.json
    python tools/check_locale.py ja --all    # also print every object x color phrase

Exits non-zero and says what is wrong if the file is incomplete or a clue
cannot be built. Run it after every edit to a language file.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    code = sys.argv[1]
    show_all = "--all" in sys.argv
    path = ROOT / "app" / "locales" / f"{code}.json"
    loc = json.loads(path.read_text(encoding="utf-8"))  # fails loudly on bad JSON
    from app.i18n import LOCALES
    LOCALES[code] = loc  # check this file even if it is not in the official list yet
    from app.clues import (COLOR_NAMES, DECOY_OBJECTS, DIRECTIONS, N_DICE_LEADS, N_SCAN_LEADS,
                           N_SEARCH_LEADS, N_WHERE, N_WORDS, RULE_TYPES, TARGET_OBJECTS, make_clue,
                           noun_phrase)
    en = json.loads((ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8"))
    problems = []
    fields = lambda text: set(re.findall(r"{(\w+)}", text))
    if loc.get("code") != code:
        problems.append(f'"code" should be "{code}"')
    if loc.get("dir") not in ("ltr", "rtl"):
        problems.append('"dir" must be "ltr" or "rtl"')
    missing = set(en["ui"]) - set(loc.get("ui", {}))
    extra = set(loc.get("ui", {})) - set(en["ui"])
    if missing:
        problems.append(f"ui keys missing: {sorted(missing)}")
    if extra:
        problems.append(f"ui keys not in English: {sorted(extra)}")
    for key, text in loc.get("ui", {}).items():
        if key in en["ui"] and fields(text) != fields(en["ui"][key]):
            problems.append(f"ui[{key}] placeholders {sorted(fields(text))} != English {sorted(fields(en['ui'][key]))}")
    cl = loc.get("clue", {})
    for k in TARGET_OBJECTS + DECOY_OBJECTS:
        if k not in cl.get("objects", {}):
            problems.append(f"clue.objects missing {k}")
    for c in COLOR_NAMES:
        if c not in cl.get("colors", {}):
            problems.append(f"clue.colors missing {c}")
    if len(cl.get("regions", {})) != 9:
        problems.append("clue.regions needs 9 entries")
    if set(cl.get("edges", {})) != {"top", "bottom", "left", "right"}:
        problems.append("clue.edges needs top/bottom/left/right")
    if set(cl.get("rule", {})) != set(RULE_TYPES) | {"question", "group_a", "group_b"}:
        problems.append("clue.rule needs the 5 rule sentences plus question, group_a, group_b")
    if set(cl.get("color_pred", {})) != set(COLOR_NAMES):
        problems.append("clue.color_pred needs all 6 colors")
    if set(cl.get("ospan", {})) != {"lead", "check", "true", "false", "recall", "undo"}:
        problems.append("clue.ospan needs lead, check, true, false, recall, undo")
    words = cl.get("words", [])
    if len(words) != N_WORDS or len(set(words)) != N_WORDS or not all(w.strip() for w in words):
        problems.append(f"clue.words needs {N_WORDS} different, non-empty words")
    if set(cl.get("corsi", {})) != {"forward", "backward"}:
        problems.append("clue.corsi needs forward and backward sentences")
    if set(cl.get("directions", {})) != set(DIRECTIONS):
        problems.append("clue.directions needs up/down/left/right")
    for name, n in (("search_leads", N_SEARCH_LEADS), ("scan_leads", N_SCAN_LEADS), ("where", N_WHERE),
                    ("dice_leads", N_DICE_LEADS)):
        if len(cl.get(name, [])) != n:
            problems.append(f"clue.{name} needs exactly {n} sentences")
    if problems:
        print("\n".join(f"PROBLEM: {p}" for p in problems))
        sys.exit(1)
    for kind in TARGET_OBJECTS:
        for color in COLOR_NAMES:
            for k in range(N_SEARCH_LEADS * N_WHERE * 3):
                clue = make_clue("search", code, f"x{k}", {"x": 90 * k % 1200, "y": 37 * k % 800,
                                 "object": kind, "color": color}, 1200, 800)
                if "{" in clue or "  " in clue:
                    print(f"PROBLEM: bad clue: {clue}")
                    sys.exit(1)
    for rt in RULE_TYPES:
        for c in COLOR_NAMES:
            for n in (1, 2, 3):
                clue = make_clue("rule", code, "r", {"rule": {"type": rt, "color": c, "n": n}}, 1200, 800)
                if "{" in clue or "  " in clue:
                    print(f"PROBLEM: bad rule clue: {clue}")
                    sys.exit(1)
    for da in DIRECTIONS:
        for db in DIRECTIONS:
            for k in range(N_DICE_LEADS * 3):
                clue = make_clue("dice", code, f"d{k}", {"dir_a": da, "dir_b": db}, 1200, 800)
                if "{" in clue or "  " in clue:
                    print(f"PROBLEM: bad dice clue: {clue}")
                    sys.exit(1)
    print(f"{code} ({loc['name']}, {loc['dir']}, verified={loc.get('verified')}): OK\n")
    print("Sample clues:")
    for k in range(4):
        print(" ", make_clue("search", code, f"search_{k:02d}", {"x": 150 + 300 * k, "y": 120 + 180 * k,
                             "object": TARGET_OBJECTS[k * 3], "color": COLOR_NAMES[k]}, 1200, 800))
    for k in range(2):
        print(" ", make_clue("scan", code, f"scan_{k:02d}", {"x": 900, "y": 650, "object": "cat",
                             "color": None}, 1200, 800))
    print(" ", make_clue("surprise", code, "surprise", {"x": 600, "y": 400}, 1200, 800))
    for rt in RULE_TYPES:
        print(" ", make_clue("rule", code, "r", {"rule": {"type": rt, "color": "green", "n": 2}}, 1200, 800))
    print("  words:", ", ".join(loc["clue"]["words"][:8]), "...")
    for d in ("forward", "backward"):
        print(" ", make_clue("corsi", code, "corsi_00", {"direction": d}, 1200, 800))
    for k, (da, db) in enumerate((("up", "right"), ("left", "down"), ("down", "left"))):
        print(" ", make_clue("dice", code, f"dice_{k:02d}", {"dir_a": da, "dir_b": db}, 1200, 800))
    if show_all:
        print("\nEvery object x color phrase:")
        for kind in TARGET_OBJECTS:
            print(" ", " | ".join(noun_phrase(code, kind, c) for c in COLOR_NAMES))


if __name__ == "__main__":
    main()
