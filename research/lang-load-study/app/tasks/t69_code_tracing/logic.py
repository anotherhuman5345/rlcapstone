"""Code tracing (card 69), adapted to one short trial.

One trial = 3 short pseudocode programs; for each, type the number it prints. Programs
are stored as a language-neutral syntax tree; view.js renders the keywords from the text
file ("set x to ...", "repeat 3 times:", "if ...:", "otherwise:", "print ...") so each
language reads naturally, while variables, numbers and operators (+ - x > <) stay the same.
Levels: program 1 = one if/otherwise, program 2 = one loop, program 3 = a loop with an
if/otherwise nested inside (two levels). The answer key comes from `run()`, a reference
interpreter, not from the generator. The two items of a pair use the same three program
shapes with different numbers (results kept in a similar range).
Prior programming experience is not measured here; collect it in the questionnaire.
"""

from app.tasks import _guard as G

TIMING = "limit"      # each program must be answered within its limit (see _guard.py)
LIMIT_MS = 45000      # view.js ask(): setTimeout(() => done(null), it.limit_ms), per program
TIME_SLACK_MS = 1000  # timer tolerance at the limit
MAX_ENTRIES = 100     # entries read from the response list (3 expected)
ANSWERS = range(-9999, 10000)  # the keypad allows a sign and at most 4 digits
CEILING_MS = G.trial_ceiling(__file__)


def _ev(e, env):
    if isinstance(e, bool):
        raise ValueError("bad expression")
    if isinstance(e, int):
        return e
    if isinstance(e, str):
        return env[e]
    op, a, b = e
    a, b = _ev(a, env), _ev(b, env)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    raise ValueError(op)


def _exec(stmts, env, out):
    for s in stmts:
        op = s["op"]
        if op == "set":
            env[s["v"]] = _ev(s["e"], env)
        elif op == "print":
            out.append(_ev(s["e"], env))
        elif op == "repeat":
            for _ in range(s["n"]):
                _exec(s["body"], env, out)
        elif op == "if":
            _exec(s["then"] if _ev(s["c"], env) else (s.get("else") or []), env, out)
        else:
            raise ValueError(op)


def run(program):
    """Reference interpreter: returns the list of printed values."""
    env, out = {}, []
    _exec(program, env, out)
    return out


def _set(v, e):
    return {"op": "set", "v": v, "e": e}


def _if_else(rng):
    while True:
        a, b, c = rng.randint(3, 9), rng.randint(2, 9), rng.randint(2, 6)
        if a == b:
            continue
        prog = [_set("x", a), _set("y", b),
                {"op": "if", "c": [">", "x", "y"],
                 "then": [_set("x", ["-", "x", "y"])],
                 "else": [_set("x", ["+", "x", c])]},
                {"op": "print", "e": ["*", "x", 2]}]
        return prog


def _loop(rng):
    a, b, n = rng.randint(1, 5), rng.randint(2, 4), rng.randint(3, 4)
    return [_set("x", a), _set("y", b),
            {"op": "repeat", "n": n, "body": [_set("x", ["+", "x", "y"]), _set("y", ["+", "y", 1])]},
            {"op": "print", "e": "x"}]


def _nested(rng):
    while True:
        a, b, n, t = rng.randint(0, 3), rng.randint(2, 4), rng.randint(3, 4), rng.randint(5, 8)
        prog = [_set("x", a), _set("y", b),
                {"op": "repeat", "n": n, "body": [
                    _set("x", ["+", "x", "y"]),
                    {"op": "if", "c": [">", "x", t],
                     "then": [_set("x", ["-", "x", t])],
                     "else": [_set("y", ["+", "y", 1])]}]},
                {"op": "print", "e": "x"}]
        # both branches must be taken at least once, so the condition really matters
        env, taken = {"x": a, "y": b}, set()
        for _ in range(n):
            env["x"] += env["y"]
            if env["x"] > t:
                env["x"] -= t
                taken.add(1)
            else:
                env["y"] += 1
                taken.add(0)
        if taken == {0, 1}:
            return prog


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        for _ in range(2):
            items.append({"programs": [_if_else(rng), _loop(rng), _nested(rng)],
                          "levels": [1, 1, 2], "limit_ms": LIMIT_MS})
    return items[:n]


def _by_index(seq, n, a, key="p"):
    """Entries keyed by program index: {index: entry}. The first entry for an index wins;
    later duplicates (duplicate_p), unknown / non-integer indices (invalid_p), entries that
    are not objects and entries out of presentation order are flagged; an index with no
    entry is flagged missing_p (and is an invalid event, scored as an omission)."""
    by, last = {}, -1
    for r in seq:
        if not isinstance(r, dict):
            a.malformed("event_not_object")
            continue
        k = r.get(key, G.MISSING)
        if not G.is_int(k) or not 0 <= k < n:
            a.malformed(f"invalid_{key}" if k is not G.MISSING else f"missing_{key}")
            continue
        if k in by:
            a.malformed(f"duplicate_{key}")
            continue
        if k < last:
            a.flag(f"out_of_order_{key}")
        last = k
        by[k] = r
    missing = n - len(by)
    if missing:
        a.flag(f"missing_{key}", missing)
    return by


@G.safe
def score(item, response):
    """response: [{"p": program index, "answer": integer or null, "rt": ms}] in program
    order, one entry per program (the first entry for an index counts; duplicate, unknown
    and missing indices are flagged). answer null with rt null = the 45 s limit ran out.
    An answer counts only when it is an integer (-9999..9999, what the keypad allows) and
    its rt is a valid time inside the per-program limit (finite, >= 100 ms, <= LIMIT_MS +
    1 s timer slack, see view.js); otherwise it is never correct (flagged).
    hit = at least 2 of the 3 printed values right in time (omissions wrong).
    metrics: accuracy, accuracy for one-level and two-level programs, mean correct RT,
    omissions, per-program events. Keys come from run()."""
    a = G.Audit(CEILING_MS)
    progs, levels = item["programs"], item["levels"]
    if not isinstance(response, list):
        return a.junk(len(progs))
    by_p = _by_index(a.stream(response, "events", cap=MAX_ENTRIES), len(progs), a)
    ok, rts, omis, events = [], [], 0, []
    lv = {1: [], 2: []}
    for k, prog in enumerate(progs):
        key = run(prog)[-1]
        r = by_p.get(k)
        if r is None:
            status, ans, rt = a.record(G.INVALID), None, None
        else:
            status, ans, rt = a.keyed(r, ANSWERS, key="answer", rt="rt", window=LIMIT_MS, slack=TIME_SLACK_MS)
        if ans is None:
            omis += 1
        good = status == G.TIMELY and ans == key
        ok.append(good)
        lv.setdefault(levels[k], []).append(good)
        if good:
            rts.append(rt)
        events.append({"i": k, "level": levels[k], "status": status, "correct": good,
                       "rt": rt if status == G.TIMELY else None})

    def acc(v):
        return round(sum(v) / len(v), 3) if v else None
    return a.finish(sum(ok) >= 2, len(progs) - sum(ok), {
        "accuracy": acc(ok), "acc_level1": acc(lv[1]), "acc_level2": acc(lv[2]),
        "mean_rt_correct": G.mean(rts), "omissions": omis, "events": events})


def example_response(item, correct=True):
    return [{"p": k, "answer": run(p)[-1] + (0 if correct else 1), "rt": 15000}
            for k, p in enumerate(item["programs"])]
