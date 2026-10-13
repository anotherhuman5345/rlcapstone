"""Attentional blink (card 07): a rapid stream of letters (100 ms each, no gap) in black;
two letters are shown in red (the targets). After the stream, report both red letters.
One trial is 10 streams of 18 letters: lags 1, 2, 3, 5, 7 (T2 position - T1 position),
each twice, shuffled. T1 is at position 4-7, so there are at least 4 letters before T1 and
at least 3 after T2 (no target next to the stream boundary). Within an item no letter is a
target twice (20 different targets); a stream's targets never appear as its distractors
and no letter repeats back to back.
Letters: a Latin set shared by English and Turkish keyboards, without I/İ, O/Ö, Q, W, X
and Turkish-only letters, so the stimulus is the same in both languages.
Pairs (k, k+1) share the lag order and T1 positions; letters differ."""
from collections import defaultdict

LETTERS = list("ABCDEFGHJKLMNPRSTUVYZ")   # 21 letters
STREAM_LEN = 18
LAGS = (1, 2, 3, 5, 7)
REPEATS = 2
SOA_MS = 100
T1_POS = (4, 5, 6, 7)


def _stream(rng, t1, lag, a, b):
    letters, prev = [], None
    pool = [c for c in LETTERS if c not in (a, b)]
    for i in range(STREAM_LEN):
        if i == t1:
            c = a
        elif i == t1 + lag:
            c = b
        else:
            nxt_target = a if i + 1 == t1 else (b if i + 1 == t1 + lag else None)
            c = rng.choice([x for x in pool if x != prev and x != nxt_target])
        letters.append(c)
        prev = c
    return {"letters": letters, "t1": t1, "t2": t1 + lag, "lag": lag}


def generate(rng, n, save_image):
    items, plan = [], None
    for k in range(n):
        if k % 2 == 0:
            lags = list(LAGS) * REPEATS
            rng.shuffle(lags)
            plan = [(rng.choice(T1_POS), lag) for lag in lags]
        targets = rng.sample(LETTERS, 2 * len(plan))
        streams = [_stream(rng, t1, lag, targets[2 * i], targets[2 * i + 1]) for i, (t1, lag) in enumerate(plan)]
        items.append({"soa_ms": SOA_MS, "choices": LETTERS, "streams": streams})
    return items


def _letter(x):
    return x if isinstance(x, str) and x in LETTERS else None


def score(item, response):
    """response: [{"r1": letter, "r2": letter, "late": ms}] per stream (r1/r2 in the order
    given; scored order-free: a target counts as reported if either answer names it).
    "late" = largest observed-minus-intended letter onset in the stream (flag if > 25 ms).
    Metrics: T1 accuracy, T2 accuracy given correct T1 (T2|T1) overall and by lag, both-correct
    rate. hit = both targets reported in at least half of the streams."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, st in enumerate(item["streams"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        said = {_letter(r.get("r1")), _letter(r.get("r2"))} - {None}
        a, b = st["letters"][st["t1"]], st["letters"][st["t2"]]
        late = r.get("late")
        flag = isinstance(late, (int, float)) and not isinstance(late, bool) and abs(late) > 25
        rows.append({"lag": st["lag"], "t1": a in said, "t2": b in said, "flag": flag})
    n = len(rows)
    t1_ok = [r for r in rows if r["t1"]]
    by_lag = defaultdict(list)
    for r in t1_ok:
        by_lag[r["lag"]].append(r["t2"])
    both = sum(r["t1"] and r["t2"] for r in rows)
    return {"hit": n > 0 and both / n >= 0.5,
            "errors": sum((not r["t1"]) + (not r["t2"]) for r in rows),
            "metrics": {"t1_accuracy": round(len(t1_ok) / n, 3) if n else None,
                        "t2_given_t1": round(sum(r["t2"] for r in t1_ok) / len(t1_ok), 3) if t1_ok else None,
                        "t2_given_t1_by_lag": {str(l): round(sum(v) / len(v), 3) for l, v in sorted(by_lag.items())},
                        "n_t1_correct_by_lag": {str(l): len(v) for l, v in sorted(by_lag.items())},
                        "both_correct": both, "streams": n,
                        "timing_flagged_streams": sum(r["flag"] for r in rows)}}


def example_response(item, correct=True):
    out = []
    for st in item["streams"]:
        a, b = st["letters"][st["t1"]], st["letters"][st["t2"]]
        if correct:
            out.append({"r1": a, "r2": b, "late": 4})
        else:
            wrong = [c for c in LETTERS if c not in (a, b)]
            out.append({"r1": wrong[0], "r2": wrong[1], "late": 4})
    return out
