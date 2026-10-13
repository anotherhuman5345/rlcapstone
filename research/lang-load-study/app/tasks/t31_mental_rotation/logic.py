"""Mental rotation (card 31): two original 2D shapes are shown side by side; the right
one is turned by 0, 60, 120 or 180 degrees. Is it the SAME shape turned, or its MIRROR
image? One trial is a short block of 8 displays: every angle once as "same" and once as
"mirror", in shuffled order, each with a new shape. Both items of a pair (k, k+1) have
exactly these 8 cells (same angles, same 7-square shape size), so they are equally hard.

Shapes are 7-square polyominoes that are chiral: the mirror image can never be turned
into the original (checked against all 90-degree turns; turns by 60/120 degrees cannot map
a square-grid shape onto a grid shape, so no other turn can either). The answer key is not
stored: score() decides "same" or "mirror" by comparing the right shape's squares with
the left shape's under every turn."""

from app.tasks import _guard as G

TIMING = "window"
WINDOW_MS = 7000        # view.js: out.push(await answer(7000)) - each display waits at most 7 s
CEILING_MS = G.trial_ceiling(__file__)
SIZE = 7
ANGLES = (0, 60, 120, 180)
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def _norm(cells):
    mx = min(x for x, _ in cells)
    my = min(y for _, y in cells)
    return tuple(sorted((x - mx, y - my) for x, y in cells))


def _rot90(cells):
    return _norm([(-y, x) for x, y in cells])


def _mirror(cells):
    return _norm([(-x, y) for x, y in cells])


def _turns(cells):
    out, c = [], _norm(cells)
    for _ in range(4):
        out.append(c)
        c = _rot90(c)
    return out


def _chiral(cells):
    return _mirror(cells) not in _turns(cells)


def _shape(rng):
    while True:
        cells = {(0, 0)}
        while len(cells) < SIZE:
            x, y = rng.choice(sorted(cells))
            dx, dy = rng.choice(STEPS)
            cells.add((x + dx, y + dy))
        c = _norm(cells)
        w = max(x for x, _ in c) + 1
        h = max(y for _, y in c) + 1
        if max(w, h) <= 4 and min(w, h) >= 2 and _chiral(c):
            return c


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        displays = []
        for angle in ANGLES:
            for same in (True, False):
                base = _shape(rng)
                right = base if same else _mirror(base)
                right = _turns(right)[rng.randrange(4)]  # different grid start, same handedness
                rot_left = rng.choice(range(0, 360, 30))
                sign = rng.choice((1, -1))
                displays.append({"left": [list(p) for p in base], "right": [list(p) for p in right],
                                 "rot_left": rot_left, "rot_right": (rot_left + sign * angle) % 360})
        rng.shuffle(displays)
        items.append({"displays": displays})
    return items


def _cells(v):
    try:
        out = [(int(p[0]), int(p[1])) for p in v]
        return out if out else None
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def key(display):
    """Oracle: 'same' when the right squares are a turn of the left squares, 'mirror' when
    they are a turn of the left's mirror image. The displayed rotation (rot_right) is a
    true rotation of the whole drawing, so it never changes handedness."""
    left, right = _cells(display["left"]), _cells(display["right"])
    if _norm(right) in _turns(left):
        return "same"
    if _norm(right) in _turns(_mirror(left)):
        return "mirror"
    raise ValueError("display shapes do not match")


def angle(display):
    d = abs(int(display["rot_right"]) - int(display["rot_left"])) % 360
    return min(d, 360 - d)


@G.safe
def score(item, response):
    """response: [{"key": "same"|"mirror"|null, "rt": ms}] in display order. The answer
    key is recomputed from the two shapes (key()).
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 7000 ms response window) or timely; only a TIMELY key equal to
    the answer is correct (an anticipatory, late or malformed answer never is).
    hit = at least 75% of the 8 displays answered correctly (6 of 8); omissions and
    invalid entries count as errors. Metrics: accuracy, mean correct RT per angle and for
    same/mirror, the RT slope per degree (rotation cost), omissions, every display's status
    in events."""
    a = G.Audit(CEILING_MS)
    displays = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(displays))
    rows = []
    for k, (d, r) in enumerate(zip(displays, a.entries(response, len(displays)))):
        ans = key(d)
        status, kk, rt = a.keyed(r, ("same", "mirror"), window=WINDOW_MS)
        ok = status == G.TIMELY and kk == ans
        rows.append({"i": k, "answer": ans, "angle": angle(d), "status": status, "rt": rt if ok else None, "ok": ok})
    n_ok = sum(r["ok"] for r in rows)
    acc = n_ok / len(rows) if rows else 0.0

    def mean_rt(sel):
        return G.mean([r["rt"] for r in rows if r["ok"] and sel(r)])

    by_angle = {str(x): mean_rt(lambda r, x=x: r["angle"] == x) for x in ANGLES}
    acc_angle = {str(x): round(sum(r["ok"] for r in rows if r["angle"] == x) /
                               max(1, sum(1 for r in rows if r["angle"] == x)), 3) for x in ANGLES}
    pts = [(r["angle"], r["rt"]) for r in rows if r["ok"]]
    slope = None
    if len({x for x, _ in pts}) >= 2:
        mx = sum(x for x, _ in pts) / len(pts)
        my = sum(t for _, t in pts) / len(pts)
        sxx = sum((x - mx) ** 2 for x, _ in pts)
        slope = round(sum((x - mx) * (t - my) for x, t in pts) / sxx, 2)
    return a.finish(bool(rows) and n_ok >= 0.75 * len(rows), len(rows) - n_ok, {
        "accuracy": round(acc, 3), "rt_by_angle": by_angle, "accuracy_by_angle": acc_angle,
        "rt_same": mean_rt(lambda r: r["answer"] == "same"),
        "rt_mirror": mean_rt(lambda r: r["answer"] == "mirror"),
        "rt_slope_ms_per_deg": slope,
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "events": [{"i": r["i"], "angle": r["angle"], "answer": r["answer"], "status": r["status"],
                    "correct": r["ok"], "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    flip = {"same": "mirror", "mirror": "same"}
    return [{"key": key(d) if correct else flip[key(d)], "rt": 900 + 8 * angle(d)} for d in item["displays"]]
