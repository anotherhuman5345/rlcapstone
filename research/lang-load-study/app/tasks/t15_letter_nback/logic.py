"""Letter n-back (card 15), adapted: one trial = one short block at a single n.

After "Start" letters appear one at a time: 500 ms shown, then 1500 ms blank (one letter
every 2 s). For every letter the person answers "Same" (right arrow / button) if it is the
letter shown n steps earlier, otherwise "Different" (left arrow / button). The first answer
inside the 2000 ms window from letter onset counts; later presses are ignored. The stream
runs at a fixed pace whatever the person does.

Items: n + 20 letters; the first n are warm-up and never scored (they have nothing n back),
the 20 scored letters contain exactly 5 matches (25%, card), never two in a row. n is 1, 2
or 3 and is the same for both items of a pair (k, k+1); pairs cycle n = 1, 2, 3, ... so a round mixes loads.
Non-match letters are chosen so they also differ from the letters n-1 and n+1 back, so
blocks contain no accidental matches and no n+/-1 lures (lure count is still recomputed
by score() and reported). Letters: B D F G H K L M N P R S T Z - the same shapes and
common in both the English and Turkish alphabets (no Q W X, no I/İ/ı confusion, no vowels
that form words, no Ç Ğ Ö Ş Ü).
"""
from statistics import NormalDist, median

LETTERS = "BDFGHKLMNPRSTZ"
SCORED = 20
MATCHES = 5
NS = (1, 2, 3)


def _targets(rng, n, total):
    """5 match positions among the scored ones, never two in a row (avoids streaks)."""
    while True:
        t = sorted(rng.sample(range(n, total), MATCHES))
        if all(b - a > 1 for a, b in zip(t, t[1:])):
            return set(t)


def _stream(rng, n):
    total = n + SCORED
    targets = _targets(rng, n, total)
    out = []
    for i in range(total):
        if i in targets:
            out.append(out[i - n])
            continue
        banned = {out[j] for j in (i - n, i - n + 1, i - n - 1) if 0 <= j < i}
        out.append(rng.choice([c for c in LETTERS if c not in banned]))
    return out


def generate(rng, n, save_image):
    items, seen = [], set()
    for k in range(n):
        nb = NS[(k // 2) % len(NS)]
        while True:
            s = _stream(rng, nb)
            if tuple(s) not in seen:
                seen.add(tuple(s))
                break
        items.append({"n": nb, "letters": s})
    return items


def _key(item):
    """Independent oracle: is letter i the same as the letter n positions earlier? Positions
    i < n have no n-back letter (no wraparound) and are not scored (None)."""
    n, s = int(item["n"]), [str(c) for c in item["letters"]]
    return [None if i < n else s[i] == s[i - n] for i in range(len(s))]


def _lures(item):
    """Non-match letters equal to the letter n-1 or n+1 back (n+/-1 lures)."""
    n, s = int(item["n"]), [str(c) for c in item["letters"]]
    return sum(1 for i in range(n, len(s)) if s[i] != s[i - n]
               and any(0 <= j < i and s[j] == s[i] for j in (i - n + 1, i - n - 1)))


def _rows(response, length):
    resp = response.get("responses") if isinstance(response, dict) else None
    resp = resp if isinstance(resp, list) else []
    rows = []
    for i in range(length):
        r = resp[i] if i < len(resp) and isinstance(resp[i], dict) else {}
        key = r.get("key") if r.get("key") in ("match", "nonmatch") else None
        rt = r.get("rt")
        rt = float(rt) if key and isinstance(rt, (int, float)) and not isinstance(rt, bool) and 0 <= rt < 1e5 else None
        rows.append((key, rt))
    return rows


def _z(p):
    return NormalDist().inv_cdf(p)


def score(item, response):
    """response: {"responses": [{"key": "match"|"nonmatch"|null, "rt": ms from letter onset}]
    one per letter in display order, "onsets": [ms], "interrupted": bool}.

    Only letters n..end are scored (the first n are warm-up). Omissions count as incorrect.
    hit = balanced accuracy >= 0.75, where balanced accuracy = mean of (correct "Same" on
    match letters / match letters) and (correct "Different" on non-match letters / non-match
    letters). Balanced, so pressing "Different" every time scores 0.5, not 0.75.
    errors = scored letters not answered correctly (wrong key or no key).
    d' = z(H) - z(F) with the finite-rate correction H = (hits + 0.5) / (match letters + 1),
    F = (false alarms + 0.5) / (non-match letters + 1); a false alarm is "Same" on a non-match
    letter (an omission on a non-match letter is an error but not a false alarm).
    Correct RTs: median RT of hits and of correct rejections.
    """
    key = _key(item)
    valid = isinstance(response, dict) and isinstance(response.get("responses"), list)
    rows = _rows(response, len(key))
    hits = misses = fas = crs = omissions = 0
    rt_hit, rt_cr = [], []
    for target, (k, rt) in zip(key, rows):
        if target is None:
            continue
        if k is None:
            omissions += 1
        if target:
            if k == "match":
                hits += 1
                if rt is not None:
                    rt_hit.append(rt)
            else:
                misses += 1
        else:
            if k == "match":
                fas += 1
            elif k == "nonmatch":
                crs += 1
                if rt is not None:
                    rt_cr.append(rt)
    n_t = sum(1 for t in key if t is True)
    n_n = sum(1 for t in key if t is False)
    hit_rate = hits / n_t if n_t else 0.0
    cr_rate = crs / n_n if n_n else 0.0
    balanced = (hit_rate + cr_rate) / 2
    h = (hits + 0.5) / (n_t + 1)
    f = (fas + 0.5) / (n_n + 1)
    scored = n_t + n_n
    return {"hit": bool(valid and balanced >= 0.75), "errors": scored - hits - crs,
            "metrics": {"n": int(item["n"]), "valid_response": valid, "scored_items": scored,
                        "match_items": n_t, "hits": hits, "misses": misses, "false_alarms": fas,
                        "correct_rejections": crs, "omissions": omissions,
                        "accuracy": round((hits + crs) / scored, 3) if scored else 0.0,
                        "balanced_accuracy": round(balanced, 3), "hit_rate": round(hit_rate, 3),
                        "false_alarm_rate": round(fas / n_n, 3) if n_n else 0.0,
                        "d_prime": round(_z(h) - _z(f), 3),
                        "median_rt_hit": round(median(rt_hit), 1) if rt_hit else None,
                        "median_rt_correct_rejection": round(median(rt_cr), 1) if rt_cr else None,
                        "valid_rt_trials": len(rt_hit) + len(rt_cr), "lures": _lures(item),
                        "interrupted": isinstance(response, dict) and response.get("interrupted") is True}}


def example_response(item, correct=True):
    key = _key(item)
    out = []
    for t in key:
        want = "match" if t else "nonmatch"
        if not correct:
            want = {"match": "nonmatch", "nonmatch": "match"}[want]
        out.append({"key": want, "rt": 650.0})
    return {"responses": out, "onsets": [2000 * i for i in range(len(key))], "interrupted": False}
