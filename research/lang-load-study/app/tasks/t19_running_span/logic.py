"""Running span (card 19), adapted to one stream per trial.

Before "Start" the person is told k (how many letters to keep). After "Start" letters
appear one per second (750 ms shown, 250 ms blank); the stream stops without warning. The
person then types the LAST k letters in the order they appeared, using an on-screen letter
keypad or the keyboard ("?" marks a letter they cannot recall), and presses OK once all k
places are filled. Nothing on screen counts the letters or shows progress, so the stop
cannot be anticipated, and the stream is never shown again.

Items: k = 3 or 4 (card); stream length 7-15, drawn at random. Both items of a pair (k, k+1)
share k and stream length; pairs alternate k = 3, 4, 3, ... Letters: B D F G H K L M N P R
S T Z (the same shapes and common in both English and Turkish; no vowels, no I/İ/ı).
No letter repeats within 4 places, so the last k letters are all different and the first
k letters are never the same as the last k. No stream repeats within the set.
"""

LETTERS = "BDFGHKLMNPRSTZ"
KS = (3, 4)
MIN_LEN, MAX_LEN = 7, 15
UNKNOWN = "?"


def _stream(rng, length):
    out = []
    for _ in range(length):
        recent = set(out[-4:])
        out.append(rng.choice([c for c in LETTERS if c not in recent]))
    return "".join(out)


def generate(rng, n, save_image):
    items, seen, k, length = [], set(), None, None
    for i in range(n):
        if i % 2 == 0:
            k = KS[(i // 2) % len(KS)]
            length = rng.randint(MIN_LEN, MAX_LEN)
        while True:
            s = _stream(rng, length)
            if s not in seen and s[:k] != s[-k:]:
                seen.add(s)
                break
        items.append({"k": k, "letters": s, "length": length})
    return items


def _target(item):
    """Independent oracle: the last k letters of the stream, in presentation order."""
    s, k = str(item["letters"]), int(item["k"])
    return s[-k:]


def _answer(response, k):
    if not isinstance(response, dict):
        return None
    a = response.get("answer")
    if not isinstance(a, str) or len(a) != k or any(c not in LETTERS + UNKNOWN for c in a):
        return None
    return a


def _ms(x):
    return round(float(x)) if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x < 1e7 else None


def score(item, response):
    """response: {"answer": "KMT" (exactly k characters; "?" = not recalled), "rt": ms from
    the stop to OK, "first_rt": ms to the first key, "edits": deletions, "onsets": [ms],
    "interrupted": bool (tab hidden while the stream played)}.

    hit = the answer equals the last k letters of the stream exactly, in order (correct
    ordered suffix). errors = k - letters in the right place. metrics: positional_accuracy =
    letters in the right place / k; item_accuracy = letters from the final k recalled in any
    place / k; recalled_first_k flags answers that match the FIRST k letters instead.
    """
    target = _target(item)
    k = len(target)
    ans = _answer(response, k)
    if ans is None:
        return {"hit": False, "errors": k,
                "metrics": {"k": k, "stream_length": len(str(item["letters"])), "valid_response": False,
                            "exact": False, "positional_accuracy": 0.0, "correct_positions": 0}}
    correct = sum(1 for a, t in zip(ans, target) if a == t)
    any_place = len(set(ans) & set(target))
    exact = ans == target
    return {"hit": exact, "errors": k - correct,
            "metrics": {"k": k, "stream_length": len(str(item["letters"])), "valid_response": True,
                        "exact": exact, "positional_accuracy": round(correct / k, 3), "correct_positions": correct,
                        "item_accuracy": round(any_place / k, 3), "unknown_marks": ans.count(UNKNOWN),
                        "recalled_first_k": ans == str(item["letters"])[:k],
                        "rt_ms": _ms(response.get("rt")), "first_key_rt_ms": _ms(response.get("first_rt")),
                        "edits": _ms(response.get("edits")),
                        "interrupted": response.get("interrupted") is True}}


def example_response(item, correct=True):
    k = int(item["k"])
    answer = _target(item) if correct else str(item["letters"])[:k]  # wrong: the FIRST k letters
    return {"answer": answer, "rt": 5000, "first_rt": 1200, "edits": 0, "interrupted": False}
