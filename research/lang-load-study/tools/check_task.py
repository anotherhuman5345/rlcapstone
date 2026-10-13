"""Check one library task (app/tasks/<folder>) without touching the shared stimulus files.

Usage:  python tools/check_task.py flanker        (task id)
Checks: task.json fields; generate() is deterministic and returns n items (pairs
(k, k+1) should be matched in difficulty); example_response(correct=True) scores as a
hit and (correct=False) as a miss; score() survives junk responses (None, {}, []);
every text/<lang>.json has the same keys as text/en.json, including "instr" and "clue";
view.html renders with each language; view.js passes `node --check` and registers
TaskViews["<id>"]. Prints a one-line summary per check; exits 1 on any failure.
"""
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    task_id = sys.argv[1]
    from app.tasks import LOAD_ERRORS, PLUGINS
    if task_id not in PLUGINS:
        for folder, err in LOAD_ERRORS.items():
            if folder.endswith(task_id) or task_id in folder:
                sys.exit(f"FAIL: {folder} does not load: {err}")
        sys.exit(f"FAIL: no task with id {task_id!r} (folders: app/tasks/*/task.json)")
    pl = PLUGINS[task_id]
    fails = []

    def check(ok, msg):
        print(("ok   " if ok else "FAIL ") + msg)
        if not ok:
            fails.append(msg)

    for key in ("id", "card", "title", "mode"):
        check(key in pl.meta, f"task.json has {key}")
    check(pl.meta.get("mode") in ("instructions_only", "instructions_and_content"), "mode is valid")

    with tempfile.TemporaryDirectory() as tmp:
        def save_image(name, img):
            fname = f"{task_id}_{name}.png"
            img.save(Path(tmp) / fname)
            return fname
        a = pl.logic.generate(random.Random(7), 12, save_image)
        b = pl.logic.generate(random.Random(7), 12, save_image)
        check(len(a) == 12, "generate(n=12) returns 12 items")
        check(json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str),
              "generate() is deterministic for a given seed")
        check(all(isinstance(i, dict) for i in a), "items are dicts")
        json.dumps(a)  # must be JSON-serialisable
        for k, item in enumerate(a):
            item = {kk: v for kk, v in item.items() if kk != "file"}
            good = pl.logic.score(item, pl.logic.example_response(item, True))
            bad = pl.logic.score(item, pl.logic.example_response(item, False))
            if k < 3:
                check(good["hit"] is True, f"item {k}: correct example response is a hit")
                check(bad["hit"] is False, f"item {k}: wrong example response is a miss")
            for junk in (None, {}, [], "x", 3):
                res = pl.logic.score(item, junk)
                if not (isinstance(res, dict) and res.get("hit") is False):
                    check(False, f"item {k}: score() must return hit=False for junk {junk!r}")
                    break
            json.dumps(good)

        en = pl.text.get("en")
        check(en is not None, "text/en.json exists")
        check(bool(en) and "instr" in en and "clue" in en, "en text has instr and clue")
        # Jinja's `text.clear` returns the dict method, not the string: forbid such names.
        reserved = {"items", "keys", "values", "get", "pop", "popitem", "update", "copy", "clear",
                    "setdefault", "fromkeys"}
        for code, tx in pl.text.items():
            check(set(tx) == set(en or {}), f"text/{code}.json has the same keys as en")
            check("\ufffd" not in json.dumps(tx, ensure_ascii=False),
                  f"text/{code}.json has no broken characters (U+FFFD)")
            bad = reserved & set(tx)
            check(not bad, f"text/{code}.json avoids reserved key names" + (f": {sorted(bad)}" if bad else ""))

        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(str(ROOT / "app" / "tasks")))
        tpl = env.get_template(pl.template)
        item = {kk: v for kk, v in a[0].items() if kk != "file"}
        for code, tx in pl.text.items():
            html = tpl.render(item=item, text=tx, img_url="/img/x.png" if a[0].get("file") else None,
                              trial={"task": task_id, "clue_lang": code})
            check(len(html.strip()) > 0, f"view.html renders ({code})")

    js = pl.js.read_text(encoding="utf-8")
    check(f'TaskViews["{task_id}"]' in js, "view.js registers TaskViews[id]")
    r = subprocess.run(["node", "--check", str(pl.js)], capture_output=True, text=True)
    check(r.returncode == 0, "view.js syntax (node --check)" + ("" if r.returncode == 0 else ": " + r.stderr.strip()[:300]))
    print(f"\n{task_id}: {'OK' if not fails else str(len(fails)) + ' problem(s)'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
