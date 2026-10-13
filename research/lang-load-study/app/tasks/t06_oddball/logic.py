"""Visual oddball (card 06): a stream of symbols, one per second (300 ms on, 700 ms blank).
Press Space (or the on-screen button) only for the rare target symbol (a square) and
ignore the frequent standard (a circle of the same colour and area).
One trial is a stream of 25 events with exactly 5 targets (20%, predeclared). Targets
never occur in the first 3 events and are separated by at least 2 standards, with
irregular gaps, so they are not trivially predictable. Pairs (k, k+1) have the same
number of targets and constraints; only the target positions differ."""
from statistics import NormalDist

from app.tasks import _guard as G

TIMING = "window"
N_EVENTS, N_TARGETS = 25, 5
ON_MS, SOA_MS = 300, 1000
MIN_RT, MAX_RT = 100, 1100      # a press counts for the event whose onset was 100..1100 ms before
WINDOW_MS = MAX_RT              # view.js press(): rt >= it.min_rt && rt < it.max_rt (100..1100 ms)
LATE_FLAG_MS = 50               # |observed - intended onset| beyond this is flagged (timing_flags)
CEILING_MS = G.trial_ceiling(__file__)


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


def dprime(hits, n_signal, fas, n_noise):
    """d' with the (count + 0.5) / (n + 1) correction for both rates."""
    if not n_signal or not n_noise:
        return None
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_signal + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def _drift(a, r):
    """The event's presentation drift "late" (observed minus intended onset, ms).
    Returns (usable, flagged). Small negatives are legal. Missing, null, non-finite or
    absurd (more than one SOA either way) -> the event is invalid: its onset, and so its
    press window, is unknown. |late| > 50 ms is flagged (late_onset, timing_flags)."""
    v = r.get("late", G.MISSING)
    if v is G.MISSING:
        a.malformed("missing_late")
        return False, False
    if not G.is_num(v) or abs(v) > SOA_MS:
        a.malformed("invalid_late")
        return False, False
    if abs(v) > LATE_FLAG_MS:
        a.flag("late_onset")
        return True, True
    return True, False


def _event(a, r, min_rt):
    """Status and rt of one event. rt below the press window (< 100 ms) cannot come from
    the browser (such a press is assigned to the previous event), so it is invalid; above
    the window it is late; both are never a hit and never a correct rejection."""
    if not isinstance(r, dict):
        return a.press(r) + (False,)
    usable, flagged = _drift(a, r)
    rt = r.get("rt", G.MISSING)
    if usable and G.is_num(rt) and 0 <= rt < min_rt:
        a.malformed("rt_below_window")
        usable = False
    if not usable:
        return a.record(G.INVALID), None, flagged
    status, t = a.press(r, window=WINDOW_MS, floor=min_rt)
    return status, t, flagged


@G.safe
def score(item, response):
    """response: {"events": [{"rt": ms|null, "late": ms}], "extra": n}. rt is the first press
    within 100-1100 ms after that event's observed onset (null = no press); "late" is the
    observed minus intended onset; "extra" counts presses not assigned to any event.
    Target events come from item["events"] == item["target"].
    Each event is classified (app/tasks/_guard.py): absent (rt null), invalid (malformed,
    impossible, below the 100 ms press window, or a missing / non-finite / absurd "late"
    drift), late (beyond the 1100 ms window) or timely.
    Target: hit = a TIMELY press; absent = miss. Standard: correct rejection = absent only;
    a timely press is a false alarm. Invalid and late entries are errors, never a hit or a
    correct rejection. hit = hit rate >= 0.8 (4 of 5 targets) and at most 2 false alarms,
    where every standard that is not a correct rejection (a press, or an invalid / late
    entry) counts against those 2.
    Timing flag: |late| > 50 ms (counted in timing_flags)."""
    a = G.Audit(CEILING_MS)
    syms = item["events"]
    n = len(syms)
    if not isinstance(response, dict):
        return a.junk(n)
    min_rt = item.get("min_rt", MIN_RT)
    rows = []
    for k, (sym, r) in enumerate(zip(syms, a.entries(response.get("events"), n))):
        status, rt, flagged = _event(a, r, min_rt)
        rows.append({"k": k, "target": sym == item["target"], "status": status,
                     "pressed": status == G.TIMELY, "rt": rt if status == G.TIMELY else None, "flag": flagged})
    tg = [r for r in rows if r["target"]]
    st = [r for r in rows if not r["target"]]
    hits = sum(r["pressed"] for r in tg)
    fas = sum(r["pressed"] for r in st)
    crs = sum(r["status"] == G.ABSENT for r in st)
    half = n // 2

    def med(rs):
        return G.median([r["rt"] for r in rs if r["target"] and r["pressed"]])

    hit_rate = hits / len(tg) if tg else 0.0
    extra = a.opt_int(response, "extra")
    # "at most 2 false alarms": a standard that is not a correct rejection (a press, or an
    # invalid / late entry) counts against the 2 allowed, so malformed standards never pass.
    return a.finish(bool(tg) and hit_rate >= 0.8 and len(st) - crs <= 2,
                    (len(tg) - hits) + (len(st) - crs), {
        "hits": hits, "misses": len(tg) - hits, "false_alarms": fas,
        "correct_rejections": crs,
        "hit_rate": round(hit_rate, 3), "fa_rate": G.rate(fas, len(st)),
        "dprime": dprime(hits, len(tg), fas, len(st)),
        "median_hit_rt": med(rows),
        "median_hit_rt_first_half": med(rows[:half]), "median_hit_rt_second_half": med(rows[half:]),
        "omissions_first_half": sum(r["target"] and r["status"] == G.ABSENT for r in rows[:half]),
        "omissions_second_half": sum(r["target"] and r["status"] == G.ABSENT for r in rows[half:]),
        "extra_presses": extra or 0,
        "timing_flags": sum(r["flag"] for r in rows), "n_events": n,
        "invalid_entries": sum(r["status"] == G.INVALID for r in rows),
        "late_entries": sum(r["status"] == G.LATE for r in rows)})


def example_response(item, correct=True):
    out = []
    for sym in item["events"]:
        is_t = sym == item["target"]
        press = is_t if correct else not is_t
        out.append({"rt": 420 if press else None, "late": 3})
    return {"events": out, "extra": 0}
