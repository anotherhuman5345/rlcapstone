"""Visual oddball (card 06): a stream of symbols, one per second (300 ms on, 700 ms blank).
Press Space (or the on-screen button) only for the rare target symbol (a square) and
ignore the frequent standard (a circle of the same colour and area).
One trial is a stream of 25 events with exactly 5 targets (20%, predeclared). Targets
never occur in the first 3 events and are separated by at least 2 standards, with
irregular gaps, so they are not trivially predictable. Pairs (k, k+1) have the same
number of targets and constraints; only the target positions differ."""
import statistics
from statistics import NormalDist

N_EVENTS, N_TARGETS = 25, 5
ON_MS, SOA_MS = 300, 1000
MIN_RT, MAX_RT = 100, 1100      # a press counts for the event whose onset was 100..1100 ms before


def _positions(rng):
    while True:
        pos = sorted(rng.sample(range(3, N_EVENTS), N_TARGETS))
        gaps = [b - a for a, b in zip(pos, pos[1:])]
        if min(gaps) >= 3 and len(set(gaps)) >= 3:
            return pos


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        pos = set(_positions(rng))
        items.append({"on_ms": ON_MS, "soa_ms": SOA_MS, "min_rt": MIN_RT, "max_rt": MAX_RT,
                      "target": "square", "standard": "circle", "colour": "#2B6CB0",
                      "events": ["square" if i in pos else "circle" for i in range(N_EVENTS)]})
    return items


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and x == x else None


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def score(item, response):
    """response: {"events": [{"rt": ms|null, "late": ms}], "extra": n}. rt is the first press
    within 100-1100 ms after that event's observed onset (null = no press); "late" is the
    observed minus intended onset; "extra" counts presses not assigned to any event.
    Target events come from item["events"] == item["target"]. hit/miss/false alarm/correct
    rejection per event. hit = hit rate >= 0.8 (4 of 5 targets) and at most 2 false alarms.
    Timing flag: |late| > 50 ms."""
    resp = response if isinstance(response, dict) else {}
    evs = resp.get("events") if isinstance(resp.get("events"), list) else []
    rows = []
    n = len(item["events"])
    for k, sym in enumerate(item["events"]):
        r = evs[k] if k < len(evs) and isinstance(evs[k], dict) else {}
        rt = _num(r.get("rt"))
        pressed = rt is not None and item["min_rt"] <= rt < item["max_rt"]
        late = _num(r.get("late"))
        rows.append({"k": k, "target": sym == item["target"], "pressed": pressed, "rt": rt if pressed else None,
                     "flag": late is not None and abs(late) > 50})
    tg = [r for r in rows if r["target"]]
    st = [r for r in rows if not r["target"]]
    hits = sum(r["pressed"] for r in tg)
    fas = sum(r["pressed"] for r in st)
    half = n // 2

    def med(rs):
        v = [r["rt"] for r in rs if r["target"] and r["pressed"]]
        return round(statistics.median(v), 1) if v else None

    hit_rate = hits / len(tg) if tg else 0.0
    extra = _num(resp.get("extra"))
    return {"hit": bool(tg) and hit_rate >= 0.8 and fas <= 2,
            "errors": (len(tg) - hits) + fas,
            "metrics": {"hits": hits, "misses": len(tg) - hits, "false_alarms": fas,
                        "correct_rejections": len(st) - fas,
                        "hit_rate": round(hit_rate, 3), "fa_rate": round(fas / len(st), 3) if st else None,
                        "dprime": dprime(hits, len(tg), fas, len(st)),
                        "median_hit_rt": med(rows),
                        "median_hit_rt_first_half": med(rows[:half]), "median_hit_rt_second_half": med(rows[half:]),
                        "omissions_first_half": sum(r["target"] and not r["pressed"] for r in rows[:half]),
                        "omissions_second_half": sum(r["target"] and not r["pressed"] for r in rows[half:]),
                        "extra_presses": int(extra) if extra is not None else 0,
                        "timing_flags": sum(r["flag"] for r in rows), "n_events": n}}


def example_response(item, correct=True):
    out = []
    for sym in item["events"]:
        is_t = sym == item["target"]
        press = is_t if correct else not is_t
        out.append({"rt": 420 if press else None, "late": 3})
    return {"events": out, "extra": 0}
