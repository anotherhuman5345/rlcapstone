"""Simon (card 23): a colored circle appears on the left or right; press the side
ASSIGNED to its color and ignore where it appears. One trial is a block of 24 displays:
every (color, side) combination 6 times, so 12 compatible (assigned side = position)
and 12 incompatible. The color->side mapping is stored in the item and counterbalanced
across pairs (both items of a pair use the same mapping, so they are equally hard);
the response buttons show the color assigned to each side, so the mapping is always
visible. Colors are blue/orange (distinguishable with common color-vision deficiencies)."""

BLOCK = 24
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


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(float(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2), 1)


def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms}] in display order.
    Compatible = the assigned side equals the stimulus side (uses the item's mapping).
    hit = accuracy >= 0.75 over the 24 displays (omissions count as errors).
    Metrics: Simon RT cost (incompatible - compatible median correct RT), error rates per
    condition and their difference, omissions."""
    try:
        displays = item["displays"]
        item["left_color"]
    except (TypeError, KeyError):
        return {"hit": False, "errors": 0, "metrics": {}}
    resp = response if isinstance(response, list) else []
    rows = []
    for k, d in enumerate(displays):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        key = r.get("key") if r.get("key") in ("left", "right") else None
        rt = r.get("rt")
        rt = float(rt) if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
        ans = _answer(item, d)
        rows.append({"compat": ans == d["side"], "key": key, "rt": rt, "ok": key == ans})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)

    def cond(c):
        sel = [r for r in rows if r["compat"] == c]
        err = round(1 - sum(r["ok"] for r in sel) / len(sel), 3) if sel else None
        return _median([r["rt"] for r in sel if r["ok"] and r["rt"]]), err

    rt_c, err_c = cond(True)
    rt_i, err_i = cond(False)
    acc = n_ok / n if n else 0.0
    return {"hit": n > 0 and acc >= 0.75, "errors": n - n_ok,
            "metrics": {"accuracy": round(acc, 3), "median_rt_compatible": rt_c, "median_rt_incompatible": rt_i,
                        "simon_cost_ms": round(rt_i - rt_c, 1) if rt_c and rt_i else None,
                        "error_rate_compatible": err_c, "error_rate_incompatible": err_i,
                        "simon_error_cost": round(err_i - err_c, 3) if err_c is not None and err_i is not None else None,
                        "valid_rt_trials": sum(1 for r in rows if r["ok"] and r["rt"]),
                        "omissions": sum(1 for r in rows if r["key"] is None)}}


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    out = []
    for d in item["displays"]:
        ans = _answer(item, d)
        out.append({"key": ans if correct else flip[ans], "rt": 450 + 40 * (ans != d["side"])})
    return out
