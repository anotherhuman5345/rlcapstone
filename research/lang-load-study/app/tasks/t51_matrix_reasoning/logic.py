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


def score(item, response):
    """response: [{"p": problem index, "choice": option index or null, "rt": ms}].
    hit = at least 3 of the 4 matrices answered correctly (omissions wrong).
    metrics: accuracy, accuracy and mean correct RT for one-rule and two-rule matrices,
    omissions. The key is recomputed with valid()."""
    try:
        probs = item["problems"]
        resp = response if isinstance(response, list) else []
        by_p = {}
        for r in resp:
            if isinstance(r, dict) and isinstance(r.get("p"), int) and r["p"] not in by_p:
                by_p[r["p"]] = r
        ok, cells = [], {1: [], 2: []}
        omis = 0
        for k, pr in enumerate(probs):
            r = by_p.get(k, {})
            ch = r.get("choice")
            if ch is None:
                omis += 1
            good = (isinstance(ch, int) and not isinstance(ch, bool) and 0 <= ch < len(pr["options"])
                    and valid(pr["cells"], pr["options"][ch]))
            ok.append(good)
            rt = r.get("rt")
            cells.setdefault(pr["rules"], []).append((good, rt if isinstance(rt, (int, float)) and rt > 0 else None))

        def acc(v):
            return round(sum(g for g, _ in v) / len(v), 3) if v else None

        def mrt(v):
            x = [rt for g, rt in v if g and rt]
            return round(sum(x) / len(x), 1) if x else None
        return {"hit": sum(ok) >= 3, "errors": len(probs) - sum(ok),
                "metrics": {"accuracy": round(sum(ok) / len(probs), 3),
                            "acc_one_rule": acc(cells[1]), "acc_two_rules": acc(cells[2]),
                            "rt_one_rule": mrt(cells[1]), "rt_two_rules": mrt(cells[2]),
                            "omissions": omis}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    out = []
    for k, pr in enumerate(item["problems"]):
        good = next(i for i, o in enumerate(pr["options"]) if valid(pr["cells"], o))
        out.append({"p": k, "choice": good if correct else (good + 1) % 4, "rt": 12000})
    return out
