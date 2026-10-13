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

NUMBERS = [10, 20, 40]
VARIANTS = ["size", "area", "field"]
BASE_R = 9.0
BASE_FIELD = 140.0
GAP = 4.0
FLASH_MS = 200
LIMIT_MS = 10000
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
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def score(item, response):
    """response: {"events": [{"estimate": int or digit string or null, "rt": ms from the
    entry prompt to confirming}], "interruptions": n} (a bare list is also accepted), in
    display order. The true count is len(display["dots"]) (counted, not trusted from "n").
    Per display: absolute error |est - n|, proportional error |est - n| / n, signed bias
    (est - n) / n. A missing/unreadable estimate is an omission (an error) and is left out
    of the error means. errors = displays with proportional error > 0.5 plus omissions.
    hit = at least 8 of 9 displays answered and mean proportional error <= 0.35."""
    try:
        disps = item["displays"]
        resp = _events(response)
        rows = []
        for k, d in enumerate(disps):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            true_n = len(d["dots"])
            est = parse_estimate(r.get("estimate"))
            rt = r.get("rt") if isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) else None
            rows.append({"n": true_n, "v": d["variant"], "est": est,
                         "pe": abs(est - true_n) / true_n if est is not None else None,
                         "bias": (est - true_n) / true_n if est is not None else None,
                         "ae": abs(est - true_n) if est is not None else None, "rt": rt})
        ans = [r for r in rows if r["est"] is not None]

        def mean(xs):
            xs = [x for x in xs if x is not None]
            return round(sum(xs) / len(xs), 3) if xs else None

        mpe = mean([r["pe"] for r in ans])
        omissions = len(rows) - len(ans)
        hit = len(ans) >= len(rows) - 1 and mpe is not None and mpe <= 0.35
        inter = response.get("interruptions") if isinstance(response, dict) else None
        return {"hit": bool(hit), "errors": omissions + sum(1 for r in ans if r["pe"] > 0.5),
                "metrics": {"mean_abs_error": mean([r["ae"] for r in ans]),
                            "mean_prop_error": mpe,
                            "signed_bias": mean([r["bias"] for r in ans]),
                            "prop_error_by_n": {str(n): mean([r["pe"] for r in ans if r["n"] == n]) for n in NUMBERS},
                            "bias_by_n": {str(n): mean([r["bias"] for r in ans if r["n"] == n]) for n in NUMBERS},
                            "bias_by_variant": {v: mean([r["bias"] for r in ans if r["v"] == v]) for v in VARIANTS},
                            "estimates": [r["est"] for r in rows],
                            "omissions": omissions,
                            "rt_mean": mean([r["rt"] for r in ans]),
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    return {"events": [{"estimate": (len(d["dots"]) + 1) if correct else str(len(d["dots"]) * 3), "rt": 2500}
                       for d in item["displays"]], "interruptions": 0}
