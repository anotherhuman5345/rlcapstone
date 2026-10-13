"""Stroop (card 21): a color word is shown in colored ink; report the INK color and
ignore the word. One trial is a block of 24 displays with four colors (red, blue, green,
yellow): 12 congruent (word = ink) and 12 incongruent (word names another color).
Every ink appears 6 times (3 congruent, 3 incongruent) and each incongruent ink is paired
once with each of the three other words, so every block has the same composition; the
two items of a pair differ only in order. Words are indices into text["words"] (the
trial's language); inks are language-neutral palette indices."""

from app.tasks import _guard as G

TIMING = "window"
BLOCK = 24
N_COLORS = 4
WINDOW_MS = 2000        # view.js: out.push(await answer(2000)) - each word waits at most 2000 ms
CEILING_MS = G.trial_ceiling(__file__)
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


def _oracle(d):
    """Independent answer key: the ink index is the correct key; congruency = word == ink
    (recomputed from the stimulus, not the generator's stored "congruent" label)."""
    return d["ink"], d["word"] == d["ink"]


def _cond(sel):
    rts = [r["rt"] for r in sel if r["ok"]]
    k = sum(r["ok"] for r in sel)
    return {"n": len(sel), "correct": k, "accuracy": G.rate(k, len(sel)),
            "error_rate": G.rate(len(sel) - k, len(sel)),
            "omissions": sum(1 for r in sel if r["status"] == G.ABSENT),
            "rt_mean": G.mean(rts), "rt_median": G.median(rts), "rt_n": len(rts)}


@G.safe
def score(item, response):
    """response: [{"key": 0-3 (palette index of the chosen ink) | null, "rt": ms}] in
    display order. The correct key is the display's ink (oracle: ink index, never the word);
    congruency is recomputed as word == ink.
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 2000 ms response window) or timely; only a TIMELY key equal to
    the ink is correct (an anticipatory, late or malformed answer never is).
    hit = accuracy >= 0.75 over all 24 displays (omissions and invalid entries are errors).
    Metrics: median correct RT per condition, Stroop RT cost (incongruent - congruent),
    error rates per condition and their difference, omissions, per-condition measures in
    by_condition and every display's status in metrics["events"]."""
    a = G.Audit(CEILING_MS)
    displays = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(displays))
    rows = []
    for k, (d, r) in enumerate(zip(displays, a.entries(response, len(displays)))):
        ans, cong = _oracle(d)
        status, key, rt = a.keyed(r, range(N_COLORS), window=WINDOW_MS)
        ok = status == G.TIMELY and key == ans
        rows.append({"i": k, "congruent": cong, "status": status, "rt": rt if ok else None, "ok": ok})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)
    acc = n_ok / n if n else 0.0
    c = _cond([r for r in rows if r["congruent"]])
    i = _cond([r for r in rows if not r["congruent"]])
    return a.finish(n > 0 and acc >= 0.75, n - n_ok, {
        "accuracy": round(acc, 3),
        "median_rt_congruent": c["rt_median"], "median_rt_incongruent": i["rt_median"],
        "stroop_cost_ms": round(i["rt_median"] - c["rt_median"], 1)
        if c["rt_median"] is not None and i["rt_median"] is not None else None,
        "mean_rt_congruent": c["rt_mean"], "mean_rt_incongruent": i["rt_mean"],
        "error_rate_congruent": c["error_rate"], "error_rate_incongruent": i["error_rate"],
        "stroop_error_cost": round(i["error_rate"] - c["error_rate"], 3)
        if c["error_rate"] is not None and i["error_rate"] is not None else None,
        "valid_rt_trials": c["rt_n"] + i["rt_n"],
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "by_condition": {"congruent": c, "incongruent": i},
        "events": [{"i": r["i"], "congruent": r["congruent"], "status": r["status"], "correct": r["ok"],
                    "rt": r["rt"]} for r in rows]})


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        key = d["ink"] if correct else (d["word"] if not d["congruent"] else (d["ink"] + 1) % N_COLORS)
        out.append({"key": key, "rt": 600 + 80 * (not d["congruent"])})
    return out
