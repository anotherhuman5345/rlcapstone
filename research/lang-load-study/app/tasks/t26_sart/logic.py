"""Sustained attention to response (card 26): digits 1-9 appear one at a time; press for
every digit except 3. Fixed schedule: digit 250 ms + mask 900 ms = 1150 ms per digit,
and a press never moves the next onset.
One trial is a block of 45 digits: each of 1-9 exactly 5 times (so the no-go digit 3 is
5/45 = 11 %, the stated digit distribution), shuffled with the first digit never a 3 and
no two 3's in a row. Each digit is shown in one of five font sizes (balanced within a
digit as far as possible) so that the shape, not a fixed picture, must be read.
Both items of a pair share these counts and constraints; only the order differs.
Whether a digit is the no-go digit is decided here from the digit itself."""
import math

from app.tasks import _guard as G

TIMING = "window"
DIGITS = list(range(1, 10))
REPEATS = 5
NOGO_DIGIT = 3
SIZES = [70, 90, 110, 130, 150]
SHOW_MS = 250
MASK_MS = 900
CYCLE_MS = SHOW_MS + MASK_MS
BINS = 3
ANTICIPATION_MS = G.ANTICIPATION_MS
WINDOW_MS = CYCLE_MS    # view.js: a press belongs to the digit whose 1150 ms window it falls in
RT_SLACK_MS = 50        # the old scorer's tolerance (rt < 1150 + 50)
LAG_FLAG_MS = 50        # onset lag (observed - scheduled onset) beyond this is flagged
CEILING_MS = G.trial_ceiling(__file__)


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        while True:
            seq = [d for d in DIGITS for _ in range(REPEATS)]
            rng.shuffle(seq)
            if seq[0] != NOGO_DIGIT and all(not (a == b == NOGO_DIGIT) for a, b in zip(seq, seq[1:])):
                break
        sizes = {d: rng.sample(SIZES, len(SIZES)) for d in DIGITS}
        used = {d: 0 for d in DIGITS}
        digits = []
        for d in seq:
            digits.append({"digit": d, "size": sizes[d][used[d] % len(SIZES)]})
            used[d] += 1
        items.append({"digits": digits, "show_ms": SHOW_MS, "mask_ms": MASK_MS})
    return items


def _lag(a, r):
    """The per-digit onset lag (view.js "lag" = observed minus scheduled onset, ms).
    Returns (usable, value). Missing -> flagged only (older payloads lack it). A value that
    is not a finite number or beyond one whole cycle in either direction is absurd: the
    event is invalid (its window is unknown) and can be neither a hit nor a withhold.
    |lag| > 50 ms is flagged (onset_lag)."""
    if "lag" not in r:
        a.flag("missing_lag")
        return True, None
    v = r["lag"]
    if not G.is_num(v) or abs(v) > CYCLE_MS:
        a.malformed("invalid_lag")
        return False, None
    if abs(v) > LAG_FLAG_MS:
        a.flag("onset_lag")
    return True, float(v)


def _stats(xs):
    if not xs:
        return None, None, None
    xs = sorted(xs)
    m = len(xs) // 2
    med = xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else None
    return round(med, 1), round(mean, 1), (round(sd, 1) if sd is not None else None)


