"""Simon (card 23): a colored circle appears on the left or right; press the side
ASSIGNED to its color and ignore where it appears. One trial is a block of 24 displays:
every (color, side) combination 6 times, so 12 compatible (assigned side = position)
and 12 incompatible. The color->side mapping is stored in the item and counterbalanced
across pairs (both items of a pair use the same mapping, so they are equally hard);
the response buttons show the color assigned to each side, so the mapping is always
visible. Colors are blue/orange (distinguishable with common color-vision deficiencies)."""

from app.tasks import _guard as G

TIMING = "window"
BLOCK = 24
WINDOW_MS = 2000        # view.js: out.push(await answer(2000)) - each circle waits at most 2000 ms
CEILING_MS = G.trial_ceiling(__file__)
PALETTE = ["#0072B2", "#E69F00"]  # 0 blue, 1 orange


def generate(rng, n, save_image):
    items = []
    for k in range(n):
        left_color = (k // 2) % 2
        displays = [{"color": c, "side": s} for c in (0, 1) for s in ("left", "right") for _ in range(6)]
        rng.shuffle(displays)
        items.append({"left_color": left_color, "palette": PALETTE, "displays": displays})
    return items


def _answer(item, d):
    """Oracle: the side assigned to the display's color (location is irrelevant)."""
    return "left" if d["color"] == item["left_color"] else "right"


def _cond(sel):
    rts = [r["rt"] for r in sel if r["ok"]]
    k = sum(r["ok"] for r in sel)
    return {"n": len(sel), "correct": k, "accuracy": G.rate(k, len(sel)),
            "error_rate": G.rate(len(sel) - k, len(sel)),
            "omissions": sum(1 for r in sel if r["status"] == G.ABSENT),
            "rt_mean": G.mean(rts), "rt_median": G.median(rts), "rt_n": len(rts)}


@G.safe
def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms}] in display order.
    Compatible = the assigned side equals the stimulus side (uses the item's mapping).
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 2000 ms response window) or timely; only a TIMELY key equal to
    the assigned side is correct (an anticipatory, late or malformed press never is).
    hit = accuracy >= 0.75 over the 24 displays (omissions and invalid entries are errors).
    Metrics: Simon RT cost (incompatible - compatible median correct RT), error rates per
    condition and their difference, omissions, per-condition measures in by_condition and
    every display's status in metrics["events"]."""
    a = G.Audit(CEILING_MS)
    displays = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(displays))
    rows = []
    for k, (d, r) in enumerate(zip(displays, a.entries(response, len(displays)))):
        ans = _answer(item, d)
        status, key, rt = a.keyed(r, ("left", "right"), window=WINDOW_MS)
        ok = status == G.TIMELY and key == ans
        rows.append({"i": k, "compatible": ans == d["side"], "status": status, "rt": rt if ok else None, "ok": ok})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)
    c = _cond([r for r in rows if r["compatible"]])
    i = _cond([r for r in rows if not r["compatible"]])
    acc = n_ok / n if n else 0.0
    return a.finish(n > 0 and acc >= 0.75, n - n_ok, {
        "accuracy": round(acc, 3), "median_rt_compatible": c["rt_median"], "median_rt_incompatible": i["rt_median"],
        "simon_cost_ms": round(i["rt_median"] - c["rt_median"], 1)
        if c["rt_median"] is not None and i["rt_median"] is not None else None,
        "mean_rt_compatible": c["rt_mean"], "mean_rt_incompatible": i["rt_mean"],
        "error_rate_compatible": c["error_rate"], "error_rate_incompatible": i["error_rate"],
        "simon_error_cost": round(i["error_rate"] - c["error_rate"], 3)
        if c["error_rate"] is not None and i["error_rate"] is not None else None,
        "valid_rt_trials": c["rt_n"] + i["rt_n"],
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "by_condition": {"compatible": c, "incompatible": i},
        "events": [{"i": r["i"], "compatible": r["compatible"], "status": r["status"], "correct": r["ok"],
                    "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    out = []
    for d in item["displays"]:
        ans = _answer(item, d)
        out.append({"key": ans if correct else flip[ans], "rt": 450 + 40 * (ans != d["side"])})
    return out
