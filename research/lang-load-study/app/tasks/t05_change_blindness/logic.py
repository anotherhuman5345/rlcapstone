"""Change blindness (card 05): two versions of a scene of simple shapes alternate
(240 ms scene, 80 ms blank, flicker paradigm) until the person clicks the one object that
differs, or 20 s pass. One trial is 3 scenes; the change types colour / disappears / shape
appear once each (shuffled). Scenes are drawn by the browser from the object lists below
(all original, generated here). Pairs (k, k+1) share the change-type order, the number of
objects and the size of the changed object; only layout, colours and shapes differ.

Hitbox of an object: circle around its centre with radius size * HIT_SCALE + HIT_PAD."""
import math
import statistics

W, H = 800, 533
N_OBJ = 14
COLS, ROWS = 6, 4
SHAPES = ["circle", "square", "triangle", "diamond", "star", "hexagon"]
COLOURS = ["#C0392B", "#2471A3", "#229954", "#D4AC0D", "#7D3C98", "#E67E22", "#17A589", "#566573"]
BACKGROUNDS = ["#F4F1EA", "#EEF3F7", "#F3EEF5", "#EFF5EE"]
CHANGES = ("colour", "remove", "shape")
HIT_SCALE, HIT_PAD = 0.6, 10
CHANGED_SIZE = 62
SCENE_MS, BLANK_MS, LIMIT_MS = 240, 80, 20000


def _scene(rng, change):
    cw, ch = W / COLS, H / ROWS
    slots = rng.sample(range(COLS * ROWS), N_OBJ)
    a = []
    for i, s in enumerate(slots):
        cx, cy = cw * (s % COLS) + cw / 2, ch * (s // COLS) + ch / 2
        a.append({"id": i, "shape": rng.choice(SHAPES), "c": rng.choice(COLOURS),
                  "x": round(cx + rng.uniform(-22, 22)), "y": round(cy + rng.uniform(-22, 22)),
                  "s": rng.randint(46, 72), "rot": rng.choice([0, 15, 30, 45])})
    target = rng.randrange(N_OBJ)
    a[target]["s"] = CHANGED_SIZE
    b = [dict(o) for o in a]
    if change == "colour":
        b[target]["c"] = rng.choice([c for c in COLOURS if c != a[target]["c"]])
    elif change == "shape":
        b[target]["shape"] = rng.choice([s for s in SHAPES if s != a[target]["shape"]])
    else:
        del b[target]
    return {"bg": rng.choice(BACKGROUNDS), "change": change, "a": a, "b": b}


def generate(rng, n, save_image):
    items, order = [], None
    for k in range(n):
        if k % 2 == 0:
            order = list(CHANGES)
            rng.shuffle(order)
        items.append({"w": W, "h": H, "scene_ms": SCENE_MS, "blank_ms": BLANK_MS, "limit_ms": LIMIT_MS,
                      "hit_scale": HIT_SCALE, "hit_pad": HIT_PAD, "scenes": [_scene(rng, c) for c in order]})
    return items


def changed_object(scene):
    """Oracle: the one object of scene A that is missing from B or differs in B."""
    b = {o["id"]: o for o in scene["b"]}
    diff = [o for o in scene["a"] if o["id"] not in b or any(o[k] != b[o["id"]][k] for k in o)]
    return diff[0] if len(diff) == 1 else None


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def score(item, response):
    """response: [{"clicks": [{"x": 0..1, "y": 0..1, "t": ms}, ...]}] per scene, x/y as
    fractions of the scene width/height, t from flicker start. A scene is found when a click
    lands inside the changed object's hitbox within the time limit; time to find = that
    click's t; incorrect clicks = clicks before it (or all clicks when not found).
    hit = changed object found in at least 2 of the 3 scenes."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, sc in enumerate(item["scenes"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        clicks = r.get("clicks") if isinstance(r.get("clicks"), list) else []
        tgt = changed_object(sc)
        rad = tgt["s"] * item["hit_scale"] + item["hit_pad"] if tgt else 0
        found_t, wrong = None, 0
        for c in clicks:
            if not isinstance(c, dict):
                continue
            x, y, t = _num(c.get("x")), _num(c.get("y")), _num(c.get("t"))
            if x is None or y is None:
                continue
            if tgt and math.hypot(x * item["w"] - tgt["x"], y * item["h"] - tgt["y"]) <= rad \
                    and (t is None or t <= item["limit_ms"] + 100):
                found_t = t if t is not None else float(item["limit_ms"])
                break
            wrong += 1
        rows.append({"change": sc["change"], "found": found_t is not None, "t": found_t, "wrong": wrong})
    found = [r for r in rows if r["found"]]
    times = [r["t"] for r in found]
    return {"hit": len(found) >= 2, "errors": sum(r["wrong"] for r in rows) + len(rows) - len(found),
            "metrics": {"found": len(found), "failures": len(rows) - len(found),
                        "incorrect_clicks": sum(r["wrong"] for r in rows),
                        "median_time_to_find_ms": round(statistics.median(times), 1) if times else None,
                        "time_to_find_by_change": {r["change"]: (round(r["t"], 1) if r["found"] else None) for r in rows}}}


def example_response(item, correct=True):
    out = []
    for sc in item["scenes"]:
        tgt = changed_object(sc)
        if correct:
            clicks = [{"x": round(tgt["x"] / item["w"], 4), "y": round(tgt["y"] / item["h"], 4), "t": 4000}]
        else:   # a click on the opposite corner of the scene (never on the changed object)
            fx = 0.02 if tgt["x"] > item["w"] / 2 else 0.98
            fy = 0.02 if tgt["y"] > item["h"] / 2 else 0.98
            clicks = [{"x": fx, "y": fy, "t": 3000}]
        out.append({"clicks": clicks})
    return out
