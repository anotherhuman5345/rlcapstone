"""Feature search (card 01): find the one orange circle among blue circles and click it,
or answer "absent" when there is none. One trial is a short block of 12 displays:
set sizes 8/16/32 x target present/absent x 2, in shuffled order (target presence 50%).
Objects sit on a jittered 8x5 grid, so they never overlap; object size is constant.
The two items of a pair (k, k+1) share the same order of set sizes and presence, only
the positions differ, so the L1 and L2 versions are equally hard."""
import math
from statistics import NormalDist

from app.tasks import _guard as G

TIMING = "window"

W, H, R = 600, 400, 16          # drawing area (SVG units) and circle radius
HIT_R = 24                      # click hitbox radius around a circle centre (drawn r + 8)
COLS, ROWS = 8, 5
TARGET, DISTRACTOR = "#E8710A", "#2B6CB0"   # orange / blue (distinct for common colour-vision types)
SET_SIZES = (8, 16, 32)
REPEATS = 2
LIMIT_MS = 3000                 # response window per display
WINDOW_MS = LIMIT_MS            # view.js: answer(it.limit_ms), item limit_ms = 3000
RT_SLACK_MS = 50                # timer tolerance (the old scorer already allowed limit + 50)
CLICK_TOL = 1.0                 # SVG units of rounding tolerance for a reported click point
VIAS = ("key", "button", "pointer")
CEILING_MS = G.trial_ceiling(__file__)


def _cells():
    cells = [(s, p) for s in SET_SIZES for p in (True, False)] * REPEATS
    return cells


