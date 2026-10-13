"""Matrix reasoning (card 51), adapted to one short trial.

One trial = 4 original 3x3 matrices (bottom-right cell missing), 2 with one rule and 2
with two rules, each with 4 answer options. Cells are drawn by view.js (SVG) from four
attributes: shape (4 kinds), count (1-3), shade (white/grey/black) and size (3 steps).
A "rule" is an attribute that varies over the matrix in one of three ways:
  progression - the same increasing sequence in every row (count or size),
  distribution - each row and each column holds three different values (Latin square),
  row - constant within a row, different between rows.
All other attributes are constant over the whole matrix.
Distractors are the correct cell with one attribute changed (values taken from the
matrix where possible). The generator never marks the key: `valid()` is an independent
evaluator that accepts a completed grid when every attribute fits at least one of the
three patterns (or is constant), and generate() keeps only problems where exactly one
option is valid. score() uses the same evaluator. The two items of a pair use the same
rule specification (which attributes, which patterns) with different values.
"""
from app.tasks import _guard as G

ATTRS = ["shape", "count", "shade", "size"]
RANGE = {"shape": 4, "count": 3, "shade": 3, "size": 3}
SPECS1 = [[("count", "progression")], [("size", "progression")], [("shape", "distribution")],
          [("shade", "distribution")], [("count", "distribution")], [("shape", "row")]]
SPECS2 = [[("count", "progression"), ("shape", "distribution")],
          [("size", "progression"), ("shade", "distribution")],
          [("shape", "distribution"), ("shade", "distribution")],
          [("count", "distribution"), ("shape", "row")],
          [("shade", "row"), ("size", "progression")],
          [("count", "progression"), ("shade", "distribution")]]
TIME_LIMIT_MS = 40000
TIMING = "limit"      # each matrix must be answered within its limit (see _guard.py)
LIMIT_MS = TIME_LIMIT_MS  # view.js ask(): setTimeout(() => done(null), it.limit_ms), per matrix
TIME_SLACK_MS = 1000  # timer tolerance at the limit
MAX_ENTRIES = 100     # entries read from the response list (4 expected)
CEILING_MS = G.trial_ceiling(__file__)


def _pattern(rng, attr, kind):
    """3x3 grid of values for one attribute."""
    vals = rng.sample(range(RANGE[attr]), 3)
    if kind == "progression":
        seq = sorted(vals)
        if attr in ("count", "size"):
            seq = [0, 1, 2] if attr == "size" else [1, 2, 3]
        if rng.random() < 0.5:
            seq = seq[::-1]
        return [list(seq) for _ in range(3)]
    if kind == "row":
        return [[v] * 3 for v in vals]
    shift = rng.choice([1, 2])
    return [[vals[(c + shift * r) % 3] for c in range(3)] for r in range(3)]


def _fits(grid):
    rows_const = all(len(set(r)) == 1 for r in grid)
    rows_same = all(r == grid[0] for r in grid)
    latin = (all(len(set(r)) == 3 for r in grid) and all(set(r) == set(grid[0]) for r in grid)
             and all(len({grid[r][c] for r in range(3)}) == 3 for c in range(3)))
    return rows_const or rows_same or latin


def valid(cells, option):
    """Independent evaluator: is `option` a lawful completion of the 8 given cells?"""
    full = list(cells) + [option]
    for a in ATTRS:
        grid = [[full[r * 3 + c].get(a) for c in range(3)] for r in range(3)]
        if not _fits(grid):
            return False
    return True


def _problem(rng, spec):
    while True:
        const = {"shape": rng.randrange(4), "count": rng.randrange(1, 4),
                 "shade": rng.randrange(3), "size": rng.randrange(3)}
        grids = {a: _pattern(rng, a, kind) for a, kind in spec}
        cells = []
        for r in range(3):
            for c in range(3):
                cells.append({a: (grids[a][r][c] if a in grids else const[a]) for a in ATTRS})
        answer = cells.pop()
        options = [answer]
        varying = [a for a, _ in spec]
        tries = 0
        while len(options) < 4 and tries < 200:
            tries += 1
            a = rng.choice(varying) if rng.random() < 0.75 else rng.choice(ATTRS)
            pool = sorted({cell[a] for cell in cells} - {answer[a]})
            if not pool or rng.random() < 0.25:
                lo = 1 if a == "count" else 0
                pool = [v for v in range(lo, lo + RANGE[a]) if v != answer[a]]
            d = dict(answer)
            d[a] = rng.choice(pool)
            if d not in options:
                options.append(d)
        if len(options) < 4:
            continue
        rng.shuffle(options)
        if sum(valid(cells, o) for o in options) == 1:
            return {"cells": cells, "options": options, "rules": len(spec)}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        specs = [rng.choice(SPECS1), rng.choice(SPECS1), rng.choice(SPECS2), rng.choice(SPECS2)]
        for _ in range(2):
            items.append({"problems": [_problem(rng, s) for s in specs], "limit_ms": TIME_LIMIT_MS})
    return items[:n]


