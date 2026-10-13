"""Paper folding (card 32): a square sheet is folded in half 1, 2 or 3 times (each fold
shown as a picture), then one hole is punched through all layers. Which of four unfolded
sheets shows the holes correctly? One trial = one puzzle.

The sheet is an 8x8 grid of cells. Folds always halve the current folded part along its
middle line, so fold lines lie on grid lines and the hole (a cell centre) is never on a
fold line. Fold codes: "L" = left half folded over onto the right half, "R" = right over
left, "T" = top over bottom, "B" = bottom over top.

The answer key is not stored. score() re-runs the reflection simulator (unfold in reverse
order, reflecting every hole across each fold line) and compares the chosen sheet with it.
Difficulty: pairs (k, k+1) share the fold count and the axis pattern (e.g. vertical then
horizontal); the fold count cycles 1, 2, 3 across pairs. Distractors have the same number
of holes as the key: one unfolded about a wrong line, one punched in a neighbouring spot,
one mirror image of the key (whichever exist and differ)."""

N = 8
AXIS = {"L": "x", "R": "x", "T": "y", "B": "y"}


def _regions(folds):
    """Folded part before each fold and after the last: (x0, y0, x1, y1) in grid lines."""
    r = (0, 0, N, N)
    out = [r]
    for f in folds:
        x0, y0, x1, y1 = r
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        r = {"L": (mx, y0, x1, y1), "R": (x0, y0, mx, y1), "T": (x0, my, x1, y1), "B": (x0, y0, x1, my)}[f]
        out.append(r)
    return out


def _lines(folds):
    regs = _regions(folds)
    out = []
    for f, (x0, y0, x1, y1) in zip(folds, regs):
        out.append(("x", (x0 + x1) // 2) if AXIS[f] == "x" else ("y", (y0 + y1) // 2))
    return out


def _reflect(p, axis, m):
    x, y = p
    return (2 * m - x - 1, y) if axis == "x" else (x, 2 * m - y - 1)


def _unfold(lines, hole):
    pts = {tuple(hole)}
    for axis, m in reversed(lines):
        pts |= {_reflect(p, axis, m) for p in pts}
    return frozenset(pts)


def unfold(folds, hole):
    """Oracle: hole cells on the opened sheet."""
    return _unfold(_lines(folds), hole)


def _ok(pattern, size):
    return len(pattern) == size and all(0 <= x < N and 0 <= y < N for x, y in pattern)


def _puzzle(rng, axes):
    folds = [rng.choice("LR" if a == "x" else "TB") for a in axes]
    x0, y0, x1, y1 = _regions(folds)[-1]
    hole = (rng.randrange(x0, x1), rng.randrange(y0, y1))
    key = unfold(folds, hole)
    size = 2 ** len(folds)
    lines = _lines(folds)
    regs = _regions(folds)
    wrong_line, wrong_spot, mirror = [], [], []
    for i, (axis, m) in enumerate(lines):  # unfold one step about the other middle line
        rx0, ry0, rx1, ry1 = regs[i]
        alt = ("y", (ry0 + ry1) // 2) if axis == "x" else ("x", (rx0 + rx1) // 2)
        wrong_line.append(_unfold(lines[:i] + [alt] + lines[i + 1:], hole))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        h = (hole[0] + dx, hole[1] + dy)
        if x0 <= h[0] < x1 and y0 <= h[1] < y1:
            wrong_spot.append(_unfold(lines, h))
    for fx, fy in ((True, False), (False, True), (True, True)):
        mirror.append(frozenset(((N - 1 - x) if fx else x, (N - 1 - y) if fy else y) for x, y in key))
    chosen = [key]
    pools = [wrong_line, wrong_spot, mirror]
    for pool in pools:
        rng.shuffle(pool)
    for pool in pools:  # one of each kind first
        for p in pool:
            if _ok(p, size) and p not in chosen:
                chosen.append(p)
                break
    rest = [p for pool in pools for p in pool]
    rng.shuffle(rest)
    for p in rest:
        if len(chosen) == 4:
            break
        if _ok(p, size) and p not in chosen:
            chosen.append(p)
    while len(chosen) < 4:  # random sheet with the same number of holes
        p = frozenset((rng.randrange(N), rng.randrange(N)) for _ in range(size))
        if _ok(p, size) and p not in chosen:
            chosen.append(p)
    rng.shuffle(chosen)
    return {"folds": folds, "hole": list(hole), "options": [sorted([list(c) for c in p]) for p in chosen]}


AXIS_PATTERNS = {1: [["x"], ["y"]], 2: [["x", "y"], ["y", "x"], ["x", "x"], ["y", "y"]],
                 3: [["x", "y", "x"], ["y", "x", "y"], ["x", "y", "y"], ["y", "x", "x"]]}


def generate(rng, n, save_image):
    items = []
    for k in range(n):
        if k % 2 == 0:
            n_folds = (k // 2) % 3 + 1
            axes = rng.choice(AXIS_PATTERNS[n_folds])
        items.append(_puzzle(rng, axes))
    return items


def _choice(response):
    if not isinstance(response, dict):
        return None, None
    c, rt = response.get("choice"), response.get("rt")
    c = c if isinstance(c, int) and not isinstance(c, bool) else None
    rt = rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
    return c, rt


def score(item, response):
    """response: {"choice": option index 0-3 or null, "rt": ms from Start}.
    hit = the chosen sheet has exactly the holes the reflection simulator produces.
    Metrics: correct, rt, fold count, holes on the key, how many key holes the chosen
    sheet got right (partial credit, for error analysis only)."""
    key = unfold(item["folds"], item["hole"])
    choice, rt = _choice(response)
    picked = None
    if choice is not None and 0 <= choice < len(item["options"]):
        picked = frozenset(tuple(c) for c in item["options"][choice])
    ok = picked == key
    return {"hit": ok, "errors": 0 if ok else 1,
            "metrics": {"correct": ok, "rt": rt if ok else None, "rt_any": rt, "folds": len(item["folds"]),
                        "omission": picked is None, "key_holes": len(key),
                        "holes_matched": len(key & picked) if picked else 0}}


def example_response(item, correct=True):
    key = unfold(item["folds"], item["hole"])
    idx = [frozenset(tuple(c) for c in o) == key for o in item["options"]]
    return {"choice": idx.index(True) if correct else idx.index(False), "rt": 8000}
