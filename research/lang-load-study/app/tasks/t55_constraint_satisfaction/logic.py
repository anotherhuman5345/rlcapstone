"""Constraint satisfaction (card 55): put 4 or 5 animals into a row of numbered places so
that every sentence is true. The sentences are verbal templates in text/<lang>.json
("templates"), filled with animal names from the same file ("objects"); items hold only
template types and indices, so every language shows equivalent content.
The generator picks a hidden arrangement, adds true constraints at random while they
still cut down the set of arrangements, stops at exactly one solution and then drops any
constraint that became redundant (so there are no contradictions and none is spare).
Pairs (k, k+1) have the same number of animals, the same multiset of constraint types
and one solution each; pairs alternate 4 animals (3-4 sentences) and 5 animals (4-6).
score() checks the submitted row against every constraint itself, so any valid
arrangement is accepted."""
from itertools import permutations

N_OBJECTS = 8          # animals in text/<lang>.json "objects"
LIMIT_MS = 90000
LEVELS = ((4, 3, 4), (5, 4, 6))   # (animals, min sentences, max sentences)
TYPES = ("left_of", "next_left", "adjacent", "not_adjacent", "at", "not_at", "end", "not_end", "between")


def holds(con, pos, n):
    """pos[i] = 0-based place of item object i."""
    t, a = con["type"], pos[con["a"]]
    if t == "left_of":
        return a < pos[con["b"]]
    if t == "next_left":
        return a == pos[con["b"]] - 1
    if t == "adjacent":
        return abs(a - pos[con["b"]]) == 1
    if t == "not_adjacent":
        return abs(a - pos[con["b"]]) != 1
    if t == "at":
        return a == con["p"] - 1
    if t == "not_at":
        return a != con["p"] - 1
    if t == "end":
        return a in (0, n - 1)
    if t == "not_end":
        return a not in (0, n - 1)
    if t == "between":
        b, c = pos[con["b"]], pos[con["c"]]
        return min(b, c) < a < max(b, c)
    raise ValueError(t)


def solutions(n, cons):
    """Every arrangement (as pos tuples) that satisfies all constraints."""
    return [pos for pos in permutations(range(n)) if all(holds(c, pos, n) for c in cons)]


def _candidates(n, pos):
    out = []
    for a in range(n):
        out += [{"type": "end", "a": a}, {"type": "not_end", "a": a}]
        out += [{"type": t, "a": a, "p": p} for t in ("at", "not_at") for p in range(1, n + 1)]
        for b in range(n):
            if b == a:
                continue
            out += [{"type": t, "a": a, "b": b} for t in ("left_of", "next_left")]
            if a < b:
                out += [{"type": t, "a": a, "b": b} for t in ("adjacent", "not_adjacent")]
            for c in range(b + 1, n):
                if c != a:
                    out.append({"type": "between", "a": a, "b": b, "c": c})
    return [c for c in out if holds(c, pos, n)]


def _prune(n, cons):
    cons = list(cons)
    changed = True
    while changed:
        changed = False
        for k in range(len(cons)):
            rest = cons[:k] + cons[k + 1:]
            if len(solutions(n, rest)) == 1:
                cons, changed = rest, True
                break
    return cons


def _first(rng, n, lo, hi):
    while True:
        target = list(range(n))
        rng.shuffle(target)
        pos = tuple(target)
        cands = _candidates(n, pos)
        rng.shuffle(cands)
        cons, sols = [], len(list(permutations(range(n))))
        for c in cands:
            if sum(1 for x in cons if x["type"] == "at") and c["type"] == "at":
                continue  # at most one "is in place p": keeps the puzzle from being a lookup
            k = len(solutions(n, cons + [c]))
            if k < sols:
                cons, sols = cons + [c], k
            if sols == 1:
                break
        cons = _prune(n, cons)
        if sols == 1 and lo <= len(cons) <= hi:
            return cons


def _partner(rng, n, types):
    for _ in range(3000):
        target = list(range(n))
        rng.shuffle(target)
        pos = tuple(target)
        cands = _candidates(n, pos)
        cons = []
        for t in types:
            opts = [c for c in cands if c["type"] == t and c not in cons]
            if not opts:
                break
            cons.append(rng.choice(opts))
        if len(cons) == len(types) and len(solutions(n, cons)) == 1 and len(_prune(n, cons)) == len(cons):
            return cons
    return None


def generate(rng, n_items, save_image):
    items = []
    while len(items) < n_items:
        n, lo, hi = LEVELS[(len(items) // 2) % len(LEVELS)]
        a = _first(rng, n, lo, hi)
        b = _partner(rng, n, sorted(c["type"] for c in a))
        if b is None:
            continue
        for cons in (a, b):
            rng.shuffle(cons)
            objs = rng.sample(range(N_OBJECTS), n)
            items.append({"n": n, "objects": objs, "constraints": cons, "n_solutions": 1, "limit_ms": LIMIT_MS})
    return items[:n_items]


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def score(item, response):
    """response: {"order": [object index at place 1, place 2, ...], "changes", "first_move_ms",
    "rt_ms", "gave_up"}; object indices refer to item["objects"] (0..n-1).
    hit = the order is a complete arrangement (each object exactly once) and every
    constraint holds; any arrangement that satisfies all constraints counts, not only the
    generator's. errors = number of violated constraints (all of them if the order is
    incomplete or invalid). Metrics: violations, solver solution count, changes, times."""
    miss = {"hit": False, "errors": 0, "metrics": {}}
    try:
        if not isinstance(response, dict):
            return miss
        n, cons = item["n"], item["constraints"]
        order = response.get("order")
        valid = (isinstance(order, list) and len(order) == n
                 and all(isinstance(o, int) and not isinstance(o, bool) for o in order)
                 and sorted(order) == list(range(n)))
        if valid:
            pos = [0] * n
            for place, o in enumerate(order):
                pos[o] = place
            violated = sum(1 for c in cons if not holds(c, pos, n))
        else:
            violated = len(cons)
        hit = valid and violated == 0
        return {"hit": hit, "errors": violated,
                "metrics": {"complete": valid, "violations": violated, "constraints": len(cons),
                            "objects": n, "n_solutions": len(solutions(n, cons)),
                            "changes": response.get("changes") if isinstance(response.get("changes"), int) else None,
                            "first_move_ms": _num(response.get("first_move_ms")),
                            "rt_ms": _num(response.get("rt_ms")), "gave_up": response.get("gave_up") is True}}
    except Exception:
        return miss


def example_response(item, correct=True):
    pos = solutions(item["n"], item["constraints"])[0]
    order = [0] * item["n"]
    for o, place in enumerate(pos):
        order[place] = o
    if not correct:
        order = order[::-1]  # the solution is unique, so the mirrored row is wrong
    return {"order": order, "changes": item["n"], "first_move_ms": 5000, "rt_ms": 40000, "gave_up": False}
