"""Feature search (card 01): find the one orange circle among blue circles and click it,
or answer "absent" when there is none. One trial is a short block of 12 displays:
set sizes 8/16/32 x target present/absent x 2, in shuffled order (target presence 50%).
Objects sit on a jittered 8x5 grid, so they never overlap; object size is constant.
The two items of a pair (k, k+1) share the same order of set sizes and presence, only
the positions differ, so the L1 and L2 versions are equally hard."""
import statistics
from statistics import NormalDist

W, H, R = 600, 400, 16          # drawing area (SVG units) and circle radius
HIT_R = 24                      # click hitbox radius around a circle centre (drawn r + 8)
COLS, ROWS = 8, 5
TARGET, DISTRACTOR = "#E8710A", "#2B6CB0"   # orange / blue (distinct for common colour-vision types)
SET_SIZES = (8, 16, 32)
REPEATS = 2
LIMIT_MS = 3000                 # response window per display


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


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and x == x else None


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def score(item, response):
    """response: [{"choice": "present"|"absent"|null, "obj": index|null, "rt": ms}] in display
    order. "obj" is the index of the clicked circle (null when "present" was given with the
    key/button, which has no location). Answer key: the target is counted from the colours.
    A display is correct when: target present -> "present" and, if a circle was clicked, it is
    the target; target absent -> "absent". Omissions are errors.
    hit = accuracy >= 0.75 (chance is about 0.5)."""
    resp = response if isinstance(response, list) else []
    tc = item["target_color"]
    rows = []
    for k, d in enumerate(item["displays"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        targets = [i for i, o in enumerate(d["objects"]) if o["c"] == tc]
        present = len(targets) == 1
        choice = r.get("choice") if r.get("choice") in ("present", "absent") else None
        obj = r.get("obj") if isinstance(r.get("obj"), int) and not isinstance(r.get("obj"), bool) else None
        wrong_loc = choice == "present" and present and obj is not None and obj not in targets
        if present:
            ok = choice == "present" and not wrong_loc
        else:
            ok = choice == "absent"
        rt = _num(r.get("rt"))
        rows.append({"size": d["set_size"], "present": present, "choice": choice, "ok": ok,
                     "wrong_loc": wrong_loc, "rt": rt if rt is not None and 100 <= rt <= LIMIT_MS + 50 else None})
    n = len(rows)
    sig = [r for r in rows if r["present"]]
    noise = [r for r in rows if not r["present"]]
    hits = sum(r["ok"] for r in sig)
    fas = sum(r["choice"] == "present" for r in noise)
    acc = sum(r["ok"] for r in rows) / n if n else 0.0
    by_size = {}
    for s in SET_SIZES:
        rts = [r["rt"] for r in rows if r["size"] == s and r["ok"] and r["rt"] is not None]
        by_size[str(s)] = round(statistics.median(rts), 1) if rts else None
    return {"hit": acc >= 0.75, "errors": n - sum(r["ok"] for r in rows),
            "metrics": {"accuracy": round(acc, 3), "hits": hits, "misses": len(sig) - hits,
                        "false_alarms": fas, "correct_rejections": len(noise) - fas,
                        "hit_rate": round(hits / len(sig), 3) if sig else None,
                        "fa_rate": round(fas / len(noise), 3) if noise else None,
                        "dprime": dprime(hits, len(sig), fas, len(noise)),
                        "wrong_location": sum(r["wrong_loc"] for r in rows),
                        "omissions": sum(r["choice"] is None for r in rows),
                        "median_rt_correct_by_size": by_size,
                        "n_valid_rt": sum(1 for r in rows if r["ok"] and r["rt"] is not None)}}


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        targets = [i for i, o in enumerate(d["objects"]) if o["c"] == item["target_color"]]
        present = bool(targets)
        if present == correct:
            out.append({"choice": "present", "obj": targets[0] if targets else None, "rt": 600 + d["set_size"]})
        else:
            out.append({"choice": "absent", "obj": None, "rt": 900})
    return out
