"""Visual crowding (card 09): keep the eyes on the central cross; a T-shaped symbol flashes
for 150 ms to the left or right, surrounded by four flanking T's (above, below, left,
right). Report which way the bar of the MIDDLE T faces (up/right/down/left).
One trial is a block of 16 flashes: 2 spacings (narrow = 1.2 x symbol size, wide = 2.5 x)
x 2 eccentricities (near/far) x 2 sides x 2 repeats, shuffled. Both items of a pair
have exactly these cells; only the orientations and order differ.
Geometry is fixed in screen units (an SVG 1000 x 400 box, symbol 30 units). Browser
units are not visual degrees without a viewing-distance calibration, and fixation is
requested, not verified (no eye tracking)."""
import math

SYMBOL = 30
SPACING = {"narrow": 36, "wide": 75}   # centre-to-centre, SVG units (1.2x and 2.5x symbol)
ECC = {"near": 180, "far": 380}         # horizontal distance from the fixation cross
ORIENTS = ["up", "right", "down", "left"]
FLASH_MS = 150
LIMIT_MS = 4000


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        events = []
        for spacing in SPACING:
            for ecc in ECC:
                for side in ("left", "right"):
                    for _rep in range(2):
                        events.append({"spacing": spacing, "ecc": ecc, "side": side,
                                       "target": rng.choice(ORIENTS),
                                       "flankers": [rng.choice(ORIENTS) for _ in range(4)]})
        rng.shuffle(events)
        items.append({"events": events, "geometry": {"symbol": SYMBOL, "spacing": SPACING, "ecc": ECC},
                      "flash_ms": FLASH_MS, "limit_ms": LIMIT_MS})
    return items


def _events(response):
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def _rt(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if 0 <= v <= LIMIT_MS + 500 else None


def score(item, response):
    """response: {"events": [{"answer": "up"|"right"|"down"|"left"|null, "rt": ms from the
    end of the flash}], "interruptions": n} (a bare list is also accepted), in event order.
    An event is correct when the answer equals the target T's orientation (the generated
    stimulus itself is the key). No answer = omission, counted as an error. Chance is 25 %.
    hit = accuracy >= 0.50 over the 16 flashes (twice chance).
    Metrics: accuracy overall, per spacing, per eccentricity and per spacing x eccentricity
    cell, the crowding effect (wide minus narrow accuracy), omissions, median correct RT."""
    try:
        evs = item["events"]
        resp = _events(response)
        rows = []
        for k, e in enumerate(evs):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            ans = r.get("answer") if r.get("answer") in ORIENTS else None
            rows.append({"e": e, "ans": ans, "ok": ans == e["target"], "rt": _rt(r.get("rt")) if ans else None})
        correct = sum(r["ok"] for r in rows)

        def acc(pred):
            sel = [r["ok"] for r in rows if pred(r["e"])]
            return round(sum(sel) / len(sel), 3) if sel else None

        cells = {f"{s}_{c}": acc(lambda e, s=s, c=c: e["spacing"] == s and e["ecc"] == c)
                 for s in SPACING for c in ECC}
        a_n, a_w = acc(lambda e: e["spacing"] == "narrow"), acc(lambda e: e["spacing"] == "wide")
        rts = sorted(r["rt"] for r in rows if r["ok"] and r["rt"] is not None)
        med = None
        if rts:
            m = len(rts) // 2
            med = round(rts[m] if len(rts) % 2 else (rts[m - 1] + rts[m]) / 2, 1)
        inter = response.get("interruptions") if isinstance(response, dict) else None
        total = correct / len(rows)
        return {"hit": total >= 0.5, "errors": len(rows) - correct,
                "metrics": {"accuracy": round(total, 3),
                            "accuracy_narrow": a_n, "accuracy_wide": a_w,
                            "accuracy_near": acc(lambda e: e["ecc"] == "near"),
                            "accuracy_far": acc(lambda e: e["ecc"] == "far"),
                            "accuracy_by_cell": cells,
                            "crowding_effect": round(a_w - a_n, 3) if a_n is not None and a_w is not None else None,
                            "omissions": sum(1 for r in rows if r["ans"] is None),
                            "rt_correct_median": med, "rt_n": len(rts),
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    turn = {"up": "down", "down": "up", "left": "right", "right": "left"}
    return {"events": [{"answer": e["target"] if correct else turn[e["target"]], "rt": 900}
                       for e in item["events"]], "interruptions": 0}
