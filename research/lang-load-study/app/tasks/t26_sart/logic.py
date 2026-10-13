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

DIGITS = list(range(1, 10))
REPEATS = 5
NOGO_DIGIT = 3
SIZES = [70, 90, 110, 130, 150]
SHOW_MS = 250
MASK_MS = 900
CYCLE_MS = SHOW_MS + MASK_MS
BINS = 3
ANTICIPATION_MS = 100


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


def _events(response):
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def _rt(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if 0 <= v < CYCLE_MS + 50 else None


def _stats(xs):
    if not xs:
        return None, None, None
    xs = sorted(xs)
    m = len(xs) // 2
    med = xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else None
    return round(med, 1), round(mean, 1), (round(sd, 1) if sd is not None else None)


def score(item, response):
    """response: {"events": [{"rt": ms from digit onset of the FIRST press in that digit's
    1150 ms window, or null; "extra": further presses}], "interruptions": n} (a bare list
    is also accepted), one entry per digit in order. Only the response key/button counts.
    Go digit (not 3): press = hit, no press = omission. Digit 3: press = commission.
    Presses < 100 ms are anticipations: they count as presses but are left out of RTs.
    errors = omissions + commissions.
    hit = go hit rate >= 0.80 AND at least 2 of the 5 threes withheld (commission rate
    <= 0.60; SART commission rates are typically high, so this only rejects ignoring the rule).
    Metrics: commission/omission rates, go RT median/mean/SD and coefficient of variation,
    mean go RT in the 4 go digits before each 3 (pre-no-go speeding), and per third of the
    block (time bins): omission rate, commissions, mean go RT."""
    try:
        digits = item["digits"]
        resp = _events(response)
        rows = []
        for k, d in enumerate(digits):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            rt = _rt(r.get("rt"))
            rows.append({"go": d["digit"] != NOGO_DIGIT, "rt": rt, "pressed": rt is not None})
        go = [r for r in rows if r["go"]]
        nogo = [r for r in rows if not r["go"]]
        hits = sum(r["pressed"] for r in go)
        comm = sum(r["pressed"] for r in nogo)
        omis = len(go) - hits
        good_rt = lambda rs: [r["rt"] for r in rs if r["go"] and r["pressed"] and r["rt"] >= ANTICIPATION_MS]
        med, mean, sd = _stats(good_rt(rows))
        pre = []
        for k, r in enumerate(rows):
            if not r["go"]:
                pre += good_rt(rows[max(0, k - 4):k])
        bins = []
        size = math.ceil(len(rows) / BINS)
        for b in range(BINS):
            part = rows[b * size:(b + 1) * size]
            g = [r for r in part if r["go"]]
            bins.append({"go_omission_rate": round(sum(not r["pressed"] for r in g) / len(g), 3) if g else None,
                         "commissions": sum(r["pressed"] for r in part if not r["go"]),
                         "nogo_n": sum(1 for r in part if not r["go"]),
                         "go_rt_mean": _stats(good_rt(part))[1]})
        extra = sum(r["extra"] for r in resp if isinstance(r, dict) and isinstance(r.get("extra"), int)
                    and not isinstance(r.get("extra"), bool) and r["extra"] > 0)
        hit = hits / len(go) >= 0.8 and (len(nogo) - comm) >= 2
        inter = response.get("interruptions") if isinstance(response, dict) else None
        return {"hit": bool(hit), "errors": omis + comm,
                "metrics": {"go_omissions": omis, "go_omission_rate": round(omis / len(go), 3),
                            "nogo_commissions": comm, "nogo_commission_rate": round(comm / len(nogo), 3),
                            "go_rt_median": med, "go_rt_mean": mean, "go_rt_sd": sd,
                            "go_rt_cv": round(sd / mean, 3) if sd is not None and mean else None,
                            "go_rt_n": len(good_rt(rows)),
                            "pre_nogo_rt_mean": _stats(pre)[1],
                            "time_bins": bins,
                            "anticipations": sum(1 for r in rows if r["pressed"] and r["rt"] < ANTICIPATION_MS),
                            "extra_presses": extra,
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    ev = []
    for d in item["digits"]:
        go = d["digit"] != NOGO_DIGIT
        press = go if correct else not go
        ev.append({"rt": 380 if press else None, "extra": 0})
    return {"events": ev, "interruptions": 0}
