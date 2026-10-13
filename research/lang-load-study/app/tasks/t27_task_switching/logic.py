"""Cued task switching (card 27): a cue word (COLOR or SHAPE, from the text file in the
trial's language) says which feature to judge; then a blue/orange circle/square appears
and is classified with two shared keys: COLOR blue=left, orange=right; SHAPE circle=left,
square=right. One trial is 25 events: the first has no switch label; the other 24 are a
full 2 (switch/repeat) x 2 (cue-stimulus interval 200/800 ms) x 2 (congruent/incongruent:
both rules give the same / different keys) design with 3 events per cell, shuffled.
Every item has this exact composition, so the two items of a pair are equally hard."""

EVENTS_PER_CELL = 3
PALETTE = ["#0072B2", "#E69F00"]  # 0 blue -> left, 1 orange -> right
SHAPES = ["circle", "square"]     # circle -> left, square -> right


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        cells = [(sw, csi, cg) for sw in (True, False) for csi in (200, 800) for cg in (True, False)
                 for _ in range(EVENTS_PER_CELL)]
        rng.shuffle(cells)
        task = rng.choice(["color", "shape"])
        events = [_event(rng, task, None, rng.choice([200, 800]), rng.choice([True, False]))]
        for sw, csi, cg in cells:
            if sw:
                task = "shape" if task == "color" else "color"
            events.append(_event(rng, task, sw, csi, cg))
        items.append({"palette": PALETTE, "events": events})
    return items


def _event(rng, task, switch, csi, congruent):
    color = rng.choice([0, 1])
    # congruent: both rules point to the same key (blue circle, orange square)
    shape = SHAPES[color] if congruent else SHAPES[1 - color]
    return {"task": task, "switch": switch, "csi": csi, "color": color, "shape": shape}


def _answer(ev):
    """Oracle: apply the cued rule to the stimulus features."""
    if ev["task"] == "color":
        return "left" if ev["color"] == 0 else "right"
    return "left" if ev["shape"] == "circle" else "right"


def _congruent(ev):
    return (ev["color"] == 0) == (ev["shape"] == "circle")


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(float(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2), 1)


def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms from stimulus onset}] per event.
    hit = accuracy >= 0.75 over all 25 events (omissions count as errors).
    Metrics (event 1 excluded from switch/repeat): switch cost in median correct RT and in
    error rate, the RT switch cost separately at 200 and 800 ms preparation (and their
    difference = preparation effect), RT congruency cost, omissions."""
    try:
        events = item["events"]
        [_answer(ev) for ev in events]
    except (TypeError, KeyError, IndexError):
        return {"hit": False, "errors": 0, "metrics": {}}
    resp = response if isinstance(response, list) else []
    rows = []
    for k, ev in enumerate(events):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        key = r.get("key") if r.get("key") in ("left", "right") else None
        rt = r.get("rt")
        rt = float(rt) if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
        rows.append({"ev": ev, "key": key, "rt": rt, "ok": key == _answer(ev)})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)

    def sel(**kw):
        return [r for r in rows if all((r["ev"]["switch"] if f == "switch" else
                                        r["ev"]["csi"] if f == "csi" else _congruent(r["ev"])) == v
                                       for f, v in kw.items())]

    def mrt(rs):
        return _median([r["rt"] for r in rs if r["ok"] and r["rt"]])

    def err(rs):
        return round(1 - sum(r["ok"] for r in rs) / len(rs), 3) if rs else None

    def diff(a, b, nd=1):
        return round(a - b, nd) if a is not None and b is not None else None

    rt_sw, rt_rep = mrt(sel(switch=True)), mrt(sel(switch=False))
    cost200 = diff(mrt(sel(switch=True, csi=200)), mrt(sel(switch=False, csi=200)))
    cost800 = diff(mrt(sel(switch=True, csi=800)), mrt(sel(switch=False, csi=800)))
    acc = n_ok / n if n else 0.0
    return {"hit": n > 0 and acc >= 0.75, "errors": n - n_ok,
            "metrics": {"accuracy": round(acc, 3),
                        "median_rt_switch": rt_sw, "median_rt_repeat": rt_rep,
                        "switch_cost_ms": diff(rt_sw, rt_rep),
                        "error_rate_switch": err(sel(switch=True)), "error_rate_repeat": err(sel(switch=False)),
                        "switch_error_cost": diff(err(sel(switch=True)), err(sel(switch=False)), 3),
                        "switch_cost_ms_csi200": cost200, "switch_cost_ms_csi800": cost800,
                        "preparation_effect_ms": diff(cost200, cost800),
                        "congruency_cost_ms": diff(mrt(sel(congruent=False)), mrt(sel(congruent=True))),
                        "valid_rt_trials": sum(1 for r in rows if r["ok"] and r["rt"]),
                        "omissions": sum(1 for r in rows if r["key"] is None)}}


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    out = []
    for ev in item["events"]:
        ans = _answer(ev)
        out.append({"key": ans if correct else flip[ans], "rt": 650 + 150 * bool(ev["switch"])})
    return out
