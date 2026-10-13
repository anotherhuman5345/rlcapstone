"""Task library: every extra task is a self-contained folder in app/tasks/.

Each folder (a Python package, e.g. app/tasks/t22_flanker/) holds:
  task.json   {"id", "card", "title", "mode", "timeout_ms"}
  logic.py    generate(rng, n, save_image) -> list of item dicts (language-neutral)
              score(item, response) -> {"hit": bool, "errors": int, "metrics": {...}}
              example_response(item, correct) -> a response score() understands (tests)
  view.html   Jinja partial: the task's screen (gets item, text, img_url, trial)
  view.js     registers TaskViews["<id>"] = function (ctx) {...}; calls ctx.finish(response, timedOut)
  text/<lang>.json  every string the task shows, in that language ("instr", "clue", ...)
See app/tasks/README.md for the full contract. Folders load automatically; a task joins
the study only when it is listed in config.ROUND_MIX.
"""
import importlib
import json
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent


class Plugin:
    def __init__(self, folder: Path):
        self.folder = folder
        self.meta = json.loads((folder / "task.json").read_text(encoding="utf-8"))
        self.id = self.meta["id"]
        self.logic = importlib.import_module(f"app.tasks.{folder.name}.logic")
        self.text = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                     for p in sorted((folder / "text").glob("*.json"))}
        self.template = f"{folder.name}/view.html"
        self.js = folder / "view.js"

    @property
    def timeout_ms(self) -> int:
        return int(self.meta.get("timeout_ms", 60000))

    def has_language(self, code: str) -> bool:
        return code in self.text


PLUGINS = {}
# A folder that fails to load is skipped (so one broken task cannot take the site
# down) and recorded here; the test suite fails while this is not empty.
LOAD_ERRORS = {}
for _folder in sorted(TASK_DIR.iterdir()):
    if (_folder / "task.json").exists():
        try:
            _plugin = Plugin(_folder)
        except Exception as exc:  # noqa: BLE001 - report any problem with the folder
            LOAD_ERRORS[_folder.name] = f"{type(exc).__name__}: {exc}"
            continue
        PLUGINS[_plugin.id] = _plugin


def ascii_digits(value):
    """Turn digits typed in another script (Arabic-Indic ٣, Bengali ৩, Devanagari ३, ...)
    into 0-9 everywhere inside a response, so typed numbers score the same in every language."""
    if isinstance(value, str):
        return "".join(str(int(ch)) if ch.isdecimal() and not ch.isascii() else ch for ch in value)
    if isinstance(value, list):
        return [ascii_digits(v) for v in value]
    if isinstance(value, dict):
        return {k: ascii_digits(v) for k, v in value.items()}
    return value
