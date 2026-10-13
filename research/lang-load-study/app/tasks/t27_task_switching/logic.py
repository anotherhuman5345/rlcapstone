"""Cued task switching (card 27): a cue word (COLOR or SHAPE, from the text file in the
trial's language) says which feature to judge; then a blue/orange circle/square appears
and is classified with two shared keys: COLOR blue=left, orange=right; SHAPE circle=left,
square=right. One trial is 25 events: the first has no switch label; the other 24 are a
full 2 (switch/repeat) x 2 (cue-stimulus interval 200/800 ms) x 2 (congruent/incongruent:
both rules give the same / different keys) design with 3 events per cell, shuffled.
Every item has this exact composition, so the two items of a pair are equally hard."""

from app.tasks import _guard as G

TIMING = "window"
EVENTS_PER_CELL = 3
WINDOW_MS = 2000        # view.js: out.push(await answer(2000)) - each stimulus waits at most 2000 ms
CEILING_MS = G.trial_ceiling(__file__)
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
    """Both rules give the same key (recomputed from the stimulus features)."""
    return (ev["color"] == 0) == (ev["shape"] == "circle")


def _switches(events):
    """Switch labels recomputed from the cued tasks: None for the first event, else whether
    its task differs from the previous event's task (the stored "switch" label is not used)."""
    return [None if k == 0 else ev["task"] != events[k - 1]["task"] for k, ev in enumerate(events)]


def _cond(sel):
    rts = [r["rt"] for r in sel if r["ok"]]
    k = sum(r["ok"] for r in sel)
    return {"n": len(sel), "correct": k, "accuracy": G.rate(k, len(sel)),
            "error_rate": G.rate(len(sel) - k, len(sel)),
            "omissions": sum(1 for r in sel if r["status"] == G.ABSENT),
            "rt_mean": G.mean(rts), "rt_median": G.median(rts), "rt_n": len(rts)}


def _diff(a, b, nd=1):
    return round(a - b, nd) if a is not None and b is not None else None


@G.safe
def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms from stimulus onset}] per event.
    The correct key applies the cued rule to the stimulus; switch/repeat is recomputed from
    the previous event's task and congruency from the stimulus features.
    Each event is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 2000 ms response window) or timely; only a TIMELY correct key
    counts (an anticipatory, late or malformed press never is correct).
    hit = accuracy >= 0.75 over all 25 events (omissions and invalid entries are errors).
    Metrics (event 1 excluded from switch/repeat): switch cost in median correct RT and in
    error rate, the RT switch cost separately at 200 and 800 ms preparation (and their
    difference = preparation effect), RT congruency cost, omissions, per-condition measures
    (switch / repeat / congruent / incongruent) in by_condition, every event in events."""
    a = G.Audit(CEILING_MS)
    events = item["events"]
    if not isinstance(response, list):
        return a.junk(len(events))
    sw = _switches(events)
    rows = []
    for k, (ev, r) in enumerate(zip(events, a.entries(response, len(events)))):
        status, key, rt = a.keyed(r, ("left", "right"), window=WINDOW_MS)
        ok = status == G.TIMELY and key == _answer(ev)
        rows.append({"i": k, "switch": sw[k], "csi": ev["csi"], "congruent": _congruent(ev), "status": status,
                     "rt": rt if ok else None, "ok": ok})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)

    def sel(**kw):
        return [r for r in rows if all(r[f] == v for f, v in kw.items())]

    def mrt(rs):
        return G.median([r["rt"] for r in rs if r["ok"]])

    cond = {"switch": _cond(sel(switch=True)), "repeat": _cond(sel(switch=False)),
            "congruent": _cond(sel(congruent=True)), "incongruent": _cond(sel(congruent=False))}
    rt_sw, rt_rep = cond["switch"]["rt_median"], cond["repeat"]["rt_median"]
    err_sw, err_rep = cond["switch"]["error_rate"], cond["repeat"]["error_rate"]
    cost200 = _diff(mrt(sel(switch=True, csi=200)), mrt(sel(switch=False, csi=200)))
    cost800 = _diff(mrt(sel(switch=True, csi=800)), mrt(sel(switch=False, csi=800)))
    acc = n_ok / n if n else 0.0
    return a.finish(n > 0 and acc >= 0.75, n - n_ok, {
        "accuracy": round(acc, 3),
        "median_rt_switch": rt_sw, "median_rt_repeat": rt_rep,
        "switch_cost_ms": _diff(rt_sw, rt_rep),
        "error_rate_switch": err_sw, "error_rate_repeat": err_rep,
        "switch_error_cost": _diff(err_sw, err_rep, 3),
        "switch_cost_ms_csi200": cost200, "switch_cost_ms_csi800": cost800,
        "preparation_effect_ms": _diff(cost200, cost800),
        "congruency_cost_ms": _diff(cond["incongruent"]["rt_median"], cond["congruent"]["rt_median"]),
        "congruency_error_cost": _diff(cond["incongruent"]["error_rate"], cond["congruent"]["error_rate"], 3),
        "valid_rt_trials": sum(1 for r in rows if r["ok"]),
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "by_condition": cond,
        "events": [{"i": r["i"], "switch": r["switch"], "csi": r["csi"], "congruent": r["congruent"],
                    "status": r["status"], "correct": r["ok"], "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    out = []
    for ev in item["events"]:
        ans = _answer(ev)
        out.append({"key": ans if correct else flip[ans], "rt": 650 + 150 * bool(ev["switch"])})
    return out