@G.safe
def score(item, response):
    """response: {"events": [{"rt": ms from digit onset of the FIRST press in that digit's
    1150 ms window, or null; "extra": further presses; "lag": observed - scheduled onset}],
    "interruptions": n, "max_lag_ms": ms} (a bare list is also accepted, without the
    metadata), one entry per digit in order. Only the response key/button counts.
    Each entry is classified (app/tasks/_guard.py): absent (rt null), invalid (not a finite
    non-negative number, impossible, an absurd onset lag, or the entry is missing),
    anticipatory (< 100 ms), late (beyond the 1150 ms window + 50 ms tolerance) or timely.
    Go digit (not 3): hit = a TIMELY press; absent = omission; anticipatory, late or invalid
    entries are errors, never hits. Digit 3: correct withhold = absent only; any press
    (timely, anticipatory or late) is a commission; an invalid entry is never a withhold.
    errors = go digits not hit + threes not withheld.
    hit = go hit rate >= 0.80 AND at least 2 of the 5 threes withheld (commission rate
    <= 0.60; SART commission rates are typically high, so this only rejects ignoring the rule).
    Metrics: commission/omission rates, go RT median/mean/SD and coefficient of variation,
    mean go RT in the 4 go digits before each 3 (pre-no-go speeding), and per third of the
    block (time bins): omission rate, commissions, mean go RT; anticipations, invalid
    entries, onset lag."""
    a = G.Audit(CEILING_MS)
    digits = item["digits"]
    is_dict = isinstance(response, dict)
    if not (is_dict or isinstance(response, list)):
        return a.junk(len(digits))
    raw = response.get("events") if is_dict else response
    rows, extra, lags = [], 0, []
    for d, r in zip(digits, a.entries(raw, len(digits))):
        go = d["digit"] != NOGO_DIGIT
        usable, lag = _lag(a, r) if isinstance(r, dict) else (True, None)
        if usable:
            status, rt = a.press(r, window=WINDOW_MS, slack=RT_SLACK_MS)
        else:
            status, rt = a.record(G.INVALID), None
        if isinstance(r, dict):
            extra += a.opt_int(r, "extra") or 0
        if lag is not None:
            lags.append(lag)
        rows.append({"go": go, "status": status, "rt": rt if status == G.TIMELY else None,
                     "hit": go and status == G.TIMELY,
                     "comm": (not go) and status in (G.TIMELY, G.ANTICIPATORY, G.LATE),
                     "withheld": (not go) and status == G.ABSENT})
    go = [r for r in rows if r["go"]]
    nogo = [r for r in rows if not r["go"]]
    hits = sum(r["hit"] for r in go)
    comm = sum(r["comm"] for r in nogo)
    cr = sum(r["withheld"] for r in nogo)
    omis = sum(r["status"] == G.ABSENT for r in go)
    good_rt = lambda rs: [r["rt"] for r in rs if r["hit"]]  # noqa: E731
    med, mean, sd = _stats(good_rt(rows))
    pre = []
    for k, r in enumerate(rows):
        if not r["go"]:
            pre += good_rt(rows[max(0, k - 4):k])
    bins = []
    size = math.ceil(len(rows) / BINS) if rows else 1
    for b in range(BINS):
        part = rows[b * size:(b + 1) * size]
        g = [r for r in part if r["go"]]
        bins.append({"go_omission_rate": G.rate(sum(r["status"] == G.ABSENT for r in g), len(g)),
                     "commissions": sum(r["comm"] for r in part),
                     "nogo_n": sum(1 for r in part if not r["go"]),
                     "go_rt_mean": _stats(good_rt(part))[1]})
    hit = bool(go) and hits / len(go) >= 0.8 and cr >= 2
    meta = response if is_dict else {}
    inter = a.opt_int(meta, "interruptions", required=is_dict)
    max_lag = None
    if is_dict:
        if "max_lag_ms" not in meta:
            a.flag("missing_max_lag_ms")
        else:
            st, max_lag = a.time(meta["max_lag_ms"], field="max_lag_ms", floor=0, required=True)
            if st == G.INVALID:
                max_lag = None
            elif lags and abs(max_lag - max(0.0, max(lags))) > 1:
                a.flag("max_lag_mismatch")
            elif max_lag > LAG_FLAG_MS:
                a.flag("onset_lag")
    return a.finish(hit, (len(go) - hits) + (len(nogo) - cr), {
        "go_omissions": omis, "go_omission_rate": G.rate(omis, len(go)),
        "go_hits": hits, "go_hit_rate": G.rate(hits, len(go)),
        "nogo_commissions": comm, "nogo_commission_rate": G.rate(comm, len(nogo)),
        "nogo_correct_withholds": cr,
        "go_rt_median": med, "go_rt_mean": mean, "go_rt_sd": sd,
        "go_rt_cv": round(sd / mean, 3) if sd is not None and mean else None,
        "go_rt_n": len(good_rt(rows)),
        "pre_nogo_rt_mean": _stats(pre)[1],
        "time_bins": bins,
        "anticipations": sum(1 for r in rows if r["status"] == G.ANTICIPATORY),
        "invalid_entries": sum(1 for r in rows if r["status"] == G.INVALID),
        "extra_presses": extra,
        "interruptions": inter,
        "max_lag_ms": max_lag, "lag_max_observed": max(lags) if lags else None})


def example_response(item, correct=True):
    ev = []
    for d in item["digits"]:
        go = d["digit"] != NOGO_DIGIT
        press = go if correct else not go
        ev.append({"rt": 380 if press else None, "extra": 0, "lag": 2})
    return {"events": ev, "interruptions": 0, "max_lag_ms": 2}
