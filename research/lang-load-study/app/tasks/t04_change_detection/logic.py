"""Change detection (card 04): study an array of coloured squares (500 ms), wait through a
blank (900 ms), then see the array again and say whether one square changed colour.
One trial is a short block of 12 events: set sizes 4/6/8 x changed/unchanged x 2, shuffled.
Unchanged test arrays are identical copies of the study array; on changed events exactly
one square takes a colour not used in the study array and nothing moves.
Pairs (k, k+1) share the order of set sizes and change; only positions/colours differ."""
import statistics
from statistics import NormalDist

W, H, SIZE = 600, 400, 44
COLS, ROWS = 6, 4
# Nine well separated colours (hue and lightness differ; reviewed for the light grey background).
PALETTE = ["#D62728", "#1F77B4", "#2CA02C", "#F2D21B", "#8E44AD", "#FF7F0E", "#222222", "#FFFFFF", "#17BECF"]
SET_SIZES = (4, 6, 8)
REPEATS = 2
STUDY_MS, BLANK_MS, LIMIT_MS = 500, 900, 3000


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


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and x == x else None


def _changed(ev):
    """Oracle: compare the two arrays square by square (positions and colours)."""
    return any(a["c"] != b["c"] or a["x"] != b["x"] or a["y"] != b["y"] for a, b in zip(ev["study"], ev["test"]))


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def score(item, response):
    """response: [{"key": "same"|"different"|null, "rt": ms}] in event order.
    Correct = "different" on changed events, "same" on unchanged ones; omissions are errors.
    Metrics: hits/misses/false alarms/correct rejections, d' (corrected), accuracy and
    Cowan's K = N * (hit rate - FA rate) per set size, median correct decision RT.
    hit = accuracy >= 0.70 (chance is 0.5; set size 8 is hard by design)."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, ev in enumerate(item["events"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        key = r.get("key") if r.get("key") in ("same", "different") else None
        ch = _changed(ev)
        rt = _num(r.get("rt"))
        rows.append({"n": ev["n"], "changed": ch, "key": key, "ok": key == ("different" if ch else "same"),
                     "rt": rt if rt is not None and 100 <= rt <= LIMIT_MS + 50 else None})
    n = len(rows)
    sig = [r for r in rows if r["changed"]]
    noise = [r for r in rows if not r["changed"]]
    hits = sum(r["key"] == "different" for r in sig)
    fas = sum(r["key"] == "different" for r in noise)
    acc = sum(r["ok"] for r in rows) / n if n else 0.0
    acc_by, k_by = {}, {}
    for s in SET_SIZES:
        rs = [r for r in rows if r["n"] == s]
        if not rs:
            continue
        acc_by[str(s)] = round(sum(r["ok"] for r in rs) / len(rs), 3)
        ss, sn = [r for r in rs if r["changed"]], [r for r in rs if not r["changed"]]
        if ss and sn:
            hr = sum(r["key"] == "different" for r in ss) / len(ss)
            fr = sum(r["key"] == "different" for r in sn) / len(sn)
            k_by[str(s)] = round(s * (hr - fr), 2)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"] is not None]
    return {"hit": acc >= 0.70, "errors": n - sum(r["ok"] for r in rows),
            "metrics": {"accuracy": round(acc, 3), "hits": hits, "misses": len(sig) - hits,
                        "false_alarms": fas, "correct_rejections": len(noise) - fas,
                        "dprime": dprime(hits, len(sig), fas, len(noise)),
                        "accuracy_by_size": acc_by, "cowan_k_by_size": k_by,
                        "omissions": sum(r["key"] is None for r in rows),
                        "median_rt_correct": round(statistics.median(rts), 1) if rts else None,
                        "n_valid_rt": len(rts)}}


def example_response(item, correct=True):
    out = []
    for ev in item["events"]:
        ch = _changed(ev) if correct else not _changed(ev)
        out.append({"key": "different" if ch else "same", "rt": 800})
    return out
