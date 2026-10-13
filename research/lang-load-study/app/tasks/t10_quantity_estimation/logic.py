"""Brief quantity estimation (card 10): a cloud of dots flashes for 200 ms and is then
covered by a mask; type how many dots you think there were.
One trial is a block of 9 displays: 10, 20 and 40 dots x 3 stimulus-control variants,
shuffled. Both items of a pair have the same cells; only dot positions and order differ.

Stimulus controls (800 x 500 drawing area, dots drawn inside a centred disc):
  "size"  - every dot has radius 9; field disc radius 140. Total ink and density grow with n.
  "area"  - total dot area is held at that of 20 dots of radius 9 (r = 9*sqrt(20/n));
            field disc radius 140. Ink is constant, so it cannot signal number.
  "field" - dot radius 9, but the disc radius scales as 140*sqrt(n/20), so density
            (dots per unit area) is constant and spread grows with n.
No single variant removes every non-numeric cue; comparing estimates across the three
variants shows how much an estimate follows ink, density or spread."""
import math
import unicodedata

from app.tasks import _guard as G

NUMBERS = [10, 20, 40]
VARIANTS = ["size", "area", "field"]
BASE_R = 9.0
BASE_FIELD = 140.0
GAP = 4.0
FLASH_MS = 200
TIMING = "limit"      # each estimate must be entered within the entry limit (see _guard.py)
LIMIT_MS = 10000      # view.js: ask() ends the entry after item.limit_ms (setTimeout(..., limit))
TIME_SLACK_MS = 1000  # timer tolerance at the limit
CEILING_MS = G.trial_ceiling(__file__)
MAX_ANSWER = 999


def _layout(rng, n, variant):
    r = BASE_R * math.sqrt(20 / n) if variant == "area" else BASE_R
    field = BASE_FIELD * math.sqrt(n / 20) if variant == "field" else BASE_FIELD
    for _attempt in range(200):
        dots = []
        tries = 0
        while len(dots) < n and tries < 20000:
            tries += 1
            ang = rng.random() * 2 * math.pi
            rad = (field - r) * math.sqrt(rng.random())
            x, y = 400 + rad * math.cos(ang), 250 + rad * math.sin(ang)
            if all((x - a) ** 2 + (y - b) ** 2 >= (2 * r + GAP) ** 2 for a, b in dots):
                dots.append((x, y))
        if len(dots) == n:
            return {"n": n, "variant": variant, "r": round(r, 2), "field": round(field, 1),
                    "dots": [[round(x, 1), round(y, 1)] for x, y in dots]}
    raise RuntimeError("could not place dots")


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        displays = [_layout(rng, num, var) for num in NUMBERS for var in VARIANTS]
        rng.shuffle(displays)
        items.append({"displays": displays, "flash_ms": FLASH_MS, "limit_ms": LIMIT_MS})
    return items


