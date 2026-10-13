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
from app.tasks import _guard as G

TIMING = "limit"
N_ACTIONS = 16  # length of "actions" in the text files
N_COLORS = 2    # length of "colors"
STUDY_MS = 45000
CASE_MS = 40000  # a case is submitted as it stands after this long
LIMIT_MS = CASE_MS     # view.js: setTimeout(() => done(true), it.case_ms) per case
TIME_SLACK_MS = 1000   # timer tolerance at the case limit / study limit
MAX_PRESSES = 200
CEILING_MS = G.trial_ceiling(__file__)
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


@G.safe
def score(item, response):
    """response: {"study_ms": ms, "cases": [{"presses": [action ids], "rt": ms, "undos": n,
    "timed_out": bool}], one per test case}.
    The correct press sequence of every case is recomputed by running the procedure's
    state machine. Presses must be button ids of this item (a malformed press is flagged and
    the case cannot be correct). A case is operated exactly right only when its presses equal
    the machine's sequence AND its rt (time from the case onset to Done or to the automatic
    end) is a valid time within the 40 s case limit (item case_ms, view.js) + 1 s timer
    tolerance; a missing, non-finite, negative, anticipatory (< 100 ms) or late rt never
    counts. The browser's timed_out flag is only reported (it never makes a case correct);
    a timed_out that contradicts rt is flagged.
    hit = at least 2 of the 3 test cases operated exactly right (whole sequence, valid time).
    metrics: cases correct, position-wise step accuracy, counts of first-error types
    (rule / count / order / short / long), study time, mean time per case, undos,
    cases that ran out of time."""
    a = G.Audit(CEILING_MS)
    steps, cases = item["steps"], item["cases"]
    if not isinstance(response, dict):
        return a.junk(len(cases))
    limit = item.get("case_ms", CASE_MS)
    buttons = set(item["buttons"])
    n_ok, step_hits, step_total, undos, times, n_to = 0, 0, 0, 0, [], 0
    kinds = {"rule": 0, "count": 0, "order": 0, "short": 0, "long": 0}
    raw = response.get("cases", G.MISSING)
    if raw is G.MISSING:
        a.malformed("missing_cases")
        raw = []
    events = []
    for k, (case, r) in enumerate(zip(cases, a.entries(raw, len(cases), "cases"))):
        d = a.obj(r, "case")
        if d is None:
            a.record(G.INVALID)
            d, valid = {}, False
        else:
            valid = True
        pr_raw = a.stream(d.get("presses", G.MISSING), "presses", cap=MAX_PRESSES) if r is not G.MISSING and \
            isinstance(r, dict) else []
        pr = []
        for p in pr_raw:
            if G.member(p, buttons):
                pr.append(p)
            else:
                a.malformed("invalid_press")
                valid = False
        st, rt = (a.time(d.get("rt", G.MISSING), field="rt", window=limit, slack=TIME_SLACK_MS, required=True)
                  if isinstance(r, dict) else (G.INVALID, None))
        if isinstance(r, dict):
            a.record(st)
            to = a.opt_bool(d, "timed_out")
            n_to += to is True
            if to is True and rt is not None and rt < limit - TIME_SLACK_MS:
                a.malformed("timed_out_before_limit")
            u = a.opt_int(d, "undos", hi=10000)
            undos += u or 0
        key = run(steps, case)
        exact = pr == key
        ok = exact and valid and st == G.TIMELY
        if exact and not ok:
            a.flag("exact_case_with_invalid_timing_or_presses")
        if ok:
            n_ok += 1
        elif not exact:
            e = _first_error(steps, case, pr)
            if e:
                kinds[e] += 1
        step_hits += sum(1 for x, y in zip(pr, key) if x == y)
        step_total += max(len(pr), len(key))
        if st == G.TIMELY:
            times.append(rt)
        events.append({"i": k, "status": st, "correct": ok, "rt": rt if st == G.TIMELY else None})
    study = a.duration(response, "study_ms", floor=0, window=item.get("study_ms", STUDY_MS) + TIME_SLACK_MS)
    return a.finish(n_ok >= 2, len(cases) - n_ok, {
        "cases_correct": n_ok, "step_accuracy": round(step_hits / step_total, 3) if step_total else None,
        "first_error_types": kinds, "rule_errors": kinds["rule"],
        "study_ms": study, "mean_case_ms": G.mean(times),
        "undos": undos, "cases_timed_out": n_to, "events": events})


def example_response(item, correct=True):
    cases = []
    for case in item["cases"]:
        seq = run(item["steps"], case)
        if not correct:
            # take the other branch at the first conditional step
            seq = run([dict(s, a=s["b"], b=s["a"]) if s["t"] == "cond" else s for s in item["steps"]], case)
        cases.append({"presses": seq, "rt": 9000, "undos": 0, "timed_out": False})
    return {"study_ms": 30000, "cases": cases}
