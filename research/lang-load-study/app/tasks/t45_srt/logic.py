"""Serial reaction-time learning (card 45), adapted to one short trial.

Four positions; press the key/box of the highlighted one. One trial = 96 targets in
three segments: random (24) - sequence (48 = a hidden 12-element pattern x 4) - random
(24). The pattern is a second-order-conditional sequence: an Euler circuit of the
complete directed graph on 4 positions, so every position appears 3 times and every
ordered transition (no repeats) exactly once per cycle. Random segments are built from
OTHER such circuits, so position frequencies and first-order transitions are matched to
the pattern segment; only the higher-order structure differs. The two items of a pair use
different patterns with the same structure.
Do not read a pattern effect as implicit learning without a separate awareness measure.
"""

from app.tasks import _guard as G

TIMING = "window"
WINDOW_MS = 2000        # view.js: const a = await answer(2000) - 2 s limit per target
CEILING_MS = G.trial_ceiling(__file__)
N_POS = 4
SEG = [("random", 2), ("pattern", 4), ("random", 2)]  # (kind, number of 12-element cycles)


def _euler(rng):
    """Random Euler circuit of the complete digraph on 4 nodes (12 edges), as 12 nodes."""
    while True:
        unused = {(a, b) for a in range(N_POS) for b in range(N_POS) if a != b}
        start = rng.randrange(N_POS)
        seq, cur = [start], start
        while unused:
            opts = [e for e in unused if e[0] == cur]
            if not opts:
                break
            e = rng.choice(sorted(opts))
            unused.discard(e)
            cur = e[1]
            seq.append(cur)
        if not unused and cur == start:
            return seq[:-1]  # 12 positions; cyclic transition back to start included


def _rotate_to_avoid(prev, cyc):
    """Rotate a cycle so its first element differs from prev (no immediate repeats)."""
    for r in range(len(cyc)):
        c = cyc[r:] + cyc[:r]
        if prev is None or c[0] != prev:
            return c
    return cyc


def _make(rng, pattern):
    seq, kinds = [], []
    for kind, reps in SEG:
        for _ in range(reps):
            if kind == "pattern":
                cyc = list(pattern)
                if seq and seq[-1] == cyc[0]:
                    # entering the pattern segment: rotate once, consistently for all reps
                    pattern = _rotate_to_avoid(seq[-1], pattern)
                    cyc = list(pattern)
            else:
                while True:
                    cyc = _euler(rng)
                    if cyc != pattern and sorted([tuple(cyc[r:] + cyc[:r]) for r in range(12)])[0] != \
                            sorted([tuple(pattern[r:] + pattern[:r]) for r in range(12)])[0]:
                        break
                cyc = _rotate_to_avoid(seq[-1] if seq else None, cyc)
            seq.extend(cyc)
            kinds.extend([kind] * len(cyc))
    return {"targets": seq, "kinds": kinds, "pattern": pattern}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        p1 = _euler(rng)
        while True:
            p2 = _euler(rng)
            if sorted(tuple(p2[r:] + p2[:r]) for r in range(12)) != sorted(tuple(p1[r:] + p1[:r]) for r in range(12)):
                break
        items.append(_make(rng, p1))
        items.append(_make(rng, p2))
    return items[:n]


@G.safe
def score(item, response):
    """response: [{"key": 0-3 or null, "rt": ms}] in target order.
    Each target is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 2000 ms response window) or timely; only a TIMELY key equal to
    the target position is correct (an anticipatory, late or malformed press never is).
    hit = overall accuracy >= 85 % (omissions and invalid entries wrong) - the trial counts
    as properly done.
    metrics: accuracy; median correct RT in the last two pattern cycles and in the two
    random segments (first and last); pattern_effect_ms = mean of the two random medians
    minus the late-pattern median (positive = faster on the pattern); omissions;
    anticipations; every target's status in events."""
    a = G.Audit(CEILING_MS)
    targets, kinds = item["targets"], item["kinds"]
    if not isinstance(response, list):
        return a.junk(len(targets))
    rows = []
    for k, (t, r) in enumerate(zip(targets, a.entries(response, len(targets)))):
        status, key, rt = a.keyed(r, range(N_POS), window=WINDOW_MS)
        good = status == G.TIMELY and key == t
        rows.append({"i": k, "kind": kinds[k], "status": status, "ok": good, "rt": rt if good else None})
    n = len(rows)
    acc = sum(r["ok"] for r in rows) / n if n else 0.0

    def med(sel):
        return G.median([r["rt"] for r in sel if r["ok"]])

    idx = [k for k, kd in enumerate(kinds) if kd == "pattern"]
    m1 = m2 = mp = None
    if idx:
        first_pat, last_pat = idx[0], idx[-1]
        m1, m2 = med(rows[:first_pat]), med(rows[last_pat + 1:])
        mp = med(rows[max(0, last_pat + 1 - 24):last_pat + 1])
    effect = round((m1 + m2) / 2 - mp, 1) if None not in (m1, m2, mp) else None
    return a.finish(n > 0 and acc >= 0.85, sum(not r["ok"] for r in rows), {
        "accuracy": round(acc, 3), "rt_random_first": m1, "rt_random_last": m2,
        "rt_pattern_late": mp, "pattern_effect_ms": effect,
        "valid_rt_n": sum(1 for r in rows if r["ok"]),
        "omissions": sum(r["status"] == G.ABSENT for r in rows),
        "anticipations": sum(r["status"] == G.ANTICIPATORY for r in rows),
        "events": [{"i": r["i"], "kind": r["kind"], "status": r["status"], "correct": r["ok"], "rt": r["rt"]}
                   for r in rows]})


def example_response(item, correct=True):
    out = []
    for t, kd in zip(item["targets"], item["kinds"]):
        out.append({"key": t if correct else (t + 1) % N_POS, "rt": 380 if kd == "pattern" else 430})
    return out
