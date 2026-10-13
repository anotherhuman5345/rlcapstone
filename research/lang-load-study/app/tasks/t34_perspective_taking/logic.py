"""Perspective taking (card 34): a top-down map shows six landmarks (coloured symbols).
"Imagine you stand at landmark A, facing landmark B. Where is landmark C: ahead, to your
right, behind you, or to your left?" One trial = one map with 4 questions, one per facing
direction on the map (viewpoint 0/90/180/270 degrees = facing map-up/right/down/left,
each within 20 degrees).

Geometry (the oracle in direction()): map x to the right, y downwards. Heading = compass
angle of B - A; bearing = compass angle of C - A; relative = bearing - heading (mod 360):
ahead 315-45, right 45-135, behind 135-225, left 225-315. Items only use C positions at
least 15 degrees from a sector boundary, so no answer is ambiguous; score() recomputes
the answer from the coordinates, independent of how the map is drawn.

Pairs (k, k+1) share the same four (viewpoint, answer) cells in different order on
different maps, so the two languages get equally hard questions."""

import math

LANDMARKS = 6
VIEWPOINTS = (0, 90, 180, 270)
CATS = ("ahead", "right", "behind", "left")
MARGIN = 15
HEAD_TOL = 20


def _compass(dx, dy):
    return math.degrees(math.atan2(dx, -dy)) % 360


def _geometry(pts, a, b, c):
    (ax, ay), (bx, by), (cx, cy) = pts[a], pts[b], pts[c]
    heading = _compass(bx - ax, by - ay)
    rel = (_compass(cx - ax, cy - ay) - heading) % 360
    return heading, rel


def _cat(rel):
    return CATS[int(((rel + 45) % 360) // 90)]


def direction(pts, a, b, c):
    """Oracle: 'ahead' | 'right' | 'behind' | 'left' for standing at a, facing b, target c."""
    return _cat(_geometry(pts, a, b, c)[1])


def _viewpoint(heading):
    return int(round(heading / 90.0)) % 4 * 90


def _map(rng):
    while True:
        pts = []
        tries = 0
        while len(pts) < LANDMARKS and tries < 500:
            tries += 1
            p = (round(rng.uniform(0.08, 0.92), 3), round(rng.uniform(0.08, 0.92), 3))
            if all(math.dist(p, q) >= 0.2 for q in pts):
                pts.append(p)
        if len(pts) == LANDMARKS:
            return pts


def _fits(pts, a, b, c, vp, cat):
    if len({a, b, c}) < 3 or math.dist(pts[a], pts[b]) < 0.2 or math.dist(pts[a], pts[c]) < 0.15:
        return False
    heading, rel = _geometry(pts, a, b, c)
    dh = abs((heading - vp + 180) % 360 - 180)
    centre = CATS.index(cat) * 90
    dr = abs((rel - centre + 180) % 360 - 180)
    return dh <= HEAD_TOL and dr <= 45 - MARGIN


def _item(rng, specs, max_maps=300):
    """One map answering the four (viewpoint, answer) specs, or None when max_maps random
    maps all fail (some spec combinations are very rare)."""
    order = list(specs)
    rng.shuffle(order)
    for _ in range(max_maps):
        pts = _map(rng)
        triples = [(a, b, c) for a in range(LANDMARKS) for b in range(LANDMARKS) for c in range(LANDMARKS)]
        qs, used_at = [], set()
        for vp, cat in order:
            options = [t for t in triples if _fits(pts, *t, vp, cat) and t[0] not in used_at]
            if not options:
                break
            a, b, c = rng.choice(options)
            used_at.add(a)  # a new standing point for every question
            qs.append({"at": a, "face": b, "to": c})
        if len(qs) == len(order):
            return {"landmarks": [list(p) for p in pts], "questions": qs}
    return None


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        # Both items of a pair share the specs; if either is too rare, draw new specs.
        specs = [(vp, rng.choice(CATS)) for vp in VIEWPOINTS]
        first = _item(rng, specs)
        second = _item(rng, specs) if first else None
        if second:
            items += [first, second]
    return items[:n]


def score(item, response):
    """response: [{"dir": "ahead"|"right"|"behind"|"left"|null, "rt": ms}] in question order.
    hit = at least 3 of the 4 questions right (omissions are wrong). Metrics: accuracy,
    accuracy and mean correct RT per viewpoint (0/90/180/270), omissions."""
    resp = response if isinstance(response, list) else []
    pts = [tuple(p) for p in item["landmarks"]]
    rows = []
    for k, q in enumerate(item["questions"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        rt = r.get("rt")
        rt = rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
        heading, _ = _geometry(pts, q["at"], q["face"], q["to"])
        ans = direction(pts, q["at"], q["face"], q["to"])
        rows.append({"vp": _viewpoint(heading), "ok": r.get("dir") == ans, "rt": rt, "dir": r.get("dir")})
    n_ok = sum(r["ok"] for r in rows)
    by_vp_acc, by_vp_rt = {}, {}
    for vp in VIEWPOINTS:
        sel = [r for r in rows if r["vp"] == vp]
        if sel:
            by_vp_acc[str(vp)] = round(sum(r["ok"] for r in sel) / len(sel), 3)
            rts = [r["rt"] for r in sel if r["ok"] and r["rt"]]
            by_vp_rt[str(vp)] = round(sum(rts) / len(rts), 1) if rts else None
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"]]
    return {"hit": n_ok >= 3, "errors": len(rows) - n_ok,
            "metrics": {"accuracy": round(n_ok / len(rows), 3), "accuracy_by_viewpoint": by_vp_acc,
                        "rt_by_viewpoint": by_vp_rt, "rt_correct_mean": round(sum(rts) / len(rts), 1) if rts else None,
                        "omissions": sum(1 for r in rows if r["dir"] is None)}}


def example_response(item, correct=True):
    pts = [tuple(p) for p in item["landmarks"]]
    out = []
    for q in item["questions"]:
        ans = direction(pts, q["at"], q["face"], q["to"])
        out.append({"dir": ans if correct else CATS[(CATS.index(ans) + 2) % 4], "rt": 4000})
    return out
