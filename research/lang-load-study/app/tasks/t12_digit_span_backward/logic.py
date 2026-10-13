"""Backward digit span (card 12), adapted to one sequence per trial. Same generator and
screen as forward span (card 11); only the lengths and the recall direction differ.

After "Start" the digits appear one per second (750 ms shown, 250 ms blank) and are never
shown again. The person then types them in REVERSE order (last digit first) on an on-screen keypad (or the
keyboard) and presses OK.

Items: lengths 2-7 (card). Both items of a pair (k, k+1) have the same length; pair
lengths walk through shuffled passes of 2..7, so a long run of pairs covers every length
about equally. Digits are distinct within a sequence (so no immediate repeats), no three
digits in a row form a +1/-1 run (e.g. 4-5-6), sequences of 3+ are never fully sorted up or
down (so reversing is never the same as sorting), and no sequence repeats within the set.
Digits are stored as a STRING ("0583"), so leading zeros survive and nothing is coerced
to a number.
"""

DIGITS = "0123456789"
LENGTHS = (2, 3, 4, 5, 6, 7)
REVERSE = True  # backward span: recall order = presentation order reversed
MAX_ANSWER = 20


def _has_run(seq):
    d = [int(c) for c in seq]
    return any(d[i + 1] - d[i] == d[i + 2] - d[i + 1] and abs(d[i + 1] - d[i]) == 1
               for i in range(len(d) - 2))


def _sequence(rng, length, seen):
    while True:
        seq = "".join(rng.sample(DIGITS, length))
        monotone = length >= 3 and seq in ("".join(sorted(seq)), "".join(sorted(seq, reverse=True)))
        if not _has_run(seq) and not monotone and seq not in seen:
            seen.add(seq)
            return seq


def generate(rng, n, save_image):
    seen, items, order, length = set(), [], [], None
    for k in range(n):
        if k % 2 == 0:
            if not order:
                order = list(LENGTHS)
                rng.shuffle(order)
            length = order.pop()
        items.append({"digits": _sequence(rng, length, seen), "length": length})
    return items


def _target(item):
    """Independent oracle: the correct answer is the presented sequence (reversed for
    backward span), recomputed from the digits, never taken from the browser."""
    seq = str(item["digits"])
    return seq[::-1] if REVERSE else seq


def _answer(response):
    if not isinstance(response, dict):
        return None
    a = response.get("answer")
    if not isinstance(a, str) or len(a) > MAX_ANSWER or any(c not in DIGITS for c in a):
        return None  # only a string of ASCII digits is accepted; numbers are rejected, not coerced
    return a


def _ms(x):
    return round(float(x)) if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x < 1e7 else None


def score(item, response):
    """response: {"answer": "0583", "rt": ms recall start -> OK, "first_rt": ms to first key,
    "edits": deletions, "onsets": [ms], "interrupted": bool (tab hidden while digits showed)}.

    The target is the WHOLE presented sequence reversed (oracle: digits[::-1]).
    hit = the typed string equals the target sequence exactly (every digit, right order,
    right length). errors = positions wrong or missing or extra (max(len) - correct positions).
    metrics: positional_accuracy = correct positions / sequence length; span_credit = length
    when exact else 0. Maximum-length criterion (computed across trials in analysis): span =
    the longest length at which at least half of that person's trials at that length are exact.
    """
    target = _target(item)
    ans = _answer(response)
    if ans is None:
        return {"hit": False, "errors": len(target),
                "metrics": {"length": len(target), "valid_response": False, "exact": False,
                            "positional_accuracy": 0.0, "correct_positions": 0, "span_credit": 0}}
    correct = sum(1 for i, c in enumerate(target) if i < len(ans) and ans[i] == c)
    exact = ans == target
    return {"hit": exact, "errors": max(len(target), len(ans)) - correct,
            "metrics": {"length": len(target), "valid_response": True, "exact": exact,
                        "positional_accuracy": round(correct / len(target), 3), "correct_positions": correct,
                        "answer_length": len(ans), "span_credit": len(target) if exact else 0,
                        "rt_ms": _ms(response.get("rt")), "first_key_rt_ms": _ms(response.get("first_rt")),
                        "edits": _ms(response.get("edits")),
                        "interrupted": response.get("interrupted") is True}}


def example_response(item, correct=True):
    target = _target(item)
    # wrong: the digits in presentation (forward) order; digits are distinct, so this always differs
    answer = target if correct else str(item["digits"])
    return {"answer": answer, "rt": 4000, "first_rt": 900, "edits": 0, "interrupted": False}