def _display(rng, set_size, present):
    cw, ch = W / COLS, H / ROWS
    slots = rng.sample(range(COLS * ROWS), set_size)
    objs = []
    for s in slots:
        cx, cy = cw * (s % COLS) + cw / 2, ch * (s // COLS) + ch / 2
        objs.append({"x": round(cx + rng.uniform(-11, 11)), "y": round(cy + rng.uniform(-11, 11)),
                     "c": DISTRACTOR})
    if present:
        objs[rng.randrange(set_size)]["c"] = TARGET
    return {"set_size": set_size, "objects": objs}


def generate(rng, n, save_image):
    items, order = [], None
    for k in range(n):
        if k % 2 == 0:                       # new structure for each pair
            order = _cells()
            rng.shuffle(order)
        items.append({"w": W, "h": H, "r": R, "hit_r": HIT_R, "limit_ms": LIMIT_MS,
                      "target_color": TARGET, "distractor_color": DISTRACTOR,
                      "displays": [_display(rng, s, p) for s, p in order]})
    return items


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def _location(a, r, d, choice):
    """Validate the location fields of a timely answer {obj, via, x, y} against the display.
    Returns (usable, wrong_loc). A pointer answer must name a circle and its reported point
    (x, y as fractions of the drawing area) must lie in that circle's hitbox: the clicked
    circle is recomputed from the geometry, never trusted from "obj" alone. Key/button
    answers carry no location (obj, x, y null); "absent" never has one."""
    objs = d["objects"]
    obj = r.get("obj", G.MISSING)
    if obj is G.MISSING:
        a.malformed("missing_obj")
        return False, False
    if obj is not None and not (G.is_int(obj) and 0 <= obj < len(objs)):
        a.malformed("invalid_obj")
        return False, False
    via = r.get("via", G.MISSING)
    if via is G.MISSING:
        a.flag("missing_via")          # older payloads: no location check possible
        if choice == "absent" and obj is not None:
            a.malformed("obj_with_absent")
            return False, False
        return True, obj is not None and objs[obj]["c"] != d["_tc"]
    if not G.member(via, VIAS):
        a.malformed("invalid_via")
        return False, False
    x, y = r.get("x"), r.get("y")
    if via != "pointer":
        if obj is not None or x is not None or y is not None:
            a.malformed("location_without_pointer")
            return False, False
        return True, False
    if choice != "present" or obj is None:
        a.malformed("pointer_without_obj")
        return False, False
    if not (G.is_num(x) and G.is_num(y)):
        a.malformed("invalid_click_point")
        return False, False
    o = objs[obj]
    if math.hypot(x * d["_w"] - o["x"], y * d["_h"] - o["y"]) > d["_hr"] + CLICK_TOL:
        a.malformed("click_outside_obj")
        return False, False
    return True, o["c"] != d["_tc"]


@G.safe
def score(item, response):
    """response: [{"choice": "present"|"absent"|null, "obj": index|null, "via":
    "key"|"button"|"pointer"|null, "x": 0-1|null, "y": 0-1|null, "rt": ms}] in display
    order. "obj" is the index of the clicked circle (null when "present" was given with the
    key/button, which has no location); x, y the click point as fractions of the drawing
    area. Answer key: the target is counted from the colours; a pointer answer is checked
    against the geometry (the point must lie in the named circle's hitbox).
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 3000 ms response window + 50 ms timer tolerance) or timely.
    A display is correct only with a TIMELY, well-formed answer: target present ->
    "present" and, if a circle was clicked, it is the target; target absent -> "absent".
    Omissions, anticipatory, late and malformed answers are errors.
    hit = accuracy >= 0.75 (chance is about 0.5)."""
    a = G.Audit(CEILING_MS)
    displays = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(displays))
    tc = item["target_color"]
    geo = {"_tc": tc, "_w": item.get("w", W), "_h": item.get("h", H), "_hr": item.get("hit_r", HIT_R)}
    rows = []
    for k, (d, r) in enumerate(zip(displays, a.entries(response, len(displays)))):
        targets = [i for i, o in enumerate(d["objects"]) if o["c"] == tc]
        present = len(targets) == 1
        status, choice, rt = a.keyed(r, ("present", "absent"), key="choice", window=WINDOW_MS, slack=RT_SLACK_MS)
        made, wrong_loc = None, False
        if status == G.TIMELY:
            usable, wrong_loc = _location(a, r, dict(d, **geo), choice)
            made = choice if usable else None
            wrong_loc = usable and wrong_loc
        ok = (made == "present" and not wrong_loc) if present else made == "absent"
        rows.append({"i": k, "size": d["set_size"], "present": present, "status": status, "made": made, "ok": ok,
                     "wrong_loc": wrong_loc, "rt": rt if ok else None})
    n = len(rows)
    sig = [r for r in rows if r["present"]]
    noise = [r for r in rows if not r["present"]]
    hits = sum(r["ok"] for r in sig)
    fas = sum(r["made"] == "present" for r in noise)
    acc = sum(r["ok"] for r in rows) / n if n else 0.0
    by_size = {str(s): G.median([r["rt"] for r in rows if r["size"] == s and r["ok"]]) for s in SET_SIZES}
    return a.finish(n > 0 and acc >= 0.75, n - sum(r["ok"] for r in rows), {
        "accuracy": round(acc, 3), "hits": hits, "misses": len(sig) - hits,
        "false_alarms": fas, "correct_rejections": sum(r["ok"] for r in noise),
        "hit_rate": G.rate(hits, len(sig)), "fa_rate": G.rate(fas, len(noise)),
        "dprime": dprime(hits, len(sig), fas, len(noise)),
        "wrong_location": sum(r["wrong_loc"] for r in rows),
        "omissions": sum(r["status"] == G.ABSENT for r in rows),
        "median_rt_correct_by_size": by_size,
        "n_valid_rt": sum(1 for r in rows if r["ok"]),
        "events": [{"i": r["i"], "set_size": r["size"], "present": r["present"], "status": r["status"],
                    "correct": r["ok"], "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        targets = [i for i, o in enumerate(d["objects"]) if o["c"] == item["target_color"]]
        present = bool(targets)
        if present == correct:
            if targets:
                o = d["objects"][targets[0]]
                out.append({"choice": "present", "obj": targets[0], "via": "pointer",
                            "x": round(o["x"] / item["w"], 4), "y": round(o["y"] / item["h"], 4),
                            "rt": 600 + d["set_size"]})
            else:
                out.append({"choice": "present", "obj": None, "via": "key", "x": None, "y": None, "rt": 650})
        else:
            out.append({"choice": "absent", "obj": None, "via": "key", "x": None, "y": None, "rt": 900})
    return out
