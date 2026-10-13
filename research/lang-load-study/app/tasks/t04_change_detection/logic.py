"""Change detection (card 04): study an array of coloured squares (500 ms), wait through a
blank (900 ms), then see the array again and say whether one square changed colour.
One trial is a short block of 12 events: set sizes 4/6/8 x changed/unchanged x 2, shuffled.
Unchanged test arrays are identical copies of the study array; on changed events exactly
one square takes a colour not used in the study array and nothing moves.
Pairs (k, k+1) share the order of set sizes and change; only positions/colours differ."""
from statistics import NormalDist

from app.tasks import _guard as G

TIMING = "window"

W, H, SIZE = 600, 400, 44
COLS, ROWS = 6, 4
# Nine well separated colours (hue and lightness differ; reviewed for the light grey background).
PALETTE = ["#D62728", "#1F77B4", "#2CA02C", "#F2D21B", "#8E44AD", "#FF7F0E", "#222222", "#FFFFFF", "#17BECF"]
SET_SIZES = (4, 6, 8)
REPEATS = 2
STUDY_MS, BLANK_MS, LIMIT_MS = 500, 900, 3000
WINDOW_MS = LIMIT_MS    # view.js: answer(it.limit_ms), item limit_ms = 3000
RT_SLACK_MS = 50        # timer tolerance (the old scorer already allowed limit + 50)
STUDY_TOL = (STUDY_MS / 2, STUDY_MS * 2)   # observed study duration outside -> study_ms_off flag
CEILING_MS = G.trial_ceiling(__file__)


def _event(rng, n, change):
    cw, ch = W / COLS, H / ROWS
    slots = rng.sample(range(COLS * ROWS), n)
    colours = rng.sample(PALETTE, n)
    study = []
    for s, c in zip(slots, colours):
        cx, cy = cw * (s % COLS) + cw / 2, ch * (s // COLS) + ch / 2
        study.append({"x": round(cx + rng.uniform(-18, 18)), "y": round(cy + rng.uniform(-18, 18)), "c": c})
    test = [dict(o) for o in study]
    if change:
        unused = [c for c in PALETTE if c not in colours]
        test[rng.randrange(n)]["c"] = rng.choice(unused)
    return {"n": n, "study": study, "test": test}


def generate(rng, n, save_image):
    items, order = [], None
    for k in range(n):
        if k % 2 == 0:
            order = [(s, c) for s in SET_SIZES for c in (True, False)] * REPEATS
            rng.shuffle(order)
        items.append({"w": W, "h": H, "size": SIZE, "study_ms": STUDY_MS, "blank_ms": BLANK_MS,
                      "limit_ms": LIMIT_MS, "events": [_event(rng, s, c) for s, c in order]})
    return items


def _changed(ev):
    """Oracle: compare the two arrays square by square (positions and colours)."""
    return any(a["c"] != b["c"] or a["x"] != b["x"] or a["y"] != b["y"] for a, b in zip(ev["study"], ev["test"]))


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def _study(a, r):
    """study_ms_observed of one event (view.js frame-timed study array duration).
    Returns (usable, value): a malformed value (wrong type, non-finite, negative, impossible)
    makes the event unusable (presentation unknown); a missing one is only flagged
    (older payloads lack it); a plausible-but-off duration is only flagged."""
    if not isinstance(r, dict) or "study_ms_observed" not in r:
        if isinstance(r, dict):
            a.flag("missing_study_ms_observed")
        return True, None
    st, t = a.time(r["study_ms_observed"], field="study_ms_observed", floor=0)
    if st == G.INVALID or st == G.ABSENT:
        if st == G.ABSENT:
            a.malformed("invalid_study_ms_observed")
        return False, None
    if not STUDY_TOL[0] <= t <= STUDY_TOL[1]:
        a.flag("study_ms_off")
    return True, t


@G.safe
def score(item, response):
    """response: [{"key": "same"|"different"|null, "rt": ms, "study_ms_observed": ms}] in
    event order. Change is recomputed by comparing the study and test arrays.
    Each event is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 3000 ms response window + 50 ms timer tolerance) or timely.
    Correct = a TIMELY "different" on changed events, a TIMELY "same" on unchanged ones;
    omissions, anticipatory, late and malformed entries (also a malformed
    study_ms_observed) are errors and never count as hits or correct rejections.
    Metrics: hits/misses/false alarms/correct rejections (timely answers only), d'
    (corrected), accuracy and Cowan's K = N * (hit rate - FA rate) per set size, median
    correct decision RT, event statuses in events.
    hit = accuracy >= 0.70 (chance is 0.5; set size 8 is hard by design)."""
    a = G.Audit(CEILING_MS)
    evs = item["events"]
    if not isinstance(response, list):
        return a.junk(len(evs))
    rows, studies = [], []
    for k, (ev, r) in enumerate(zip(evs, a.entries(response, len(evs)))):
        status, key, rt = a.keyed(r, ("same", "different"), window=WINDOW_MS, slack=RT_SLACK_MS)
        usable, st_ms = _study(a, r)
        if st_ms is not None:
            studies.append(st_ms)
        ch = _changed(ev)
        made = key if status == G.TIMELY and usable else None
        ok = made == ("different" if ch else "same")
        rows.append({"i": k, "n": ev["n"], "changed": ch, "status": status, "made": made, "ok": ok,
                     "rt": rt if ok else None})
    n = len(rows)
    sig = [r for r in rows if r["changed"]]
    noise = [r for r in rows if not r["changed"]]
    hits = sum(r["made"] == "different" for r in sig)
    fas = sum(r["made"] == "different" for r in noise)
    acc = sum(r["ok"] for r in rows) / n if n else 0.0
    acc_by, k_by = {}, {}
    for s in SET_SIZES:
        rs = [r for r in rows if r["n"] == s]
        if not rs:
            continue
        acc_by[str(s)] = round(sum(r["ok"] for r in rs) / len(rs), 3)
        ss, sn = [r for r in rs if r["changed"]], [r for r in rs if not r["changed"]]
        if ss and sn:
            hr = sum(r["made"] == "different" for r in ss) / len(ss)
            fr = sum(r["made"] == "different" for r in sn) / len(sn)
            k_by[str(s)] = round(s * (hr - fr), 2)
    rts = [r["rt"] for r in rows if r["ok"]]
    return a.finish(n > 0 and acc >= 0.70, n - sum(r["ok"] for r in rows), {
        "accuracy": round(acc, 3), "hits": hits, "misses": len(sig) - hits,
        "false_alarms": fas, "correct_rejections": sum(r["made"] == "same" for r in noise),
        "dprime": dprime(hits, len(sig), fas, len(noise)),
        "accuracy_by_size": acc_by, "cowan_k_by_size": k_by,
        "omissions": sum(r["status"] == G.ABSENT for r in rows),
        "median_rt_correct": G.median(rts),
        "n_valid_rt": len(rts),
        "study_ms_observed_median": G.median(studies),
        "events": [{"i": r["i"], "set_size": r["n"], "changed": r["changed"], "status": r["status"],
                    "correct": r["ok"], "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    out = []
    for ev in item["events"]:
        ch = _changed(ev) if correct else not _changed(ev)
        out.append({"key": "different" if ch else "same", "rt": 800, "study_ms_observed": STUDY_MS})
    return out
