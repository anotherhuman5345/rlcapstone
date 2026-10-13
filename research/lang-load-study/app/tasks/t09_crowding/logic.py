"""Visual crowding (card 09): keep the eyes on the central cross; a T-shaped symbol flashes
for 150 ms to the left or right, surrounded by four flanking T's (above, below, left,
right). Report which way the bar of the MIDDLE T faces (up/right/down/left).
One trial is a block of 16 flashes: 2 spacings (narrow = 1.2 x symbol size, wide = 2.5 x)
x 2 eccentricities (near/far) x 2 sides x 2 repeats, shuffled. Both items of a pair
have exactly these cells; only the orientations and order differ.
Geometry is fixed in screen units (an SVG 1000 x 400 box, symbol 30 units). Browser
units are not visual degrees without a viewing-distance calibration, and fixation is
requested, not verified (no eye tracking)."""

from app.tasks import _guard as G

TIMING = "window"
SYMBOL = 30
SPACING = {"narrow": 36, "wide": 75}   # centre-to-centre, SVG units (1.2x and 2.5x symbol)
ECC = {"near": 180, "far": 380}         # horizontal distance from the fixation cross
ORIENTS = ["up", "right", "down", "left"]
FLASH_MS = 150
LIMIT_MS = 4000
WINDOW_MS = LIMIT_MS    # view.js: answer() timer setTimeout(..., limit), limit = item.limit_ms = 4000
RT_SLACK_MS = 50        # timer tolerance
FLASH_TOL = (FLASH_MS / 2, FLASH_MS * 2)   # observed flash duration outside this -> flash_ms_off flag
CEILING_MS = G.trial_ceiling(__file__)


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


def _flash(a, r):
    """The observed flash duration of one event (view.js rAF-to-rAF estimate).
    Returns (usable, value): a malformed value (wrong type, null, non-finite, negative,
    impossible) makes the event unusable, because the presentation is unknown; a missing
    one is only flagged (older payloads lack it); a plausible-but-off duration is only
    flagged (flash_ms_off)."""
    if not isinstance(r, dict) or "flash_ms" not in r:
        if isinstance(r, dict):
            a.flag("missing_flash_ms")
        return True, None
    st, t = a.time(r["flash_ms"], field="flash_ms", floor=0)
    if st in (G.INVALID, G.ABSENT):
        if st == G.ABSENT:
            a.malformed("invalid_flash_ms")
        return False, None
    if not FLASH_TOL[0] <= t <= FLASH_TOL[1]:
        a.flag("flash_ms_off")
    return True, t


@G.safe
def score(item, response):
    """response: {"events": [{"answer": "up"|"right"|"down"|"left"|null, "rt": ms from the
    end of the flash, "flash_ms": observed flash duration}], "interruptions": n} (a bare
    list is also accepted, without the metadata), in event order.
    The correct answer is the target T's orientation (the generated stimulus itself is the
    key). Each event is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 4000 ms answer window + 50 ms timer tolerance) or timely; an
    event is correct only when a TIMELY answer equals the target (an anticipatory, late or
    malformed answer never is, nor is an event whose flash_ms is malformed). No answer =
    omission, counted as an error. Chance is 25 %.
    hit = accuracy >= 0.50 over the 16 flashes (twice chance).
    Metrics: accuracy overall, per spacing, per eccentricity and per spacing x eccentricity
    cell, the crowding effect (wide minus narrow accuracy), omissions, median correct RT,
    observed flash duration (median), every event's status in events."""
    a = G.Audit(CEILING_MS)
    evs = item["events"]
    is_dict = isinstance(response, dict)
    if not (is_dict or isinstance(response, list)):
        return a.junk(len(evs))
    raw = response.get("events") if is_dict else response
    rows, flashes = [], []
    for k, (e, r) in enumerate(zip(evs, a.entries(raw, len(evs)))):
        status, ans, rt = a.keyed(r, ORIENTS, key="answer", window=WINDOW_MS, slack=RT_SLACK_MS)
        usable, fl = _flash(a, r)
        if fl is not None:
            flashes.append(fl)
        ok = status == G.TIMELY and ans == e["target"] and usable
        rows.append({"i": k, "e": e, "status": status, "ok": ok, "rt": rt if ok else None})
    correct = sum(r["ok"] for r in rows)

    def acc(pred):
        sel = [r["ok"] for r in rows if pred(r["e"])]
        return round(sum(sel) / len(sel), 3) if sel else None

    cells = {f"{s}_{c}": acc(lambda e, s=s, c=c: e["spacing"] == s and e["ecc"] == c)
             for s in SPACING for c in ECC}
    a_n, a_w = acc(lambda e: e["spacing"] == "narrow"), acc(lambda e: e["spacing"] == "wide")
    rts = [r["rt"] for r in rows if r["ok"]]
    meta = response if is_dict else {}
    inter = a.opt_int(meta, "interruptions", required=is_dict)
    total = correct / len(rows) if rows else 0.0
    return a.finish(bool(rows) and total >= 0.5, len(rows) - correct, {
        "accuracy": round(total, 3),
        "accuracy_narrow": a_n, "accuracy_wide": a_w,
        "accuracy_near": acc(lambda e: e["ecc"] == "near"),
        "accuracy_far": acc(lambda e: e["ecc"] == "far"),
        "accuracy_by_cell": cells,
        "crowding_effect": round(a_w - a_n, 3) if a_n is not None and a_w is not None else None,
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "rt_correct_median": G.median(rts), "rt_n": len(rts),
        "flash_ms_median": G.median(flashes),
        "interruptions": inter,
        "events": [{"i": r["i"], "spacing": r["e"]["spacing"], "ecc": r["e"]["ecc"], "status": r["status"],
                    "correct": r["ok"], "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    turn = {"up": "down", "down": "up", "left": "right", "right": "left"}
    return {"events": [{"answer": e["target"] if correct else turn[e["target"]], "rt": 900, "flash_ms": FLASH_MS}
                       for e in item["events"]], "interruptions": 0}
