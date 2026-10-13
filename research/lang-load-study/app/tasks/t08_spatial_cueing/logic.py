"""Spatial cueing (card 08): keep the eyes on the centre, an arrow cue points left or
right, and 200 ms later a dot appears in the left or right box; press the key for the
side of the dot. One trial is a block of 20 events: 14 valid cues (70 %) and 6 invalid
ones, with the target on the left and right equally often (7+3 per side). Both items of
a pair have exactly this composition, only the order differs. Validity is computed
from the actual cue and target sides, never stored as a separate answer.
There is no eye tracking: central fixation is requested, not verified."""
import math

BLOCK_VALID = 14      # per block; 7 left + 7 right
BLOCK_INVALID = 6     # per block; 3 left + 3 right
CTI_MS = 200          # cue-target interval
LIMIT_MS = 1500       # response window after target onset
ANTICIPATION_MS = 100  # faster responses are flagged and kept out of the RT means
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


def _events(response):
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def _rt(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if 0 <= v <= LIMIT_MS + 500 else None


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2, 1)


def score(item, response):
    """response: {"events": [{"key": "left"|"right"|null, "rt": ms from target onset,
    "early": presses before the target}], "interruptions": n} (a bare list of events is
    also accepted), in event order.
    An event is correct when the key names the side the target appeared on; a missing
    key is an omission (counted as an error). hit = accuracy >= 0.80 over all 20 events.
    Metrics: accuracy, omissions, median correct RT for valid and invalid cues, the cueing
    effect (invalid minus valid median RT), anticipations (< 100 ms, excluded from RTs)."""
    try:
        evs = item["events"]
        resp = _events(response)
        rows = []
        for k, e in enumerate(evs):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            key = r.get("key") if r.get("key") in ("left", "right") else None
            rt = _rt(r.get("rt")) if key else None
            rows.append({"valid": e["cue"] == e["target"], "ok": key == e["target"], "key": key, "rt": rt})
        correct = sum(r["ok"] for r in rows)
        acc = correct / len(rows)
        antic = sum(1 for r in rows if r["rt"] is not None and r["rt"] < ANTICIPATION_MS)

        def med(valid):
            return _median([r["rt"] for r in rows if r["ok"] and r["valid"] == valid
                            and r["rt"] is not None and r["rt"] >= ANTICIPATION_MS])

        rv, ri = med(True), med(False)
        n_valid = sum(r["valid"] for r in rows)
        inter = response.get("interruptions") if isinstance(response, dict) else None
        return {"hit": acc >= 0.8, "errors": len(rows) - correct,
                "metrics": {"accuracy": round(acc, 3),
                            "accuracy_valid": round(sum(r["ok"] for r in rows if r["valid"]) / max(n_valid, 1), 3),
                            "accuracy_invalid": round(sum(r["ok"] for r in rows if not r["valid"]) / max(len(rows) - n_valid, 1), 3),
                            "omissions": sum(1 for r in rows if r["key"] is None),
                            "rt_valid_median": rv, "rt_invalid_median": ri,
                            "cueing_effect_ms": round(ri - rv, 1) if rv is not None and ri is not None else None,
                            "valid_rt_n": sum(1 for r in rows if r["ok"] and r["rt"] is not None and r["rt"] >= ANTICIPATION_MS),
                            "anticipations": antic,
                            "early_presses": sum(int(r.get("early") or 0) for r in resp if isinstance(r, dict)
                                                 and isinstance(r.get("early"), int)),
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    return {"events": [{"key": e["target"] if correct else FLIP[e["target"]],
                        "rt": 380 + 45 * (e["cue"] != e["target"]), "early": 0}
                       for e in item["events"]], "interruptions": 0}
