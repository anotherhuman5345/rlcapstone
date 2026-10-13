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

import functools
import json
import math

from app.tasks import _guard as G

TIMING = "limit"        # the Done press (rt) must come inside LIMIT_MS
LIMIT_MS = 100000       # view.js: timer = setTimeout(() => end(true), 100000)
CEILING_MS = G.trial_ceiling(__file__)
MAX_ORDER = 100
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


@functools.lru_cache(maxsize=256)
def _optimum_cached(key):
    """optimum() for one map, memoized on a JSON key (depot, stops)."""
    depot, stops = json.loads(key)
    return optimum({"depot": depot, "stops": stops})


@G.safe
def score(item, response):
    """response: {"order": [stop index, ...] in visiting order (0-based), "undos": int,
    "plan_ms": ms from Start to first stop, "rt": ms from Start to Done}.
    hit = the route visits every stop exactly once (no constraint violations), its cost
    is at most 5% above the exact optimum AND the route was sent with a valid rt inside the
    100 s limit (a missing, non-finite, negative or late time never counts). Unknown or
    repeated stops (the browser cannot send them) are flagged. Metrics: route cost, optimal
    cost, ratio to optimum, optimal (cost equals the optimum: tied optima all count),
    violations (missing + repeated + unknown stops), undos, planning and total time."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    n = len(item["stops"])
    order = a.stream(response.get("order", G.MISSING), "order", cap=MAX_ORDER)
    valid = [i for i in order if G.member(i, range(n))]
    unknown = len(order) - len(valid)
    repeats = len(valid) - len(set(valid))
    missing = n - len(set(valid))
    if unknown:
        a.malformed("unknown_stop")
    if repeats:
        a.malformed("repeated_stop")
    violations = unknown + repeats + missing
    opt = _optimum_cached(json.dumps([item["depot"], item["stops"]]))
    cost = route_cost(item, valid) if violations == 0 else None
    ratio = round(cost / opt, 4) if cost is not None else None
    good = cost is not None and cost <= (1 + TOLERANCE) * opt
    st, rt = a.time(response.get("rt"), field="rt", window=LIMIT_MS, required=True)
    if good and st != G.TIMELY:
        a.flag("solved_outside_time_limit")
    hit = good and st == G.TIMELY
    plan = a.duration(response, "plan_ms", window=LIMIT_MS)
    return a.finish(hit, violations + (0 if hit else 1), {
        "route_cost": cost, "optimal_cost": opt, "ratio_to_optimum": ratio,
        "optimal": cost == opt, "n_stops": n, "violations": violations,
        "missing": missing, "repeats": repeats, "undos": a.opt_int(response, "undos"),
        "plan_ms": plan, "rt": rt, "rt_status": st})


def example_response(item, correct=True):
    order = _best_order(item)
    if not correct:
        order = order[:-1]  # leaves one stop out
    return {"order": order, "undos": 0, "plan_ms": 4000, "rt": 15000}
