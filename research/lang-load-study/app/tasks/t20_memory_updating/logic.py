"""Memory updating (card 20): two to four labelled boxes start with numbers (shown for
4 s, then hidden). Spoken-style instructions such as "Add 3 to box B" or "Subtract 2
from box A" appear one at a time (3 s each); at the end the person types the final
value of every box.

The instruction wording lives in text/<lang>.json ("op_add", "op_sub" with {n} and
{b}); items only hold language-neutral numbers. Pairs (k, k+1) share the box count,
update count and the add/subtract sequence; values, boxes and amounts differ. Values
stay within 0..20 (never negative). The answer key comes from the simulator below."""

from app.tasks import _guard as G

TIMING = "untimed"   # view.js answer phase has no time limit; rt is descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)
LIMIT = 20
MAX_VALUE = 99       # the answer inputs take at most 2 digits (view.js maxLength = 2)
PLAN = {2: 5, 3: 6, 4: 8}   # boxes -> updates per trial


def simulate(start, updates):
    """Reference simulator: apply each update in order; returns the final values."""
    vals = list(start)
    for u in updates:
        vals[u["box"]] += u["n"] if u["op"] == "add" else -u["n"]
    return vals


def _trial(rng, boxes, ops):
    while True:
        start = [rng.randint(1, 9) for _ in range(boxes)]
        vals, ups, ok = list(start), [], True
        for op in ops:
            if op == "add":
                cand = [b for b in range(boxes) if vals[b] <= LIMIT - 1]
            else:
                cand = [b for b in range(boxes) if vals[b] >= 1]
            if not cand:
                ok = False
                break
            b = rng.choice(cand)
            room = LIMIT - vals[b] if op == "add" else vals[b]
            n = rng.randint(1, min(5, room))
            vals[b] += n if op == "add" else -n
            ups.append({"op": op, "n": n, "box": b})
        if ok and len({u["box"] for u in ups}) == boxes and simulate(start, ups) == vals \
                and all(0 <= v <= LIMIT for v in vals):
            return {"boxes": boxes, "start": start, "updates": ups}


def generate(rng, n, save_image):
    items = []
    for k in range(n):
        if k % 2 == 0:
            boxes = [2, 3, 4][(k // 2) % 3]
            n_up = PLAN[boxes]
            n_sub = rng.randint(n_up // 3, n_up // 2)
            ops = ["sub"] * n_sub + ["add"] * (n_up - n_sub)
            rng.shuffle(ops)
        items.append(_trial(rng, boxes, ops))
    return items


@G.safe
def score(item, response):
    """response: {"values": [final value typed per box, int 0..99 or null], "rt": ms (recall
    time, answer screen to Done)}. One value per box: missing entries are omissions and
    extra ones are ignored (both flagged); a value that is not an integer 0..99 (the input
    takes at most 2 digits; strings, floats and booleans are not coerced) is flagged and
    scored wrong. The key comes from simulate().
    hit = every box's final value is exactly right.
    errors = number of boxes wrong or left empty.
    Recall is unspeeded: rt is descriptive, checked (finite, >= 100 ms, below the trial
    timeout) and null when bad (flagged); correctness stands."""
    truth = simulate(item["start"], item["updates"])
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(len(truth))
    got = []
    for v in a.entries(response.get("values", G.MISSING), len(truth), "values"):
        if v is G.MISSING or v is None:
            got.append(None)
        elif G.member(v, range(MAX_VALUE + 1)):
            got.append(v)
        else:
            a.malformed("invalid_value")
            got.append(None)
    ok = [g is not None and g == t for g, t in zip(got, truth)]
    per_box_updates = [sum(1 for u in item["updates"] if u["box"] == b) for b in range(len(truth))]
    rt = a.duration(response, "rt")
    return a.finish(all(ok), len(ok) - sum(ok), {
        "boxes": len(truth), "updates": len(item["updates"]),
        "subtractions": sum(1 for u in item["updates"] if u["op"] == "sub"),
        "box_accuracy": round(sum(ok) / len(ok), 3), "boxes_correct": sum(ok),
        "correct_by_box": ok, "updates_by_box": per_box_updates,
        "omissions": sum(1 for g in got if g is None),
        "recall_rt": rt})


def example_response(item, correct=True):
    truth = simulate(item["start"], item["updates"])
    vals = truth if correct else [v + 1 for v in truth]
    return {"values": vals, "rt": 5000}
