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

from app.tasks import _guard as G

# The report is unspeeded; the timed quantity is the presentation drift "late" (view.js
# play(): largest observed-minus-intended letter onset). A drift beyond one SOA means a
# letter slot was skipped, so the window is the 100 ms SOA (item.soa_ms in view.js).
TIMING = "window"

LETTERS = list("ABCDEFGHJKLMNPRSTUVYZ")   # 21 letters
STREAM_LEN = 18
LAGS = (1, 2, 3, 5, 7)
REPEATS = 2
SOA_MS = 100
T1_POS = (4, 5, 6, 7)
WINDOW_MS = SOA_MS
DRIFT_FLAG_MS = 25     # drift above this (but within one SOA) is flagged, the stream still counts
CEILING_MS = G.trial_ceiling(__file__)


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


def _letter(x, a, field):
    """An answer letter: a member of LETTERS, else None (flagged invalid_/missing_<field>)."""
    if x is G.MISSING:
        a.malformed(f"missing_{field}")
        return None
    if G.member(x, LETTERS):
        return x
    a.malformed(f"invalid_{field}")
    return None


@G.safe
def score(item, response):
    """response: [{"r1": letter, "r2": letter, "late": ms}] per stream (r1/r2 in the order
    given; scored order-free: a target counts as reported if either answer names it).
    "late" = largest observed-minus-intended letter onset in the stream (presentation drift,
    view.js play()). The report itself is unspeeded.

    Presentation validity: drift must be a finite number in [0, SOA] (100 ms). A drift above
    one SOA means a whole letter slot was skipped (a target may never have been shown); a
    missing, non-numeric, negative or impossible drift means the presentation is unknown.
    Such a stream is flagged and can never count as reported (T1, T2 or both); drift > 25 ms
    but within one SOA is only flagged (timing_flagged_streams).
    r1/r2 must be letters of the choice set (missing / invalid letters are flagged and never
    match). Exactly one entry per stream (missing entries count as not reported, extra ones
    are flagged).
    Metrics: T1 accuracy, T2 accuracy given correct T1 (T2|T1) overall and by lag, both-correct
    rate. hit = both targets reported, with a valid presentation, in at least half of the
    streams."""
    a = G.Audit(CEILING_MS)
    streams = item["streams"]
    if not isinstance(response, list):
        return a.junk(2 * len(streams))
    rows = []
    for k, (st, r) in enumerate(zip(streams, a.entries(response, len(streams), "streams"))):
        d = a.obj(r, "stream")
        if d is None:
            a.record(G.INVALID)
            rows.append({"lag": st["lag"], "t1": False, "t2": False, "flag": False, "valid": False})
            continue
        said = {_letter(d.get("r1", G.MISSING), a, "r1"), _letter(d.get("r2", G.MISSING), a, "r2")} - {None}
        status, late = a.time(d.get("late", G.MISSING), field="late", window=SOA_MS, floor=0, required=True)
        a.record(status)
        valid = status == G.TIMELY
        if status == G.LATE:
            a.invalid_events += 1           # a skipped letter slot: the presentation is invalid
        flag = late is not None and late > DRIFT_FLAG_MS
        if flag and valid:
            a.flag("timing_drift")
        x, y = st["letters"][st["t1"]], st["letters"][st["t2"]]
        rows.append({"lag": st["lag"], "t1": valid and x in said, "t2": valid and y in said,
                     "flag": flag or not valid, "valid": valid})
    n = len(rows)
    t1_ok = [r for r in rows if r["t1"]]
    by_lag = defaultdict(list)
    for r in t1_ok:
        by_lag[r["lag"]].append(r["t2"])
    both = sum(r["t1"] and r["t2"] for r in rows)
    return a.finish(n > 0 and both / n >= 0.5,
                    sum((not r["t1"]) + (not r["t2"]) for r in rows),
                    {"t1_accuracy": round(len(t1_ok) / n, 3) if n else None,
                     "t2_given_t1": round(sum(r["t2"] for r in t1_ok) / len(t1_ok), 3) if t1_ok else None,
                     "t2_given_t1_by_lag": {str(l): round(sum(v) / len(v), 3) for l, v in sorted(by_lag.items())},
                     "n_t1_correct_by_lag": {str(l): len(v) for l, v in sorted(by_lag.items())},
                     "both_correct": both, "streams": n,
                     "timing_flagged_streams": sum(r["flag"] for r in rows),
                     "invalid_presentation_streams": sum(not r["valid"] for r in rows)})


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
