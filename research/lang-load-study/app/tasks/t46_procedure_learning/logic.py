"""Procedure learning (card 46), adapted to one short trial.

An abstract machine is operated by a 6-step procedure written in words (text file):
3 fixed steps ("Press OPEN."), 2 conditional steps ("If the lamp is red, press HEAT;
otherwise press COOL.") and 1 counted step ("Press STIR as many times as the number on
the display."). Guided phase: the steps plus one worked example (a case and its correct
button presses) can be studied for up to STUDY_MS. Unguided phase: the steps disappear
and the participant operates the machine for 3 new cases (lamp colour + number).

The procedure is a state machine (`Machine`); score() runs it to get the correct press
sequence for every case. The two items of a pair have the same step-type order and the
same test cases (so the same answer lengths and branching), but distinct button labels
and condition colours.
"""

N_ACTIONS = 16  # length of "actions" in the text files
N_COLORS = 2    # length of "colors"
STUDY_MS = 45000
CASE_MS = 40000  # a case is submitted as it stands after this long
TYPES = ["fixed", "fixed", "fixed", "cond", "cond", "repeat"]


class Machine:
    """States are (step index, presses still owed in a counted step)."""

    def __init__(self, steps, case):
        self.steps, self.case = steps, case
        self.i, self.left = 0, None

    def expected(self):
        if self.i >= len(self.steps):
            return None
        st = self.steps[self.i]
        if st["t"] == "fixed" or st["t"] == "repeat":
            return st["a"]
        return st["a"] if self.case["lamp"] == st["color"] else st["b"]

    def press(self, action):
        """Advance on the correct action; return False (no change) on a wrong one."""
        if action != self.expected():
            return False
        st = self.steps[self.i]
        if st["t"] == "repeat":
            if self.left is None:
                self.left = self.case["number"]
            self.left -= 1
            if self.left > 0:
                return True
            self.left = None
        self.i += 1
        return True


def run(steps, case):
    m, seq = Machine(steps, case), []
    while m.expected() is not None:
        a = m.expected()
        seq.append(a)
        m.press(a)
    return seq


def _structure(rng):
    while True:
        t = TYPES[:]
        rng.shuffle(t)
        if t[0] == "fixed" and t[-1] != "repeat":
            return t


def _cases(rng):
    """Demo + 3 test cases: both lamp colours tested, numbers 1-3 all used once."""
    nums = [1, 2, 3]
    rng.shuffle(nums)
    lamps = [0, 1, rng.randrange(2)]
    rng.shuffle(lamps)
    tests = [{"lamp": l, "number": n} for l, n in zip(lamps, nums)]
    demo = {"lamp": rng.randrange(2), "number": 2}
    return demo, tests


def _make(rng, types, actions, demo, tests):
    pool = list(actions)
    steps = []
    for t in types:
        if t == "cond":
            steps.append({"t": t, "color": rng.randrange(N_COLORS), "a": pool.pop(), "b": pool.pop()})
        else:
            steps.append({"t": t, "a": pool.pop()})
    buttons = sorted(set(actions) - set(pool))
    rng.shuffle(buttons)
    return {"steps": steps, "buttons": buttons, "demo": demo, "demo_answer": run(steps, demo),
            "cases": tests, "study_ms": STUDY_MS, "case_ms": CASE_MS}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        types = _structure(rng)
        demo, tests = _cases(rng)
        acts = rng.sample(range(N_ACTIONS), 16)
        items.append(_make(rng, types, acts[:8], demo, tests))
        items.append(_make(rng, types, acts[8:], demo, tests))
    return items[:n]


def _first_error(steps, case, presses):
    """Classify the first deviation: 'rule' (other branch of a conditional), 'count'
    (wrong number of presses in the counted step), 'order' (another step's button),
    'short' (stopped early), 'long' (extra presses), or None (all correct)."""
    m = Machine(steps, case)
    for a in presses:
        exp = m.expected()
        if exp is None:
            return "long"
        if not m.press(a):
            st = steps[m.i]
            if st["t"] == "cond" and a in (st["a"], st["b"]):
                return "rule"
            if st["t"] == "repeat" or (m.i > 0 and steps[m.i - 1]["t"] == "repeat" and a == steps[m.i - 1]["a"]):
                return "count"
            return "order"
    return None if m.expected() is None else ("count" if m.left is not None else "short")


def score(item, response):
    """response: {"study_ms": ms, "cases": [{"presses": [action ids], "rt": ms, "undos": n,
    "timed_out": bool}]}.
    hit = at least 2 of the 3 test cases operated exactly right (whole sequence).
    metrics: cases correct, position-wise step accuracy, counts of first-error types
    (rule / count / order / short / long), study time, mean time per case, undos,
    cases that ran out of time."""
    try:
        steps, cases = item["steps"], item["cases"]
        resp = response if isinstance(response, dict) else {}
        rc = resp.get("cases") if isinstance(resp.get("cases"), list) else []
        n_ok, step_hits, step_total, undos, times, n_to = 0, 0, 0, 0, [], 0
        kinds = {"rule": 0, "count": 0, "order": 0, "short": 0, "long": 0}
        for k, case in enumerate(cases):
            r = rc[k] if k < len(rc) and isinstance(rc[k], dict) else {}
            pr = r.get("presses")
            pr = [p for p in pr if isinstance(p, int) and not isinstance(p, bool)] if isinstance(pr, list) else []
            key = run(steps, case)
            if pr == key:
                n_ok += 1
            else:
                e = _first_error(steps, case, pr)
                if e:
                    kinds[e] += 1
            step_hits += sum(1 for a, b in zip(pr, key) if a == b)
            step_total += max(len(pr), len(key))
            n_to += r.get("timed_out") is True
            if isinstance(r.get("undos"), int):
                undos += r["undos"]
            if isinstance(r.get("rt"), (int, float)) and r["rt"] > 0:
                times.append(r["rt"])
        st = resp.get("study_ms")
        return {"hit": n_ok >= 2, "errors": len(cases) - n_ok,
                "metrics": {"cases_correct": n_ok, "step_accuracy": round(step_hits / step_total, 3) if step_total else None,
                            "first_error_types": kinds, "rule_errors": kinds["rule"],
                            "study_ms": st if isinstance(st, (int, float)) else None,
                            "mean_case_ms": round(sum(times) / len(times), 1) if times else None,
                            "undos": undos, "cases_timed_out": n_to}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    cases = []
    for case in item["cases"]:
        seq = run(item["steps"], case)
        if not correct:
            # take the other branch at the first conditional step
            seq = run([dict(s, a=s["b"], b=s["a"]) if s["t"] == "cond" else s for s in item["steps"]], case)
        cases.append({"presses": seq, "rt": 9000, "undos": 0})
    return {"study_ms": 30000, "cases": cases}
