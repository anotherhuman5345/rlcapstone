"""Symmetry span (card 18): judge whether an 8x8 black-and-white pattern is mirror
symmetric about its vertical midline, then see one red square flash in a 4x4 grid;
after the whole set, tap the flashed squares in the order they appeared.

One trial is one set (3 or 4 steps). Pairs (k, k+1) share the set size and the number
of symmetric patterns, and every pattern has the same number of black cells (24 of
64), so symmetric and non-symmetric patterns cannot be told apart by density. The
answer key is recomputed here from the pattern itself (mirroring oracle)."""

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


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def score(item, response):
    """response: {"symmetry": [{"answer": "yes"|"no"|null, "rt": ms}] in step order,
                  "recall": [cell 0-15, ...] in the order tapped, "recall_rt": ms}.
    hit = the flashed squares are recalled exactly, in order (strict serial recall)
    AND at most one symmetry judgement is wrong or missing (processing check).
    errors = symmetry errors (incl. omissions) + serial recall positions wrong."""
    steps = item["steps"]
    size = len(steps)
    resp = response if isinstance(response, dict) else {}
    sym = resp.get("symmetry") if isinstance(resp.get("symmetry"), list) else []
    rec = resp.get("recall") if isinstance(resp.get("recall"), list) else []
    rec = [c for c in rec if isinstance(c, int) and not isinstance(c, bool) and 0 <= c < GRID]
    sym_ok, rts = [], []
    for k, st in enumerate(steps):
        r = sym[k] if k < len(sym) and isinstance(sym[k], dict) else {}
        truth = "yes" if is_symmetric(st["pattern"]) else "no"
        ok = r.get("answer") == truth
        sym_ok.append(ok)
        if ok and _num(r.get("rt")):
            rts.append(r["rt"])
    locs = [st["loc"] for st in steps]
    serial = sum(1 for k, loc in enumerate(locs) if k < len(rec) and rec[k] == loc)
    any_order = len(set(rec) & set(locs))
    exact = rec == locs
    sym_err = size - sum(sym_ok)
    return {"hit": bool(exact and sym_err <= 1),
            "errors": sym_err + (size - serial),
            "metrics": {"set_size": size, "recall_exact": exact, "recall_serial_correct": serial,
                        "recall_serial_accuracy": round(serial / size, 3),
                        "recall_items_any_order": any_order, "recall_count": len(rec),
                        "symmetry_accuracy": round(sum(sym_ok) / size, 3),
                        "symmetry_omissions": sum(1 for k in range(size) if not (k < len(sym) and isinstance(sym[k], dict) and sym[k].get("answer") in ("yes", "no"))),
                        "symmetry_rt_correct_mean": round(sum(rts) / len(rts), 1) if rts else None,
                        "recall_rt": _num(resp.get("recall_rt"))}}


def example_response(item, correct=True):
    steps = item["steps"]
    sym = [{"answer": ("yes" if is_symmetric(st["pattern"]) else "no") if correct
            else ("no" if is_symmetric(st["pattern"]) else "yes"), "rt": 1800} for st in steps]
    locs = [st["loc"] for st in steps]
    recall = locs if correct else [(c + 1) % GRID for c in locs]
    return {"symmetry": sym, "recall": recall, "recall_rt": 6000}
