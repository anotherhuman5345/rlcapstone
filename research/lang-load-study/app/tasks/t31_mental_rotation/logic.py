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


def score(item, response):
    """response: [{"key": "same"|"mirror"|null, "rt": ms}] in display order.
    hit = at least 75% of the 8 displays answered correctly (6 of 8); omissions count as
    errors. Metrics: accuracy, mean correct RT per angle and for same/mirror, the RT slope
    per degree (rotation cost), omissions."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, d in enumerate(item["displays"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        rt = r.get("rt")
        rt = rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
        ans = key(d)
        rows.append({"answer": ans, "angle": angle(d), "key": r.get("key"), "rt": rt,
                     "ok": r.get("key") == ans})
    n_ok = sum(r["ok"] for r in rows)
    acc = n_ok / len(rows)

    def mean_rt(sel):
        rts = [r["rt"] for r in rows if r["ok"] and r["rt"] and sel(r)]
        return round(sum(rts) / len(rts), 1) if rts else None

    by_angle = {str(a): mean_rt(lambda r, a=a: r["angle"] == a) for a in ANGLES}
    acc_angle = {str(a): round(sum(r["ok"] for r in rows if r["angle"] == a) /
                               max(1, sum(1 for r in rows if r["angle"] == a)), 3) for a in ANGLES}
    pts = [(r["angle"], r["rt"]) for r in rows if r["ok"] and r["rt"]]
    slope = None
    if len({a for a, _ in pts}) >= 2:
        mx = sum(a for a, _ in pts) / len(pts)
        my = sum(t for _, t in pts) / len(pts)
        sxx = sum((a - mx) ** 2 for a, _ in pts)
        slope = round(sum((a - mx) * (t - my) for a, t in pts) / sxx, 2)
    return {"hit": n_ok >= 0.75 * len(rows), "errors": len(rows) - n_ok,
            "metrics": {"accuracy": round(acc, 3), "rt_by_angle": by_angle, "accuracy_by_angle": acc_angle,
                        "rt_same": mean_rt(lambda r: r["answer"] == "same"),
                        "rt_mirror": mean_rt(lambda r: r["answer"] == "mirror"),
                        "rt_slope_ms_per_deg": slope,
                        "omissions": sum(1 for r in rows if r["key"] is None)}}


def example_response(item, correct=True):
    flip = {"same": "mirror", "mirror": "same"}
    return [{"key": key(d) if correct else flip[key(d)], "rt": 900 + 8 * angle(d)} for d in item["displays"]]
