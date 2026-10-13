"""Memory updating (card 20): two to four labelled boxes start with numbers (shown for
4 s, then hidden). Spoken-style instructions such as "Add 3 to box B" or "Subtract 2
from box A" appear one at a time (3 s each); at the end the person types the final
value of every box.

The instruction wording lives in text/<lang>.json ("op_add", "op_sub" with {n} and
{b}); items only hold language-neutral numbers. Pairs (k, k+1) share the box count,
update count and the add/subtract sequence; values, boxes and amounts differ. Values
stay within 0..20 (never negative). The answer key comes from the simulator below."""

LIMIT = 20
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


def _int(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, str) and x.strip().isdigit() and x.strip().isascii():
        return int(x.strip())
    return None


def score(item, response):
    """response: {"values": [final value typed per box, int or null], "rt": ms (recall time)}.
    hit = every box's final value is exactly right.
    errors = number of boxes wrong or left empty."""
    truth = simulate(item["start"], item["updates"])
    resp = response if isinstance(response, dict) else {}
    vals = resp.get("values") if isinstance(resp.get("values"), list) else []
    got = [_int(vals[b]) if b < len(vals) else None for b in range(len(truth))]
    ok = [g == t for g, t in zip(got, truth)]
    per_box_updates = [sum(1 for u in item["updates"] if u["box"] == b) for b in range(len(truth))]
    rt = resp.get("rt")
    return {"hit": all(ok), "errors": len(ok) - sum(ok),
            "metrics": {"boxes": len(truth), "updates": len(item["updates"]),
                        "subtractions": sum(1 for u in item["updates"] if u["op"] == "sub"),
                        "box_accuracy": round(sum(ok) / len(ok), 3), "boxes_correct": sum(ok),
                        "correct_by_box": ok, "updates_by_box": per_box_updates,
                        "omissions": sum(1 for g in got if g is None),
                        "recall_rt": rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) else None}}


def example_response(item, correct=True):
    truth = simulate(item["start"], item["updates"])
    vals = truth if correct else [v + 1 for v in truth]
    return {"values": vals, "rt": 5000}
