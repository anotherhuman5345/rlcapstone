"""Backward spatial span (card 14), adapted to one sequence per trial.

Nine squares sit at fixed, irregular places on a board (same kind of board as the Corsi
task). After "Start" some squares light up one at a time (500 ms lit, 500 ms gap). The
person then clicks/taps them (or Tab + Enter/Space) in REVERSE order: last lit first. The
trial ends by itself when they have clicked as many squares as were lit. Squares are
disabled while the sequence plays, so no click during encoding is accepted.

Items: lengths 2-6 (card). Both items of a pair (k, k+1) have the same length; pair lengths
walk through shuffled passes of 2..6. Squares are distinct within a sequence (no repeats,
so no adjacent duplicates and no palindromes), and no sequence repeats within the set.
"""
from app.tasks import _guard as G

TIMING = "untimed"   # recall is unspeeded (view.js has no recall limit); times are descriptive
CEILING_MS = G.trial_ceiling(__file__)

# (x, y) centres as fractions of a 3:2 board; irregular, no overlaps for 11%-wide squares.
BLOCKS = [(0.12, 0.22), (0.38, 0.12), (0.70, 0.18), (0.88, 0.42), (0.55, 0.45),
          (0.24, 0.60), (0.46, 0.82), (0.76, 0.74), (0.10, 0.88)]
LENGTHS = (2, 3, 4, 5, 6)
MAX_CLICKS = 20


def generate(rng, n, save_image):
    seen, items, order, length = set(), [], [], None
    for k in range(n):
        if k % 2 == 0:
            if not order:
                order = list(LENGTHS)
                rng.shuffle(order)
            length = order.pop()
        while True:
            seq = rng.sample(range(len(BLOCKS)), length)
            if tuple(seq) not in seen:
                seen.add(tuple(seq))
                break
        items.append({"blocks": [list(b) for b in BLOCKS], "sequence": seq, "length": length})
    return items


def _target(item):
    """Independent oracle: the whole lit sequence, reversed."""
    return [int(i) for i in item["sequence"]][::-1]


def _clicks(response, a):
    """The click list, or None (flagged) unless it is a list of at most MAX_CLICKS square
    indices 0..8 (no coercion of other types)."""
    c = response.get("clicks", G.MISSING)
    if c is G.MISSING:
        a.malformed("missing_clicks")
        return None
    if not isinstance(c, list) or len(c) > MAX_CLICKS:
        a.malformed("invalid_clicks")
        return None
    if not all(G.member(i, range(len(BLOCKS))) for i in c):
        a.malformed("invalid_click_index")
        return None
    return c


def _times(response, n_clicks, a):
    """Check click_rts (one finite, non-negative, non-decreasing time per click, below the
    trial timeout) and rt (= the last click time). Returns (rt or None, click_rts list)."""
    rt = a.duration(response, "rt")
    raw = response.get("click_rts", G.MISSING)
    ts = []
    if raw is G.MISSING:
        a.malformed("missing_click_rts")
    else:
        seq = a.stream(raw, "click_rts", cap=MAX_CLICKS)
        for v in seq:
            st, t = a.time(v, field="click_rts", floor=0)
            ts.append(t if st == G.TIMELY else None)
        a.monotonic(ts, "click_rts")
        if isinstance(raw, list) and n_clicks is not None and len(raw) != n_clicks:
            a.flag("click_rts_count_mismatch")
        if rt is not None and ts and ts[-1] is not None and ts[-1] != rt:
            a.flag("rt_not_last_click")
    return rt, ts


@G.safe
def score(item, response):
    """response: {"clicks": [square index, ...] in click order, "click_rts": [ms from the end of
    the sequence], "rt": ms to last click, "interrupted": bool (tab hidden during the sequence)}.

    hit = the clicks equal the lit sequence reversed, exactly (same squares, same order,
    same count). errors = positions wrong, missing or extra. metrics: positional_accuracy =
    correct positions / length; span_credit = length when exact else 0. Predefined span
    (across trials, in analysis): the longest length at which at least half of the
    person's trials at that length are exact.
    Clicks must be integer square indices (anything else makes the response invalid,
    flagged); the view ends the trial after exactly `length` clicks, so another count is
    flagged. Recall is unspeeded: rt / click_rts are descriptive and checked (finite,
    non-negative, below the trial timeout, click times non-decreasing, one per click, rt =
    last click); bad values are flagged and reported as null, the clicks are still scored.
    """
    target = _target(item)
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(len(target))
    clicks = _clicks(response, a)
    rt, _ = _times(response, len(clicks) if clicks is not None else None, a)
    interrupted = a.opt_bool(response, "interrupted")
    if clicks is None:
        return a.finish(False, len(target), {
            "length": len(target), "valid_response": False, "exact": False,
            "positional_accuracy": 0.0, "correct_positions": 0, "span_credit": 0,
            "rt_ms": rt, "interrupted": interrupted})
    if len(clicks) != len(target):
        a.flag("click_count_mismatch")
    correct = sum(1 for i, b in enumerate(target) if i < len(clicks) and clicks[i] == b)
    exact = clicks == target
    forward = [int(i) for i in item["sequence"]]
    return a.finish(exact, max(len(target), len(clicks)) - correct, {
        "length": len(target), "valid_response": True, "exact": exact,
        "positional_accuracy": round(correct / len(target), 3), "correct_positions": correct,
        "clicked": len(clicks), "span_credit": len(target) if exact else 0,
        "recalled_forward": clicks == forward and len(target) > 1,
        "rt_ms": round(rt) if rt is not None else None,
        "interrupted": interrupted})


def example_response(item, correct=True):
    target = _target(item)
    clicks = target if correct else [int(i) for i in item["sequence"]]  # wrong: forward order
    return {"clicks": clicks, "click_rts": [800 * (k + 1) for k in range(len(clicks))],
            "rt": 800 * len(clicks), "interrupted": False}
