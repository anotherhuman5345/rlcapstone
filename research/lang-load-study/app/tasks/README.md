# Task library: how to add a task

Every library task is one folder here, named `tNN_<name>` where NN is its card number in
the study specification (e.g. `t22_flanker`). The folder is a Python package and contains:

| File | What it does |
|---|---|
| `__init__.py` | empty |
| `task.json` | `{"id": "flanker", "card": "22", "title": "Flanker", "mode": "instructions_only", "timeout_ms": 90000}` |
| `logic.py` | `generate`, `score`, `example_response` (below) |
| `view.html` | Jinja partial for the task's screen |
| `view.js` | registers `TaskViews["<id>"] = function (ctx) { ... }` |
| `text/en.json`, `text/tr.json`, ... | every word the participant sees, per language |

`t22_flanker` is the reference implementation; copy its shape.

## logic.py

```python
def generate(rng, n, save_image) -> list[dict]:
    """n items, language-neutral, JSON-serialisable. Use only `rng` (a random.Random)
    so the output is deterministic. Items come in pairs (0,1), (2,3), ...: the two items
    of a pair are shown in the person's two languages, so make them equally hard (same
    structure/difficulty, different surface details). The last item is used as practice.
    If the task needs a picture, draw it with PIL (1200x800) and call
    save_image(name, img) -> filename; put that filename in the item as "file"."""

def score(item, response) -> {"hit": bool, "errors": int, "metrics": dict}:
    """Score on the server. Must never crash: junk (None, {}, [], "x", 3) -> hit False.
    "hit" is the task's main pass/fail for the trial (document the rule in the docstring);
    "errors" a count of mistakes; "metrics" the task's real scores (accuracy, RTs, d',
    span, excess moves, ...). Answer keys must be computed by an independent oracle
    (solver, simulator, parser), not trusted from the browser."""

def example_response(item, correct=True):
    """A response the browser could send: correct=True must score as a clean hit (no flags),
    correct=False as a miss. Used by tests."""

TIMING = "window"    # or "limit" / "untimed" (below)
WINDOW_MS = 2000     # with "window": the per-event response window (LIMIT_MS with "limit")
```

### Validating responses (`_guard.py`)

The browser's response is untrusted input. Score it at the event level with the shared
helpers in `app/tasks/_guard.py` (`from app.tasks import _guard as G`; decorate `score` with
`@G.safe`, build one `G.Audit(G.trial_ceiling(__file__))` per call and return
`audit.finish(hit, errors, metrics)`). Every event gets one status: absent, invalid
(wrong type, non-finite / negative / impossible time, unknown key, key without time, entry
missing), anticipatory (< 100 ms), late (beyond the documented window) or timely.

- `TIMING = "window"`: events have a response window (often set in view.js, e.g.
  `await answer(2000)`; copy it into `WINDOW_MS`). Only a timely response counts as made;
  a withhold (no-go, stop, standard) succeeds only when the event is absent, never when its
  entry is malformed.
- `TIMING = "limit"`: the decisive action (solving move, final click, submitted answer) must
  carry a valid time inside `LIMIT_MS`.
- `TIMING = "untimed"`: times are descriptive; bad ones are flagged and reported as null.

Malformed data never crashes a scorer and never passes silently: `metrics["flags"]` lists
everything abnormal (e.g. `invalid_rt`, `late_rt`, `extra_events`, `missing_audio`) and
`metrics["invalid_events"]` counts malformed events; a clean response has no flags.
Metrics must be strict JSON (no NaN/Infinity).

## view.js

```js
TaskViews["<id>"] = function (ctx) {
  // ctx.item: the item from generate(); ctx.text: this language's text/<lang>.json
  // ctx.root: the element holding view.html; ctx.imgUrl: picture URL or null
  // ctx.status(msg): show a short status line
  // ctx.practice: true on the practice item and the try page; show correctness
  //   feedback only when it is true (unless feedback is part of the task itself)
  // ctx.finish(response, timedOut): call exactly once when the trial is over
};
```

Rules: plain browser JavaScript (no libraries, no build step, no network calls). Work with
mouse, touch and keyboard (give on-screen buttons for every key). Use `performance.now()`
for timing and put reaction times inside the response. Ignore key auto-repeat
(`e.repeat`). Start timed sequences only after a "Start" button so instructions can be
read first. Keep one trial between about 10 and 90 seconds: it is repeated twice per
round. Set `timeout_ms` in task.json comfortably above the longest normal trial; the
limit is counted from the person's first click or key press in the task.

## Text and language

Everything the participant reads comes from `text/<lang>.json`; nothing in view.html or
view.js may be English hard-coded. Do not name a key `items`, `keys`, `values`, `get`, `pop`, `update`, `copy` or
`clear` (in templates these resolve to dictionary methods). Required keys: `"instr"` (one line for the
instructions page) and `"clue"` (the instruction shown above the task in the trial's
language). Add any other keys you need (button labels, words, sentences, options).
If the task has verbal content (words, sentences, options), store it in the text file and
refer to it from items by index, so items stay language-neutral and every language shows
equivalent content; set `"mode": "instructions_and_content"`. Otherwise
`"mode": "instructions_only"`. Use original content only: no copied test items, no
copyrighted puzzles or pictures. Turkish (`tr`) is required alongside English; more
languages are added later with the same keys.

## Check

```bash
python tools/check_task.py <id>
```

It checks determinism, scoring of correct/wrong/junk responses, matching text keys,
template rendering per language, and JavaScript syntax. Then run

```bash
python tools/adversarial_check.py <id>
```

which mutates the correct example response (times set to 999999, -5, 0, NaN, Infinity,
strings, null; events reordered, duplicated, nulled or blown up to 10 000; wrong types at
every level; fields deleted or added) and checks that impossible or late times never score
as a timely correct response and malformed payloads never score as a clean hit (rules in
the script's docstring; `tests/test_adversarial.py` runs it for every task).

A task joins the study only when listed in `ROUND_MIX`; every task can be tried alone at `/try/<id>`.
