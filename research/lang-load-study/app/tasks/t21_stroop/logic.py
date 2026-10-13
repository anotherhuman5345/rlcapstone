"""Stroop (card 21): a color word is shown in colored ink; report the INK color and
ignore the word. One trial is a block of 24 displays with four colors (red, blue, green,
yellow): 12 congruent (word = ink) and 12 incongruent (word names another color).
Every ink appears 6 times (3 congruent, 3 incongruent) and each incongruent ink is paired
once with each of the three other words, so every block has the same composition; the
two items of a pair differ only in order. Words are indices into text["words"] (the
trial's language); inks are language-neutral palette indices."""

BLOCK = 24
N_COLORS = 4
# red, blue, green, yellow; shown on a dark panel so all four have good contrast.
PALETTE = ["#e8412c", "#3d8bff", "#2fb35a", "#f2d22e"]


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        displays = []
        for ink in range(N_COLORS):
            for _ in range(3):
                displays.append({"word": ink, "ink": ink, "congruent": True})
            for word in range(N_COLORS):
                if word != ink:
                    displays.append({"word": word, "ink": ink, "congruent": False})
        rng.shuffle(displays)
        items.append({"displays": displays, "palette": PALETTE})
    return items


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(float(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2), 1)


def _key(r):
    k = r.get("key") if isinstance(r, dict) else None
    return k if isinstance(k, int) and not isinstance(k, bool) and 0 <= k < N_COLORS else None


def _rt(r):
    rt = r.get("rt") if isinstance(r, dict) else None
    return float(rt) if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None


def score(item, response):
    """response: [{"key": 0-3 (palette index of the chosen ink) | null, "rt": ms}] in
    display order. The correct key is the display's ink (oracle: ink index, never the word).
    hit = accuracy >= 0.75 over all 24 displays (omissions count as errors).
    Metrics: median correct RT per condition, Stroop RT cost (incongruent - congruent),
    error rates per condition and their difference, omissions."""
    try:
        displays = item["displays"]
    except (TypeError, KeyError):
        return {"hit": False, "errors": 0, "metrics": {}}
    resp = response if isinstance(response, list) else []
    rows = []
    for k, d in enumerate(displays):
        r = resp[k] if k < len(resp) else None
        key = _key(r)
        rows.append((d, key, _rt(r), key == d["ink"]))
    n = len(rows)
    n_ok = sum(ok for *_, ok in rows)
    acc = n_ok / n if n else 0.0

    def cond(c):
        sel = [row for row in rows if row[0]["congruent"] == c]
        rts = [rt for d, key, rt, ok in sel if ok and rt]
        err = 1 - sum(ok for *_, ok in sel) / len(sel) if sel else None
        return _median(rts), (round(err, 3) if err is not None else None), len(rts)

    rt_c, err_c, nc = cond(True)
    rt_i, err_i, ni = cond(False)
    return {"hit": n > 0 and acc >= 0.75, "errors": n - n_ok,
            "metrics": {"accuracy": round(acc, 3),
                        "median_rt_congruent": rt_c, "median_rt_incongruent": rt_i,
                        "stroop_cost_ms": round(rt_i - rt_c, 1) if rt_c and rt_i else None,
                        "error_rate_congruent": err_c, "error_rate_incongruent": err_i,
                        "stroop_error_cost": round(err_i - err_c, 3) if err_c is not None and err_i is not None else None,
                        "valid_rt_trials": nc + ni,
                        "omissions": sum(1 for _, key, _, _ in rows if key is None)}}


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        key = d["ink"] if correct else (d["word"] if not d["congruent"] else (d["ink"] + 1) % N_COLORS)
        out.append({"key": key, "rt": 600 + 80 * (not d["congruent"])})
    return out
