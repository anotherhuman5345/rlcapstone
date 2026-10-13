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

# (x, y) centres as fractions of a 3:2 board; irregular, no overlaps for 11%-wide squares.
BLOCKS = [(0.12, 0.22), (0.38, 0.12), (0.70, 0.18), (0.88, 0.42), (0.55, 0.45),
          (0.24, 0.60), (0.46, 0.82), (0.76, 0.74), (0.10, 0.88)]
LENGTHS = (2, 3, 4, 5, 6)


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


def _clicks(response):
    if not isinstance(response, dict):
        return None
    c = response.get("clicks")
    if not isinstance(c, list) or len(c) > 20:
        return None
    if not all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(BLOCKS) for i in c):
        return None
    return c


def _ms(x):
    return round(float(x)) if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x < 1e7 else None


def score(item, response):
    """response: {"clicks": [square index, ...] in click order, "click_rts": [ms from the end of
    the sequence], "rt": ms to last click, "interrupted": bool (tab hidden during the sequence)}.

    hit = the clicks equal the lit sequence reversed, exactly (same squares, same order,
    same count). errors = positions wrong, missing or extra. metrics: positional_accuracy =
    correct positions / length; span_credit = length when exact else 0. Predefined span
    (across trials, in analysis): the longest length at which at least half of the
    person's trials at that length are exact.
    """
    target = _target(item)
    clicks = _clicks(response)
    if clicks is None:
        return {"hit": False, "errors": len(target),
                "metrics": {"length": len(target), "valid_response": False, "exact": False,
                            "positional_accuracy": 0.0, "correct_positions": 0, "span_credit": 0}}
    correct = sum(1 for i, b in enumerate(target) if i < len(clicks) and clicks[i] == b)
    exact = clicks == target
    forward = [int(i) for i in item["sequence"]]
    return {"hit": exact, "errors": max(len(target), len(clicks)) - correct,
            "metrics": {"length": len(target), "valid_response": True, "exact": exact,
                        "positional_accuracy": round(correct / len(target), 3), "correct_positions": correct,
                        "clicked": len(clicks), "span_credit": len(target) if exact else 0,
                        "recalled_forward": clicks == forward and len(target) > 1,
                        "rt_ms": _ms(response.get("rt")),
                        "interrupted": response.get("interrupted") is True}}


def example_response(item, correct=True):
    target = _target(item)
    clicks = target if correct else [int(i) for i in item["sequence"]]  # wrong: forward order
    return {"clicks": clicks, "click_rts": [800 * (k + 1) for k in range(len(clicks))],
            "rt": 800 * len(clicks), "interrupted": False}
