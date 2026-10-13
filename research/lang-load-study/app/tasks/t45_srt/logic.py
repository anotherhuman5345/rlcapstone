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


def score(item, response):
    """response: [{"key": 0-3 or null, "rt": ms}] in target order.
    hit = overall accuracy >= 85 % (omissions wrong) - the trial counts as properly done.
    metrics: accuracy; median correct RT in the last two pattern cycles and in the two
    random segments (first and last); pattern_effect_ms = mean of the two random medians
    minus the late-pattern median (positive = faster on the pattern); omissions."""
    try:
        targets, kinds = item["targets"], item["kinds"]
        resp = response if isinstance(response, list) else []
        rows = []
        for k, t in enumerate(targets):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            key, rt = r.get("key"), r.get("rt")
            good = isinstance(key, int) and not isinstance(key, bool) and key == t
            rows.append((kinds[k], good, rt if isinstance(rt, (int, float)) and rt > 0 else None, key is None))
        n = len(rows)
        acc = sum(g for _, g, _, _ in rows) / n

        def med(sel):
            v = sorted(rt for (kd, g, rt, _) in sel if g and rt is not None)
            if not v:
                return None
            m = len(v) // 2
            return float(v[m]) if len(v) % 2 else (v[m - 1] + v[m]) / 2
        idx = [k for k, kd in enumerate(kinds) if kd == "pattern"]
        first_pat, last_pat = idx[0], idx[-1]
        rand1 = rows[:first_pat]
        rand2 = rows[last_pat + 1:]
        late = rows[last_pat + 1 - 24:last_pat + 1]
        m1, m2, mp = med(rand1), med(rand2), med(late)
        effect = round((m1 + m2) / 2 - mp, 1) if None not in (m1, m2, mp) else None
        return {"hit": acc >= 0.85, "errors": sum(not g for _, g, _, _ in rows),
                "metrics": {"accuracy": round(acc, 3), "rt_random_first": m1, "rt_random_last": m2,
                            "rt_pattern_late": mp, "pattern_effect_ms": effect,
                            "valid_rt_n": sum(1 for _, g, rt, _ in rows if g and rt is not None),
                            "omissions": sum(om for _, _, _, om in rows)}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    out = []
    for t, kd in zip(item["targets"], item["kinds"]):
        out.append({"key": t if correct else (t + 1) % N_POS, "rt": 380 if kd == "pattern" else 430})
    return out
