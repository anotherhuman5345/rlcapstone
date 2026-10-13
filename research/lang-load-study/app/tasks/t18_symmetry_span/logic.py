"""Symmetry span (card 18): judge whether an 8x8 black-and-white pattern is mirror
symmetric about its vertical midline, then see one red square flash in a 4x4 grid;
after the whole set, tap the flashed squares in the order they appeared.

One trial is one set (3 or 4 steps). Pairs (k, k+1) share the set size and the number
of symmetric patterns, and every pattern has the same number of black cells (24 of
64), so symmetric and non-symmetric patterns cannot be told apart by density. The
answer key is recomputed here from the pattern itself (mirroring oracle)."""
from app.tasks import _guard as G

TIMING = "window"         # each symmetry judgement has a 4000 ms window (view.js judgeAnswer(4000));
JUDGE_MS = 4000           # the location recall is unspeeded
WINDOW_MS = JUDGE_MS
RT_SLACK_MS = 50          # timer tolerance at the window end
ANSWERS = ("yes", "no")
CEILING_MS = G.trial_ceiling(__file__)

ROWS, COLS, HALF = 8, 8, 4
FILLED_LEFT = 12          # black cells in the left half; the full pattern has 24
MOVED = 3                 # cells moved on the right half to break symmetry
GRID = 16                 # 4x4 recall grid


def is_symmetric(pattern):
    """Oracle: every row reads the same mirrored."""
    return all(row == row[::-1] for row in pattern)


def _symmetric(rng):
    cells = rng.sample(range(ROWS * HALF), FILLED_LEFT)
    rows = [["0"] * COLS for _ in range(ROWS)]
    for c in cells:
        r, col = divmod(c, HALF)
        rows[r][col] = "1"
        rows[r][COLS - 1 - col] = "1"
    return rows


def _pattern(rng, symmetric):
    while True:
        rows = _symmetric(rng)
        if not symmetric:
            right = [(r, c) for r in range(ROWS) for c in range(HALF, COLS)]
            on = [rc for rc in right if rows[rc[0]][rc[1]] == "1"]
            off = [rc for rc in right if rows[rc[0]][rc[1]] == "0"]
            for (r1, c1), (r2, c2) in zip(rng.sample(on, MOVED), rng.sample(off, MOVED)):
                rows[r1][c1], rows[r2][c2] = "0", "1"
        pat = ["".join(r) for r in rows]
        if is_symmetric(pat) == symmetric:
            return pat


def generate(rng, n, save_image):
    items = []
    for k in range(n):
        if k % 2 == 0:  # pair template: set size and how many patterns are symmetric
            size = 3 if (k // 2) % 2 == 0 else 4
            n_sym = rng.choice([size // 2, (size + 1) // 2])
        flags = [True] * n_sym + [False] * (size - n_sym)
        rng.shuffle(flags)
        locs = rng.sample(range(GRID), size)
        items.append({"set_size": size,
                      "steps": [{"pattern": _pattern(rng, f), "loc": loc} for f, loc in zip(flags, locs)]})
    return items


@G.safe
def score(item, response):
    """response: {"symmetry": [{"answer": "yes"|"no"|null, "rt": ms}] in step order,
                  "recall": [cell 0-15, ...] in the order tapped, "recall_rt": ms}.
    Each symmetry judgement is classified (app/tasks/_guard.py): absent (no answer: timed
    out), invalid (unknown answer, answer without rt or rt without answer, bad rt, entry
    missing), anticipatory (< 100 ms), late (beyond the 4000 ms judging window, view.js
    judgeAnswer(4000), + 50 ms timer tolerance) or timely. Only a timely judgement can be
    correct. Recall is unspeeded: cells must be integers 0-15 tapped at most once (the browser
    blocks repeats); invalid or repeated cells are flagged and the recall is then not exact.
    recall_rt is descriptive (flagged when bad).
    hit = the flashed squares are recalled exactly, in order (strict serial recall, from a
    well-formed recall list) AND at most one symmetry judgement is wrong, missing or not
    timely (processing check).
    errors = symmetry errors (incl. omissions) + serial recall positions wrong."""
    steps = item["steps"]
    size = len(steps)
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(2 * size)
    sym_ok, rts, omissions, not_timely = [], [], 0, 0
    for st, r in zip(steps, a.entries(response.get("symmetry", G.MISSING), size, "symmetry")):
        status, ans, rt = a.keyed(r, ANSWERS, key="answer", window=JUDGE_MS, slack=RT_SLACK_MS)
        truth = "yes" if is_symmetric(st["pattern"]) else "no"
        ok = status == G.TIMELY and ans == truth
        sym_ok.append(ok)
        omissions += status == G.ABSENT
        not_timely += status in (G.INVALID, G.ANTICIPATORY, G.LATE)
        if ok:
            rts.append(rt)
    raw = a.stream(response.get("recall", G.MISSING), "recall", cap=GRID)
    rec, seen, rec_ok = [], set(), isinstance(response.get("recall"), list)
    for c in raw:
        if not G.member(c, range(GRID)):
            a.malformed("invalid_recall")
            rec_ok = False
            rec.append(None)
            continue
        if c in seen:
            a.malformed("duplicate_recall")
            rec_ok = False
        seen.add(c)
        rec.append(c)
    recall_rt = a.duration(response, "recall_rt", floor=0)
    locs = [st["loc"] for st in steps]
    serial = sum(1 for k, loc in enumerate(locs) if k < len(rec) and rec[k] == loc)
    any_order = len(seen & set(locs))
    exact = rec_ok and rec == locs
    sym_err = size - sum(sym_ok)
    return a.finish(exact and sym_err <= 1, sym_err + (size - serial), {
        "set_size": size, "recall_exact": exact, "recall_serial_correct": serial,
        "recall_serial_accuracy": round(serial / size, 3),
        "recall_items_any_order": any_order, "recall_count": len(rec),
        "symmetry_accuracy": round(sum(sym_ok) / size, 3),
        "symmetry_omissions": omissions, "symmetry_not_timely": not_timely,
        "symmetry_rt_correct_mean": G.mean(rts), "recall_rt": recall_rt})


def example_response(item, correct=True):
    steps = item["steps"]
    sym = [{"answer": ("yes" if is_symmetric(st["pattern"]) else "no") if correct
            else ("no" if is_symmetric(st["pattern"]) else "yes"), "rt": 1800} for st in steps]
    locs = [st["loc"] for st in steps]
    recall = locs if correct else [(c + 1) % GRID for c in locs]
    return {"symmetry": sym, "recall": recall, "recall_rt": 6000}
