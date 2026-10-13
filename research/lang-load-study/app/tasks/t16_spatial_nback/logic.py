"""Spatial n-back (card 16), adapted: one trial = one short block at a single n.

A 3x3 grid; after "Start" one cell lights up at a time: 500 ms lit, then 1500 ms dark (one
location every 2 s). For every location the person answers "Same" (right arrow / button)
if it is the cell lit n steps earlier, otherwise "Different" (left arrow / button). The first
answer inside the 2000 ms window from onset counts; later presses are ignored. The stream
runs at a fixed pace whatever the person does.

Items: n + 20 locations; the first n are warm-up and never scored (nothing n back; no
wraparound), the 20 scored locations contain exactly 5 matches (25%), never two in a row.
n is 1 or 2 (card) and is the same for both items of a pair (k, k+1); pairs alternate n = 1, 2, 1, ...
Non-match cells also differ from the cells n-1 and n+1 back (no accidental matches, no
n+/-1 lures; score() recomputes and reports lures). Spatial frequency is balanced: each
non-match cell is drawn from the least-used allowed cells, so every cell is used about
equally (max - min use <= 2 is enforced). Cells are numbered 0-8 row by row.
"""
from statistics import NormalDist

from app.tasks import _guard as G

TIMING = "window"      # view.js: SOA = 2000; the first answer inside the 2000 ms window counts
SOA_MS = 2000
WINDOW_MS = SOA_MS
RT_SLACK_MS = 50       # timer tolerance: the window closes at the next onset, which can lag a frame
ONSET_TOL_MS = 50
KEYS = ("match", "nonmatch")
CEILING_MS = G.trial_ceiling(__file__)

CELLS = 9
SCORED = 20
MATCHES = 5
NS = (1, 2)


def _targets(rng, n, total):
    """5 match positions among the scored ones, never two in a row (avoids streaks)."""
    while True:
        t = sorted(rng.sample(range(n, total), MATCHES))
        if all(b - a > 1 for a, b in zip(t, t[1:])):
            return set(t)


def _stream(rng, n):
    total = n + SCORED
    while True:
        targets = _targets(rng, n, total)
        out, used = [], [0] * CELLS
        for i in range(total):
            if i in targets:
                c = out[i - n]
            else:
                banned = {out[j] for j in (i - n, i - n + 1, i - n - 1) if 0 <= j < i}
                allowed = [c for c in range(CELLS) if c not in banned]
                low = min(used[c] for c in allowed)
                c = rng.choice([c for c in allowed if used[c] == low])
            out.append(c)
            used[c] += 1
        if max(used) - min(used) <= 2:
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
        items.append({"n": nb, "cells": s})
    return items


def _key(item):
    """Independent oracle: is cell i the same as the cell n positions earlier? Positions
    i < n have no n-back cell (no wraparound) and are not scored (None)."""
    n, s = int(item["n"]), [int(c) for c in item["cells"]]
    return [None if i < n else s[i] == s[i - n] for i in range(len(s))]


def _lures(item):
    """Non-match cells equal to the cell n-1 or n+1 back (n+/-1 lures)."""
    n, s = int(item["n"]), [int(c) for c in item["cells"]]
    return sum(1 for i in range(n, len(s)) if s[i] != s[i - n]
               and any(0 <= j < i and s[j] == s[i] for j in (i - n + 1, i - n - 1)))


def _rows(response, length, a):
    """One (status, key, rt) per stimulus (app/tasks/_guard.py): exactly `length` entries
    (missing ones invalid, extra ones flagged). Only a TIMELY entry carries a key that may be
    scored as an answer made in the window."""
    raw = response.get("responses", G.MISSING) if isinstance(response, dict) else G.MISSING
    return [a.keyed(r, KEYS, window=WINDOW_MS, slack=RT_SLACK_MS) for r in a.entries(raw, length, "responses")]


def _onsets(response, length, a):
    """Presentation onsets (ms from the first stimulus): one per stimulus, finite, within the
    trial, strictly increasing. Problems are flagged (they describe the presentation, the
    answers are still scored). Returns the list (None for bad values) or None if absent."""
    if "onsets" not in response:
        a.malformed("missing_onsets")
        return None
    raw = response["onsets"]
    if not isinstance(raw, list):
        a.malformed("invalid_onsets")
        return None
    vals = []
    for v in a.entries(raw, length, "onsets"):
        if v is G.MISSING:
            vals.append(None)
            continue
        st, t = a.time(v, field="onsets", floor=0)
        vals.append(t if st == G.TIMELY else None)
    prev = None
    for t in vals:
        if t is None:
            continue
        if prev is not None and t <= prev:
            a.malformed("non_increasing_onsets")
            break
        prev = t
    drift = [t - i * SOA_MS for i, t in enumerate(vals) if t is not None]
    if any(d < -ONSET_TOL_MS or d > SOA_MS for d in drift):
        a.flag("onset_drift")       # a stimulus shown more than one SOA off its schedule
    return vals