def parse_estimate(v):
    """Whole number 0..999 from an int or a string of decimal digits in any script
    (e.g. Arabic-Indic digits); surrounding/inner spaces are ignored. Separators such as
    "," or "." are rejected (in Turkish "1,5" is a decimal), as is anything else. Else None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 0 <= v <= MAX_ANSWER else None
    if isinstance(v, float) and math.isfinite(v) and v == int(v):
        return parse_estimate(int(v))
    if not isinstance(v, str) or len(v) > 12:
        return None
    digits = []
    for ch in v.strip():
        if ch in " \u00a0\u202f":
            continue
        d = unicodedata.decimal(ch, None)
        if d is None:
            return None
        digits.append(str(d))
    if not digits:
        return None
    return parse_estimate(int("".join(digits)))


def _events(response):
    """The per-display list: response["events"] (a bare list is also accepted)."""
    if isinstance(response, list):
        return response
    return response.get("events", G.MISSING)


@G.safe
def score(item, response):
    """response: {"events": [{"estimate": digit string (any script) or int or null, "rt": ms
    from the entry prompt to confirming (or to the 10 s timeout), "confirmed": bool (false =
    the 10 s limit ran out and whatever was typed was sent), "flash_ms": measured flash
    duration}], "interruptions": n} (a bare list is also accepted), in display order (one
    entry per display; extra entries are ignored and flagged, missing ones are omissions).
    The true count is len(display["dots"]) (counted, not trusted from "n").
    An estimate counts only when its rt is a valid time inside the 10 s entry limit
    (finite, >= 100 ms, <= LIMIT_MS + 1 s timer slack, see view.js): a missing,
    non-finite, negative, impossible, anticipatory or late rt makes the display an
    omission (flagged). An unreadable estimate is flagged and is an omission too.
    Per display: absolute error |est - n|, proportional error |est - n| / n, signed bias
    (est - n) / n. Omissions are errors and are left out of the error means.
    errors = displays with proportional error > 0.5 plus omissions.
    hit = at least 8 of 9 displays answered in time and mean proportional error <= 0.35."""
    a = G.Audit(CEILING_MS)
    disps = item["displays"]
    if not isinstance(response, (dict, list)):
        return a.junk(len(disps))
    entries = a.entries(_events(response), len(disps), "events")
    rows = []
    for k, (d, r) in enumerate(zip(disps, entries)):
        true_n = len(d["dots"])
        row = {"n": true_n, "v": d["variant"], "est": None, "rt": None, "status": G.INVALID}
        rows.append(row)
        ev = a.obj(r)
        if ev is None:
            a.record(G.INVALID)
            continue
        raw = ev.get("estimate", G.MISSING)
        if raw is G.MISSING:
            a.malformed("missing_estimate")
            est = None
        elif raw is None:
            est = None
        else:
            est = parse_estimate(raw)
            if est is None:
                a.malformed("invalid_estimate")
        st, rt = a.time(ev.get("rt", G.MISSING), field="rt", window=LIMIT_MS, slack=TIME_SLACK_MS, required=True)
        confirmed = a.opt_bool(ev, "confirmed")
        if confirmed is True and raw is None:
            a.malformed("confirmed_without_estimate")   # OK only works once something is typed
        if confirmed is False and st == G.TIMELY and rt < LIMIT_MS - TIME_SLACK_MS:
            a.flag("unconfirmed_before_limit")          # the view only sends unconfirmed at the limit
        fl = a.duration(ev, "flash_ms", floor=0)
        if fl is not None and not (FLASH_MS / 2 <= fl <= 2 * FLASH_MS):
            a.flag("flash_ms_out_of_range")
        if raw is not G.MISSING and raw is not None and est is None:
            row["status"] = a.record(G.INVALID)
        elif st != G.TIMELY:
            row["status"] = a.record(st if st != G.ABSENT else G.INVALID)
            if est is not None:
                a.flag("estimate_outside_limit")
        elif est is None:
            row["status"] = a.record(G.ABSENT)
            row["rt"] = rt
        else:
            row["status"] = a.record(G.TIMELY)
            row["est"], row["rt"] = est, rt
    for row in rows:
        est, true_n = row["est"], row["n"]
        row["pe"] = abs(est - true_n) / true_n if est is not None else None
        row["bias"] = (est - true_n) / true_n if est is not None else None
        row["ae"] = abs(est - true_n) if est is not None else None
    ans = [r for r in rows if r["est"] is not None]

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 3) if xs else None

    mpe = mean([r["pe"] for r in ans])
    omissions = len(rows) - len(ans)
    hit = len(ans) >= len(rows) - 1 and mpe is not None and mpe <= 0.35
    inter = a.opt_int(response, "interruptions", hi=10000) if isinstance(response, dict) else None
    return a.finish(hit, omissions + sum(1 for r in ans if r["pe"] > 0.5), {
        "mean_abs_error": mean([r["ae"] for r in ans]),
        "mean_prop_error": mpe,
        "signed_bias": mean([r["bias"] for r in ans]),
        "prop_error_by_n": {str(n): mean([r["pe"] for r in ans if r["n"] == n]) for n in NUMBERS},
        "bias_by_n": {str(n): mean([r["bias"] for r in ans if r["n"] == n]) for n in NUMBERS},
        "bias_by_variant": {v: mean([r["bias"] for r in ans if r["v"] == v]) for v in VARIANTS},
        "estimates": [r["est"] for r in rows],
        "omissions": omissions,
        "rt_mean": mean([r["rt"] for r in ans]),
        "interruptions": inter,
        "events": [{"i": k, "n": r["n"], "variant": r["v"], "status": r["status"],
                    "estimate": r["est"], "rt": r["rt"]} for k, r in enumerate(rows)]})


def example_response(item, correct=True):
    return {"events": [{"estimate": (len(d["dots"]) + 1) if correct else str(len(d["dots"]) * 3), "rt": 2500,
                        "confirmed": True, "flash_ms": 200}
                       for d in item["displays"]], "interruptions": 0}
