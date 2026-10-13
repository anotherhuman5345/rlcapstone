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
from statistics import NormalDist, median

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
    """response: {"responses": [{"key": "match"|"nonmatch"|null, "rt": ms from onset}]
    one per location in display order, "onsets": [ms], "interrupted": bool}.

    Only locations n..end are scored (the first n are warm-up). Omissions count as incorrect.
    hit = balanced accuracy >= 0.75, where balanced accuracy = mean of (correct "Same" on
    match locations / match locations) and (correct "Different" on non-match locations /
    non-match locations). Balanced, so pressing "Different" every time scores 0.5, not 0.75.
    errors = scored locations not answered correctly (wrong key or no key).
    d' = z(H) - z(F) with the finite-rate correction H = (hits + 0.5) / (match locations + 1),
    F = (false alarms + 0.5) / (non-match locations + 1); a false alarm is "Same" on a non-match
    location (an omission on a non-match location is an error but not a false alarm).
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
