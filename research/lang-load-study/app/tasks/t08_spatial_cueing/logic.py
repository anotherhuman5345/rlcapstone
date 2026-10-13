"""Spatial cueing (card 08): keep the eyes on the centre, an arrow cue points left or
right, and 200 ms later a dot appears in the left or right box; press the key for the
side of the dot. One trial is a block of 20 events: 14 valid cues (70 %) and 6 invalid
ones, with the target on the left and right equally often (7+3 per side). Both items of
a pair have exactly this composition, only the order differs. Validity is computed
from the actual cue and target sides, never stored as a separate answer.
There is no eye tracking: central fixation is requested, not verified."""

from app.tasks import _guard as G

TIMING = "window"
BLOCK_VALID = 14      # per block; 7 left + 7 right
BLOCK_INVALID = 6     # per block; 3 left + 3 right
CTI_MS = 200          # cue-target interval
LIMIT_MS = 1500       # response window after target onset (item limit_ms; view.js answer() timer)
WINDOW_MS = LIMIT_MS  # view.js: setTimeout(..., limit) with limit = item.limit_ms = 1500
RT_SLACK_MS = 50      # timer tolerance: the browser stops listening when the 1500 ms timer fires
ANTICIPATION_MS = G.ANTICIPATION_MS  # faster responses are anticipations: never correct
CEILING_MS = G.trial_ceiling(__file__)
FLIP = {"left": "right", "right": "left"}


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        events = []
        for side in ("left", "right"):
            events += [{"cue": side, "target": side}] * (BLOCK_VALID // 2)
            events += [{"cue": FLIP[side], "target": side}] * (BLOCK_INVALID // 2)
        events = [dict(e) for e in events]
        rng.shuffle(events)
        items.append({"events": events, "cti_ms": CTI_MS, "limit_ms": LIMIT_MS})
    return items


def _cond(sel):
    rts = [r["rt"] for r in sel if r["ok"]]
    k = sum(r["ok"] for r in sel)
    return {"n": len(sel), "correct": k, "accuracy": G.rate(k, len(sel)),
            "error_rate": G.rate(len(sel) - k, len(sel)),
            "omissions": sum(1 for r in sel if r["status"] == G.ABSENT),
            "rt_mean": G.mean(rts), "rt_median": G.median(rts), "rt_n": len(rts)}


@G.safe
def score(item, response):
    """response: {"events": [{"key": "left"|"right"|null, "rt": ms from target onset,
    "early": presses before the target}], "interruptions": n} (a bare list of events is
    also accepted, without the metadata), in event order.
    Validity (cue side == target side) and the correct key (the target side) are computed
    from the item. Each event is classified (app/tasks/_guard.py) as absent, invalid,
    anticipatory (< 100 ms), late (> the 1500 ms response window + 50 ms timer tolerance)
    or timely; an event is correct only when a TIMELY key names the target side (an
    anticipatory, late or malformed answer never is). A missing key is an omission.
    hit = accuracy >= 0.80 over all 20 events (omissions and invalid entries are errors).
    Metrics: accuracy (overall, valid, invalid), omissions, median correct RT for valid and
    invalid cues, the cueing effect (invalid minus valid median RT), anticipations,
    per-condition measures in by_condition and every event's status in events."""
    a = G.Audit(CEILING_MS)
    evs = item["events"]
    is_dict = isinstance(response, dict)
    if not (is_dict or isinstance(response, list)):
        return a.junk(len(evs))
    raw = response.get("events") if is_dict else response
    rows, early = [], 0
    for k, (e, r) in enumerate(zip(evs, a.entries(raw, len(evs)))):
        status, key, rt = a.keyed(r, ("left", "right"), window=WINDOW_MS, slack=RT_SLACK_MS)
        if isinstance(r, dict):
            early += a.opt_int(r, "early") or 0
        ok = status == G.TIMELY and key == e["target"]
        rows.append({"i": k, "valid": e["cue"] == e["target"], "status": status, "ok": ok,
                     "rt": rt if ok else None})
    correct = sum(r["ok"] for r in rows)
    acc = correct / len(rows) if rows else 0.0
    v = _cond([r for r in rows if r["valid"]])
    i = _cond([r for r in rows if not r["valid"]])
    meta = response if is_dict else {}
    inter = a.opt_int(meta, "interruptions", required=is_dict)
    return a.finish(bool(rows) and acc >= 0.8, len(rows) - correct, {
        "accuracy": round(acc, 3),
        "accuracy_valid": v["accuracy"] if v["accuracy"] is not None else 0.0,
        "accuracy_invalid": i["accuracy"] if i["accuracy"] is not None else 0.0,
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "rt_valid_median": v["rt_median"], "rt_invalid_median": i["rt_median"],
        "cueing_effect_ms": round(i["rt_median"] - v["rt_median"], 1)
        if v["rt_median"] is not None and i["rt_median"] is not None else None,
        "rt_valid_mean": v["rt_mean"], "rt_invalid_mean": i["rt_mean"],
        "error_rate_valid": v["error_rate"], "error_rate_invalid": i["error_rate"],
        "valid_rt_n": v["rt_n"] + i["rt_n"],
        "anticipations": sum(1 for r in rows if r["status"] == G.ANTICIPATORY),
        "early_presses": early,
        "interruptions": inter,
        "by_condition": {"valid": v, "invalid": i},
        "events": [{"i": r["i"], "valid": r["valid"], "status": r["status"], "correct": r["ok"], "rt": r["rt"]}
                   for r in rows]})


def example_response(item, correct=True):
    return {"events": [{"key": e["target"] if correct else FLIP[e["target"]],
                        "rt": 380 + 45 * (e["cue"] != e["target"]), "early": 0}
                       for e in item["events"]], "interruptions": 0}
