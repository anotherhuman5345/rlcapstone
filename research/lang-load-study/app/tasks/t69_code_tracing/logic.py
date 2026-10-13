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

LIMIT_MS = 45000


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


def score(item, response):
    """response: [{"p": program index, "answer": integer or null, "rt": ms}].
    hit = at least 2 of the 3 printed values right (omissions wrong).
    metrics: accuracy, accuracy for one-level and two-level programs, mean correct RT,
    omissions. Keys come from run()."""
    try:
        progs, levels = item["programs"], item["levels"]
        resp = response if isinstance(response, list) else []
        by_p = {}
        for r in resp:
            if isinstance(r, dict) and isinstance(r.get("p"), int) and r["p"] not in by_p:
                by_p[r["p"]] = r
        ok, rts, omis = [], [], 0
        lv = {1: [], 2: []}
        for k, prog in enumerate(progs):
            key = run(prog)[-1]
            r = by_p.get(k, {})
            ans = r.get("answer")
            if ans is None:
                omis += 1
            good = isinstance(ans, int) and not isinstance(ans, bool) and ans == key
            ok.append(good)
            lv.setdefault(levels[k], []).append(good)
            rt = r.get("rt")
            if good and isinstance(rt, (int, float)) and rt > 0:
                rts.append(rt)

        def acc(v):
            return round(sum(v) / len(v), 3) if v else None
        return {"hit": sum(ok) >= 2, "errors": len(progs) - sum(ok),
                "metrics": {"accuracy": acc(ok), "acc_level1": acc(lv[1]), "acc_level2": acc(lv[2]),
                            "mean_rt_correct": round(sum(rts) / len(rts), 1) if rts else None,
                            "omissions": omis}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    return [{"p": k, "answer": run(p)[-1] + (0 if correct else 1), "rt": 15000}
            for k, p in enumerate(item["programs"])]
