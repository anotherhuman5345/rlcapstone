"""Change blindness (card 05): two versions of a scene of simple shapes alternate
(240 ms scene, 80 ms blank, flicker paradigm) until the person clicks the one object that
differs, or 20 s pass. One trial is 3 scenes; the change types colour / disappears / shape
appear once each (shuffled). Scenes are drawn by the browser from the object lists below
(all original, generated here). Pairs (k, k+1) share the change-type order, the number of
objects and the size of the changed object; only layout, colours and shapes differ.

Hitbox of an object: circle around its centre with radius size * HIT_SCALE + HIT_PAD."""
import math

from app.tasks import _guard as G

TIMING = "limit"        # a find must come inside the scene's LIMIT_MS
CEILING_MS = G.trial_ceiling(__file__)
TIME_SLACK_MS = 100     # frame tolerance at the limit (the old scorer's +100 ms)
MAX_CLICKS = 1000       # per scene

W, H = 800, 533
N_OBJ = 14
COLS, ROWS = 6, 4
SHAPES = ["circle", "square", "triangle", "diamond", "star", "hexagon"]
COLOURS = ["#C0392B", "#2471A3", "#229954", "#D4AC0D", "#7D3C98", "#E67E22", "#17A589", "#566573"]
BACKGROUNDS = ["#F4F1EA", "#EEF3F7", "#F3EEF5", "#EFF5EE"]
CHANGES = ("colour", "remove", "shape")
HIT_SCALE, HIT_PAD = 0.6, 10
CHANGED_SIZE = 62
SCENE_MS, BLANK_MS, LIMIT_MS = 240, 80, 20000   # view.js tick(): if (el >= it.limit_ms) end()


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


def _frac(v):
    """A click coordinate: a finite fraction of the scene size in [0, 1], else None."""
    return float(v) if G.is_num(v) and 0 <= v <= 1 else None


def _scene_row(a, k, sc, entry, item):
    """Score one scene. Malformed clicks (not an object, x/y not a fraction 0..1, a missing
    or invalid time) are flagged and not used. The first well-formed click inside the
    changed object's hitbox ends the scene in the browser: it is a find only when its time
    is valid and inside the limit; any click after it is flagged and ignored."""
    tgt = changed_object(sc)
    rad = tgt["s"] * item["hit_scale"] + item["hit_pad"] if tgt else 0
    d = a.obj(entry, "scene")
    if d is None:
        a.record(G.INVALID)
        return {"change": sc["change"], "found": False, "t": None, "wrong": 0, "status": G.INVALID}
    clicks = a.stream(d.get("clicks", G.MISSING), "clicks", cap=MAX_CLICKS)
    status, found_t, wrong, times, after = G.ABSENT, None, 0, [], 0
    ended = False
    for c in clicks:
        if ended:
            after += 1
            continue
        if not isinstance(c, dict):
            a.malformed("click_not_object")
            continue
        st, t = a.time(c.get("t", G.MISSING), field="t", window=item["limit_ms"], slack=TIME_SLACK_MS,
                       required=True)
        times.append(t if st != G.INVALID else None)
        x, y = _frac(c.get("x")), _frac(c.get("y"))
        if x is None or y is None:
            a.malformed("invalid_xy")
            continue
        if tgt and math.hypot(x * item["w"] - tgt["x"], y * item["h"] - tgt["y"]) <= rad:
            ended, status = True, st
            if st == G.TIMELY:
                found_t = t
            else:
                a.flag("find_outside_time_limit")
            continue
        wrong += 1
    if after:
        a.flag("clicks_after_find", after)
    a.monotonic(times, "t")
    a.record(status)
    return {"change": sc["change"], "found": found_t is not None, "t": found_t, "wrong": wrong,
            "status": status}


@G.safe
def score(item, response):
    """response: [{"clicks": [{"x": 0..1, "y": 0..1, "t": ms}, ...]}] per scene, x/y as
    fractions of the scene width/height, t from flicker start. A scene is found when a click
    lands inside the changed object's hitbox AND that click has a valid time inside the 20 s
    limit (a missing, non-finite, negative, anticipatory or late time is never a find);
    time to find = that click's t; incorrect clicks = clicks before it (or all clicks when
    not found). Missing / extra scene entries, malformed clicks, clicks after the find and
    click times that go backwards are flagged.
    hit = changed object found in at least 2 of the 3 scenes."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, list):
        return a.junk()
    scenes = item["scenes"]
    entries = a.entries(response, len(scenes), "scenes")
    rows = [_scene_row(a, k, sc, entries[k], item) for k, sc in enumerate(scenes)]
    found = [r for r in rows if r["found"]]
    times = [r["t"] for r in found]
    return a.finish(len(found) >= 2, sum(r["wrong"] for r in rows) + len(rows) - len(found), {
        "found": len(found), "failures": len(rows) - len(found),
        "incorrect_clicks": sum(r["wrong"] for r in rows),
        "median_time_to_find_ms": G.median(times),
        "time_to_find_by_change": {r["change"]: (round(r["t"], 1) if r["found"] else None) for r in rows},
        "events": [{"i": k, "change": r["change"], "status": r["status"], "correct": r["found"],
                    "rt": round(r["t"], 1) if r["found"] else None} for k, r in enumerate(rows)]})


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