def _by_index(seq, n, a, key="p"):
    """Entries keyed by problem index: {index: entry}. The first entry for an index wins;
    later duplicates (duplicate_p), unknown / non-integer indices (invalid_p), entries that
    are not objects and entries out of presentation order are flagged; an index with no
    entry is flagged missing_p (and is an invalid event, scored as an omission)."""
    by, last = {}, -1
    for r in seq:
        if not isinstance(r, dict):
            a.malformed("event_not_object")
            continue
        k = r.get(key, G.MISSING)
        if not G.is_int(k) or not 0 <= k < n:
            a.malformed(f"invalid_{key}" if k is not G.MISSING else f"missing_{key}")
            continue
        if k in by:
            a.malformed(f"duplicate_{key}")
            continue
        if k < last:
            a.flag(f"out_of_order_{key}")
        last = k
        by[k] = r
    missing = n - len(by)
    if missing:
        a.flag(f"missing_{key}", missing)
    return by


@G.safe
def score(item, response):
    """response: [{"p": problem index, "choice": option index or null, "rt": ms}] in matrix
    order, one entry per matrix (the first entry for an index counts; duplicate, unknown
    and missing indices are flagged). choice null with rt null = the 40 s limit ran out.
    A choice counts only when its rt is a valid time inside the per-matrix limit
    (finite, >= 100 ms, <= LIMIT_MS + 1 s timer slack, see view.js); a choice with a
    missing / non-finite / negative / impossible / anticipatory / late rt, or an option
    index that does not exist, is never correct (flagged).
    hit = at least 3 of the 4 matrices answered correctly in time (omissions wrong).
    metrics: accuracy, accuracy and mean correct RT for one-rule and two-rule matrices,
    omissions, per-matrix events. The key is recomputed with valid()."""
    a = G.Audit(CEILING_MS)
    probs = item["problems"]
    if not isinstance(response, list):
        return a.junk(len(probs))
    by_p = _by_index(a.stream(response, "events", cap=MAX_ENTRIES), len(probs), a)
    ok, cells, events = [], {1: [], 2: []}, []
    omis = 0
    for k, pr in enumerate(probs):
        r = by_p.get(k)
        if r is None:
            status, ch, rt = a.record(G.INVALID), None, None
        else:
            status, ch, rt = a.keyed(r, range(len(pr["options"])), key="choice", rt="rt",
                                     window=LIMIT_MS, slack=TIME_SLACK_MS)
        if status in (G.ABSENT, G.INVALID) and ch is None:
            omis += 1
        good = status == G.TIMELY and valid(pr["cells"], pr["options"][ch])
        ok.append(good)
        cells.setdefault(pr["rules"], []).append((good, rt if good else None))
        events.append({"i": k, "rules": pr["rules"], "status": status, "choice": ch if status == G.TIMELY else None,
                       "correct": good, "rt": rt if status == G.TIMELY else None})

    def acc(v):
        return round(sum(g for g, _ in v) / len(v), 3) if v else None

    def mrt(v):
        x = [rt for g, rt in v if g and rt is not None]
        return round(sum(x) / len(x), 1) if x else None
    return a.finish(sum(ok) >= 3, len(probs) - sum(ok), {
        "accuracy": round(sum(ok) / len(probs), 3),
        "acc_one_rule": acc(cells[1]), "acc_two_rules": acc(cells[2]),
        "rt_one_rule": mrt(cells[1]), "rt_two_rules": mrt(cells[2]),
        "omissions": omis, "events": events})


def example_response(item, correct=True):
    out = []
    for k, pr in enumerate(item["problems"]):
        good = next(i for i, o in enumerate(pr["options"]) if valid(pr["cells"], o))
        out.append({"p": k, "choice": good if correct else (good + 1) % 4, "rt": 12000})
    return out
