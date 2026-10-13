"""Forward digit span (card 11), adapted to one sequence per trial.

After "Start" the digits appear one per second (750 ms shown, 250 ms blank) and are never
shown again. The person then types them in the SAME order on an on-screen keypad (or the
keyboard) and presses OK.

Items: lengths 3-8 (card). Both items of a pair (k, k+1) have the same length; pair
lengths walk through shuffled passes of 3..8, so a long run of pairs covers every length
about equally. Digits are distinct within a sequence (so no immediate repeats), no three
digits in a row form a +1/-1 run (e.g. 4-5-6), sequences of 3+ are never fully sorted up or
down (so reversing is never the same as sorting), and no sequence repeats within the set.
Digits are stored as a STRING ("0583"), so leading zeros survive and nothing is coerced
to a number.
"""

from app.tasks import _guard as G

TIMING = "untimed"   # recall is unspeeded; times are descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)
DIGITS = "0123456789"
LENGTHS = (3, 4, 5, 6, 7, 8)
REVERSE = False  # forward span: recall order = presentation order
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


def _answer(a, audit):
    """Only a string of ASCII digits (at most MAX_ANSWER) is an answer; numbers are rejected,
    not coerced. Anything else is flagged and returns None."""
    if isinstance(a, str) and len(a) <= MAX_ANSWER and all(c in DIGITS for c in a):
        return a
    audit.malformed("invalid_answer" if a is not G.MISSING else "missing_answer")
    return None


@G.safe
def score(item, response):
    """response: {"answer": "0583", "rt": ms recall start -> OK, "first_rt": ms to first key,
    "edits": deletions, "onsets": [ms], "interrupted": bool (tab hidden while digits showed)}.

    hit = the typed string equals the target sequence exactly (every digit, right order,
    right length). errors = positions wrong or missing or extra (max(len) - correct positions).
    Recall is unspeeded: rt / first_rt / edits / onsets are descriptive and are checked
    (finite, non-negative, below the trial timeout, onsets increasing); bad values are
    flagged in metrics["flags"] and reported as null, the answer is still scored.
    metrics: positional_accuracy = correct positions / sequence length; span_credit = length
    when exact else 0. Maximum-length criterion (computed across trials in analysis): span =
    the longest length at which at least half of that person's trials at that length are exact.
    """
    target = _target(item)
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(len(target))
    ans = _answer(response.get("answer", G.MISSING), a)
    rt = a.duration(response, "rt")
    first = a.duration(response, "first_rt", floor=0)
    edits = a.opt_int(response, "edits", hi=1000)
    interrupted = a.opt_bool(response, "interrupted")
    if "onsets" in response:
        onsets = a.stream(response["onsets"], "onsets", cap=100)
        ts = []
        for v in onsets:
            st, t = a.time(v, field="onsets", floor=0)
            ts.append(t if st == G.TIMELY else None)
        a.monotonic(ts, "onsets")
    if rt is not None and first is not None and first > rt:
        a.malformed("first_rt_after_rt")
    if ans is None:
        return a.finish(False, len(target), {
            "length": len(target), "valid_response": False, "exact": False, "positional_accuracy": 0.0,
            "correct_positions": 0, "span_credit": 0, "rt_ms": rt, "first_key_rt_ms": first,
            "edits": edits, "interrupted": interrupted})
    correct = sum(1 for i, c in enumerate(target) if i < len(ans) and ans[i] == c)
    exact = ans == target
    return a.finish(exact, max(len(target), len(ans)) - correct, {
        "length": len(target), "valid_response": True, "exact": exact,
        "positional_accuracy": round(correct / len(target), 3), "correct_positions": correct,
        "answer_length": len(ans), "span_credit": len(target) if exact else 0,
        "rt_ms": rt, "first_key_rt_ms": first, "edits": edits, "interrupted": interrupted})


def example_response(item, correct=True):
    target = _target(item)
    # wrong: swap the first two digits (distinct digits, so this always differs)
    answer = target if correct else target[1] + target[0] + target[2:]
    onsets = [1000 * i for i in range(len(str(item["digits"])))]
    return {"answer": answer, "rt": 4000, "first_rt": 900, "edits": 0, "onsets": onsets, "interrupted": False}
