"""Route optimization (card 39): a map shows a depot and 5-8 numbered stops. Plan the
shortest round trip that leaves the depot, visits every stop exactly once, and returns to
the depot; click/tap the stops (or type their numbers) in visiting order. One trial = one
map.

Cost rule (explicit configuration): symmetric costs; the cost of a leg is the straight-
line distance on a 1000 x 1000 map rounded to a whole unit, and the route cost is the sum
of its legs including the way back to the depot. Because costs are integers, ties are
exact: every route whose cost equals the optimum (including the same loop driven the
other way) counts as optimal.

The optimum is computed exactly (Held-Karp dynamic programming over all subsets; at most
8 stops) inside score(), never taken from the browser. Stop count cycles 5, 6, 7, 8
across pairs; both items of a pair have the same number of stops."""

import math

COUNTS = (5, 6, 7, 8)
TOLERANCE = 0.05


def _points(item):
    return [tuple(item["depot"])] + [tuple(p) for p in item["stops"]]


def leg(a, b):
    return int(round(math.hypot(a[0] - b[0], a[1] - b[1])))


def route_cost(item, order):
    pts = _points(item)
    path = [0] + [i + 1 for i in order] + [0]
    return sum(leg(pts[a], pts[b]) for a, b in zip(path, path[1:]))


def optimum(item):
    """Exact shortest round-trip cost from the depot through all stops (Held-Karp)."""
    pts = _points(item)
    n = len(pts) - 1
    d = [[leg(p, q) for q in pts] for p in pts]
    best = {(1 << j, j): d[0][j + 1] for j in range(n)}
    for mask in range(1, 1 << n):
        for j in range(n):
            if not mask & (1 << j) or (mask, j) not in best:
                continue
            for k in range(n):
                if mask & (1 << k):
                    continue
                key = (mask | (1 << k), k)
                val = best[(mask, j)] + d[j + 1][k + 1]
                if val < best.get(key, float("inf")):
                    best[key] = val
    full = (1 << n) - 1
    return min(best[(full, j)] + d[j + 1][0] for j in range(n))


def _best_order(item):
    import itertools
    n = len(item["stops"])
    opt = optimum(item)
    for perm in itertools.permutations(range(n)):
        if route_cost(item, list(perm)) == opt:
            return list(perm)


def _map(rng, n):
    while True:
        pts = []
        tries = 0
        while len(pts) < n + 1 and tries < 2000:
            tries += 1
            p = (rng.randint(60, 940), rng.randint(60, 940))
            if all(math.dist(p, q) >= 110 for q in pts):
                pts.append(p)
        if len(pts) == n + 1:
            return {"depot": list(pts[0]), "stops": [list(p) for p in pts[1:]]}


def generate(rng, n, save_image):
    return [_map(rng, COUNTS[(k // 2) % len(COUNTS)]) for k in range(n)]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def score(item, response):
    """response: {"order": [stop index, ...] in visiting order (0-based), "undos": int,
    "plan_ms": ms from Start to first stop, "rt": ms from Start to Done}.
    hit = the route visits every stop exactly once (no constraint violations) and its cost
    is at most 5% above the exact optimum. Metrics: route cost, optimal cost, ratio to
    optimum, optimal (cost equals the optimum: tied optima all count), violations
    (missing + repeated + unknown stops), undos, planning and total time."""
    n = len(item["stops"])
    order = response.get("order") if isinstance(response, dict) else None
    order = order if isinstance(order, list) else []
    valid = [i for i in order if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n]
    unknown = len(order) - len(valid)
    repeats = len(valid) - len(set(valid))
    missing = n - len(set(valid))
    violations = unknown + repeats + missing
    opt = optimum(item)
    cost = route_cost(item, valid) if violations == 0 else None
    ratio = round(cost / opt, 4) if cost is not None else None
    hit = cost is not None and cost <= (1 + TOLERANCE) * opt
    r = response if isinstance(response, dict) else {}
    return {"hit": hit, "errors": violations + (0 if hit else 1),
            "metrics": {"route_cost": cost, "optimal_cost": opt, "ratio_to_optimum": ratio,
                        "optimal": cost == opt, "n_stops": n, "violations": violations,
                        "missing": missing, "repeats": repeats, "undos": _num(r.get("undos")),
                        "plan_ms": _num(r.get("plan_ms")), "rt": _num(r.get("rt"))}}


def example_response(item, correct=True):
    order = _best_order(item)
    if not correct:
        order = order[:-1]  # leaves one stop out
    return {"order": order, "undos": 0, "plan_ms": 4000, "rt": 15000}
