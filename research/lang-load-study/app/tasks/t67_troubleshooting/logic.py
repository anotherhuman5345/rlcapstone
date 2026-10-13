"""Troubleshooting (card 67), adapted to one trial with two faults in one novel machine.

The machine is a small tree of 6 parts fed by a power source; every branch end drives a
lamp. Rule (taught in the instructions): a broken part passes no signal, so every part
after it and every lamp it feeds goes dark. Each case shows which lamps are lit (the
symptom). The participant may test any part (cost 1 each; the test shows whether signal
comes OUT of that part) and then reports the broken part. Two cases per trial, both
with a fault that the lamps alone cannot pin down (2+ candidate parts), so tests are needed.

A causal simulator (signal_out) produces lamps and test results; the server replays the
participant's tests with it. Part names come from text "parts" by index.
Pairs (k, k+1) use the same tree and the same fault positions, drawn mirrored and with
different part names.
"""
from functools import lru_cache

N_PARTS = 6
N_NAMES = 12   # length of text "parts"


def _children(parent):
    ch = {i: [] for i in range(-1, len(parent))}
    for i, p in enumerate(parent):
        ch[p].append(i)
    return ch


def _leafset(parent, v):
    ch = _children(parent)
    out, stack = set(), [v]
    while stack:
        u = stack.pop()
        if ch[u]:
            stack.extend(ch[u])
        else:
            out.add(u)
    return frozenset(out)


def _upstream(parent, u):
    """u and every part between u and the source."""
    out = []
    while u != -1:
        out.append(u)
        u = parent[u]
    return out


def signal_out(parent, fault, u):
    """Causal simulator: is there signal at the output of part u when `fault` is broken?"""
    return fault not in _upstream(parent, u)


def lamps_lit(parent, fault):
    leaves = sorted(_leafset(parent, -1))
    return [signal_out(parent, fault, v) for v in leaves]


def consistent(parent, lit, tests):
    """Parts that could be broken given the lamp pattern and (part, result) test outcomes."""
    return [f for f in range(len(parent))
            if lamps_lit(parent, f) == lit and all(signal_out(parent, f, u) == r for u, r in tests)]


def optimal_tests(parent, cands):
    """Fewest tests that always isolate the fault among cands (minimax over test outcomes)."""
    parent = tuple(parent)

    @lru_cache(maxsize=None)
    def need(cs):
        if len(cs) <= 1:
            return 0
        best = None
        for u in range(len(parent)):
            yes = frozenset(f for f in cs if signal_out(parent, f, u))
            if 0 < len(yes) < len(cs):
                v = 1 + max(need(yes), need(cs - yes))
                best = v if best is None else min(best, v)
        return best if best is not None else 0
    return need(frozenset(cands))


def _depth(parent, v):
    return len(_upstream(parent, v))


def _layout(parent, mirror):
    ch = _children(parent)
    order = {k: (v[::-1] if mirror else v) for k, v in ch.items()}
    ys, leaves = {}, []

    def walk(u):
        if not order[u]:
            leaves.append(u)
            ys[u] = len(leaves) - 1
            return
        for c in order[u]:
            walk(c)
        ys[u] = sum(ys[c] for c in order[u]) / len(order[u])
    for r in order[-1]:
        walk(r)
    nl, dmax = len(leaves), max(_depth(parent, v) for v in range(len(parent)))
    x = [round(0.04 + _depth(parent, v) / (dmax + 1.6), 3) for v in range(len(parent))]
    y = [round((ys[v] + 0.5) / nl, 3) for v in range(len(parent))]
    return x, y, leaves


def _tree(rng):
    while True:
        parent = [-1] + [rng.choice([-1] + list(range(i)) + [i - 1, i - 1]) for i in range(1, N_PARTS)]
        ch = _children(parent)
        leaves = [v for v in range(N_PARTS) if not ch[v]]
        if not 2 <= len(leaves) <= 3 or len(ch[-1]) > 2:
            continue
        if max(_depth(parent, v) for v in range(N_PARTS)) > 4:
            continue
        groups = {}
        for v in range(N_PARTS):
            groups.setdefault(_leafset(parent, v), []).append(v)
        groups = sorted((g for g in groups.values() if len(g) >= 2), key=len, reverse=True)
        if len(groups) >= 2 and len(groups[0]) >= 3:
            return parent, groups


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        parent, groups = _tree(rng)
        # one fault among 3+ look-alike parts, one from another look-alike group
        faults = [rng.choice(groups[0]), rng.choice(rng.choice(groups[1:]))]
        rng.shuffle(faults)
        for m in range(2):
            x, y, leaves = _layout(parent, mirror=(m == 1))
            items.append({"parent": parent, "x": x, "y": y, "lamps": leaves,
                          "names": rng.sample(range(N_NAMES), N_PARTS),
                          "faults": faults, "limit_ms": 170000})
    return items[:n]


def score(item, response):
    """response: {"cases": [{"tests": [part, ...], "diagnosis": part or null, "t": ms}, ...]}
    (one per fault, in order). The server replays each test on the simulator.
    Metrics: diagnosis accuracy, tests used, excess tests over the minimax optimum,
    guesses (diagnosis made while more than one part was still consistent with the
    evidence seen), time.
    hit = both broken parts identified correctly."""
    miss = {"hit": False, "errors": 2, "metrics": {}}
    if not isinstance(response, dict) or not isinstance(response.get("cases"), list):
        return miss
    parent = item["parent"]
    n = len(parent)
    correct, tests_used, excess, guesses, times = 0, 0, 0, 0, []
    for k, fault in enumerate(item["faults"]):
        r = response["cases"][k] if k < len(response["cases"]) and isinstance(response["cases"][k], dict) else {}
        tests = [u for u in (r.get("tests") if isinstance(r.get("tests"), list) else [])
                 if isinstance(u, int) and not isinstance(u, bool) and 0 <= u < n]
        d = r.get("diagnosis")
        lit = lamps_lit(parent, fault)
        evidence = [(u, signal_out(parent, fault, u)) for u in tests]
        left = consistent(parent, lit, evidence)
        ok = isinstance(d, int) and not isinstance(d, bool) and d == fault
        correct += ok
        tests_used += len(tests)
        excess += len(tests) - optimal_tests(parent, consistent(parent, lit, []))
        guesses += len(left) > 1
        t = r.get("t")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            times.append(t)
    return {"hit": correct == len(item["faults"]),
            "errors": len(item["faults"]) - correct,
            "metrics": {"diagnosis_correct": correct, "diagnosis_accuracy": correct / len(item["faults"]),
                        "tests_used": tests_used, "excess_tests": excess, "guesses": guesses,
                        "mean_case_ms": round(sum(times) / len(times), 1) if times else None}}


def example_response(item, correct=True):
    cases = []
    for fault in item["faults"]:
        parent = item["parent"]
        cands = consistent(parent, lamps_lit(parent, fault), [])
        d = fault if correct else next(c for c in cands if c != fault)
        cases.append({"tests": cands, "diagnosis": d, "t": 20000})
    return {"cases": cases}