def _z(p):
    return NormalDist().inv_cdf(p)


@G.safe
def score(item, response):
    """response: {"responses": [{"key": "match"|"nonmatch"|null, "rt": ms from onset}]
    one per location in display order, "onsets": [ms], "interrupted": bool}.

    Every entry is classified (app/tasks/_guard.py): absent (no key, no rt), invalid (unknown
    key, key without rt or rt without key, non-finite / negative / impossible rt, entry
    missing), anticipatory (rt < 100 ms), late (rt beyond the 2000 ms window + 50 ms timer
    tolerance; the browser ignores later presses) or timely. Only a timely key is an answer.
    Only locations n..end are scored (the first n are warm-up). Omissions (absent) and
    anticipatory / late / invalid entries count as incorrect.
    hit = balanced accuracy >= 0.75, where balanced accuracy = mean of (timely correct "Same"
    on match locations / match locations) and (timely correct "Different" on non-match locations /
    non-match locations). Balanced, so pressing "Different" every time scores 0.5, not 0.75.
    errors = scored locations not answered correctly (wrong key, no key or no timely key).
    d' = z(H) - z(F) with the finite-rate correction H = (hits + 0.5) / (match locations + 1),
    F = (false alarms + 0.5) / (non-match locations + 1); a false alarm is a timely "Same" on a
    non-match location (an omission on a non-match location is an error but not a false alarm).
    Correct RTs: median RT of hits and of correct rejections.
    "onsets" (presentation timing) are checked: one per location, finite, within the trial,
    strictly increasing; problems are flagged. "interrupted" must be a bool (flagged else).
    """
    key = _key(item)
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(sum(1 for t in key if t is not None))
    valid = isinstance(response.get("responses"), list)
    rows = _rows(response, len(key), a)
    _onsets(response, len(key), a)
    interrupted = a.opt_bool(response, "interrupted")
    hits = misses = fas = crs = omissions = anticip = late = invalid = 0
    rt_hit, rt_cr = [], []
    for target, (st, k, rt) in zip(key, rows):
        if target is None:
            continue
        if st == G.ABSENT:
            omissions += 1
        elif st == G.ANTICIPATORY:
            anticip += 1
        elif st == G.LATE:
            late += 1
        elif st == G.INVALID:
            invalid += 1
        if st != G.TIMELY:
            k = None
        if target:
            if k == "match":
                hits += 1
                rt_hit.append(rt)
            else:
                misses += 1
        else:
            if k == "match":
                fas += 1
            elif k == "nonmatch":
                crs += 1
                rt_cr.append(rt)
    n_t = sum(1 for t in key if t is True)
    n_n = sum(1 for t in key if t is False)
    hit_rate = hits / n_t if n_t else 0.0
    cr_rate = crs / n_n if n_n else 0.0
    balanced = (hit_rate + cr_rate) / 2
    h = (hits + 0.5) / (n_t + 1)
    f = (fas + 0.5) / (n_n + 1)
    scored = n_t + n_n
    return a.finish(valid and balanced >= 0.75, scored - hits - crs, {
        "n": int(item["n"]), "valid_response": valid, "scored_items": scored,
        "match_items": n_t, "hits": hits, "misses": misses, "false_alarms": fas,
        "correct_rejections": crs, "omissions": omissions,
        "anticipations": anticip, "late_responses": late, "invalid_responses": invalid,
        "accuracy": round((hits + crs) / scored, 3) if scored else 0.0,
        "balanced_accuracy": round(balanced, 3), "hit_rate": round(hit_rate, 3),
        "false_alarm_rate": round(fas / n_n, 3) if n_n else 0.0,
        "d_prime": round(_z(h) - _z(f), 3),
        "median_rt_hit": G.median(rt_hit), "median_rt_correct_rejection": G.median(rt_cr),
        "valid_rt_trials": len(rt_hit) + len(rt_cr), "lures": _lures(item),
        "interrupted": interrupted is True})


def example_response(item, correct=True):
    key = _key(item)
    out = []
    for t in key:
        want = "match" if t else "nonmatch"
        if not correct:
            want = {"match": "nonmatch", "nonmatch": "match"}[want]
        out.append({"key": want, "rt": 650.0})
    return {"responses": out, "onsets": [2000 * i for i in range(len(key))], "interrupted": False}
