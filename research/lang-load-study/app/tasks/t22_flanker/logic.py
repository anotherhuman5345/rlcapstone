"""Flanker (card 22): report the direction of the MIDDLE arrow, ignoring the four
around it. One trial is a short block of 16 displays, half congruent (>>>>>)
and half incongruent (>><>>), in shuffled order. Pairs of items (k, k+1) have the
same structure, so the L1 and L2 versions of a pair are equally hard."""

from app.tasks import _guard as G

TIMING = "window"
BLOCK = 16
WINDOW_MS = 1500        # view.js: each display waits at most 1500 ms for a key
CEILING_MS = G.trial_ceiling(__file__)


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        displays = []
        for c in range(BLOCK):
            mid = rng.choice(["<", ">"])
            congruent = c % 2 == 0
            flank = mid if congruent else {"<": ">", ">": "<"}[mid]
            displays.append({"text": flank * 2 + mid + flank * 2, "answer": "left" if mid == "<" else "right",
                             "congruent": congruent})
        rng.shuffle(displays)
        items.append({"displays": displays})
    return items


def _oracle(d):
    """Independent answer key: the direction of the MIDDLE arrow of the displayed string,
    and congruency = every flanker points the same way as the middle arrow."""
    text = d["text"]
    mid = text[len(text) // 2]
    return ("left" if mid == "<" else "right"), all(c == mid for c in text)


@G.safe
def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms}] in display order.
    The answer key and congruency are recomputed from each display's arrow string.
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 1500 ms response window) or timely; only a TIMELY key equal to
    the middle arrow is correct (an anticipatory, late or malformed press never is).
    hit = accuracy >= 0.75 over the 16 displays (omissions and invalid entries are errors).
    Metrics: accuracy, per condition (congruent / incongruent) accuracy, error rate,
    mean and median correct RT and valid-RT count, the flanker RT and error costs,
    omissions, and every display's status in metrics["events"]."""
    a = G.Audit(CEILING_MS)
    displays = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(displays))
    rows = []
    for k, (d, r) in enumerate(zip(displays, a.entries(response, len(displays)))):
        ans, cong = _oracle(d)
        status, key, rt = a.keyed(r, ("left", "right"), window=WINDOW_MS)
        ok = status == G.TIMELY and key == ans
        rows.append({"i": k, "congruent": cong, "status": status, "key": key, "rt": rt if ok else None, "ok": ok})
    n = len(rows)
    n_ok = sum(r["ok"] for r in rows)
    acc = n_ok / n if n else 0.0
    cond = {}
    for name, c in (("congruent", True), ("incongruent", False)):
        sel = [r for r in rows if r["congruent"] == c]
        rts = [r["rt"] for r in sel if r["ok"]]
        cond[name] = {"n": len(sel), "correct": sum(r["ok"] for r in sel),
                      "accuracy": G.rate(sum(r["ok"] for r in sel), len(sel)),
                      "error_rate": G.rate(len(sel) - sum(r["ok"] for r in sel), len(sel)),
                      "omissions": sum(1 for r in sel if r["status"] == G.ABSENT),
                      "rt_mean": G.mean(rts), "rt_median": G.median(rts), "rt_n": len(rts)}
    c, i = cond["congruent"], cond["incongruent"]
    return a.finish(acc >= 0.75, n - n_ok, {
        "accuracy": round(acc, 3),
        "rt_congruent": c["rt_mean"], "rt_incongruent": i["rt_mean"],
        "flanker_cost_ms": round(i["rt_mean"] - c["rt_mean"], 1) if c["rt_mean"] is not None and i["rt_mean"] is not None else None,
        "median_rt_congruent": c["rt_median"], "median_rt_incongruent": i["rt_median"],
        "error_rate_congruent": c["error_rate"], "error_rate_incongruent": i["error_rate"],
        "flanker_error_cost": round(i["error_rate"] - c["error_rate"], 3) if c["error_rate"] is not None and i["error_rate"] is not None else None,
        "by_condition": cond,
        "omissions": sum(1 for r in rows if r["status"] == G.ABSENT),
        "events": [{"i": r["i"], "congruent": r["congruent"], "status": r["status"], "correct": r["ok"], "rt": r["rt"]}
                   for r in rows]})


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    return [{"key": d["answer"] if correct else flip[d["answer"]], "rt": 500 + 40 * (not d["congruent"])}
            for d in item["displays"]]
