"""Novel interface learning (card 70), adapted to one trial: 1 training goal + 2 transfer goals.

A made-up device has 3 lamps (colours off/red/yellow/blue), a selection marker and an edit
mode, operated by 6 controls drawn as abstract glyphs (no arrows or familiar icons):
  0 select left   1 select right   (only outside edit mode)
  2 edit on/off   3 next colour of the selected lamp (only in edit mode)
  4 all lamps off (any mode)       5 confirm (only outside edit mode; ends the goal)
Every goal names the lamp colours to reach in words (text "goal" + "colors"), then
"confirm". Training goal: a legend explains each glyph. Transfer goals: no legend.
Pressing a control that has no effect in the current mode is an error.

The workflow state machine (step) is used by the server to replay the presses and by
BFS to get each goal's optimal number of presses. Pairs (k, k+1) have goals with the same
optimal lengths, with different glyphs, layouts and colours.
"""
from collections import deque

from app.tasks import _guard as G

TIMING = "limit"
N_GLYPHS = 10
LEFT, RIGHT, EDIT, CYCLE, CLEAR, OK = range(6)
MAX_ACTIONS = 40
LIMIT_MS = 200000      # item limit_ms: view.js ends the trial with setTimeout(end, it.limit_ms) from Start
BETWEEN_MS = 1200      # view.js: pause before the next goal (setTimeout(startGoal, 1200))
TIME_SLACK_MS = 1000   # timer tolerance at the limit
CEILING_MS = G.trial_ceiling(__file__)
GOAL_LEN = [(6, 8), (8, 10), (8, 10)]   # optimal presses: training, transfer 1, transfer 2


def step(state, a):
    """Workflow state machine. state = (colors tuple, cursor, edit). Returns
    (new_state, had_effect, confirmed)."""
    colors, cur, edit = state
    if a == LEFT and not edit:
        return (colors, (cur - 1) % 3, edit), True, False
    if a == RIGHT and not edit:
        return (colors, (cur + 1) % 3, edit), True, False
    if a == EDIT:
        return (colors, cur, not edit), True, False
    if a == CYCLE and edit:
        c = list(colors)
        c[cur] = (c[cur] + 1) % 4
        return (tuple(c), cur, edit), True, False
    if a == CLEAR:
        return ((0, 0, 0), cur, edit), colors != (0, 0, 0), False
    if a == OK and not edit:
        return state, True, True
    return state, False, False


def optimal(start, target):
    """Fewest presses from start (cursor 0, not editing) to a correct confirm (BFS)."""
    s0 = (tuple(start), 0, False)
    seen, q = {s0: 0}, deque([s0])
    while q:
        s = q.popleft()
        if s[0] == tuple(target) and not s[2]:
            return seen[s] + 1
        for a in (LEFT, RIGHT, EDIT, CYCLE, CLEAR):
            n, _, _ = step(s, a)
            if n not in seen:
                seen[n] = seen[s] + 1
                q.append(n)
    return None


def _goal(rng, length):
    while True:
        start = [rng.randint(0, 3) for _ in range(3)]
        target = [rng.randint(0, 3) for _ in range(3)]
        if start != target and target != [0, 0, 0] and optimal(start, target) == length:
            return {"start": start, "target": target, "optimal": length}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        lengths = [rng.randint(lo, hi) for lo, hi in GOAL_LEN]
        for _ in range(2):
            items.append({"glyphs": rng.sample(range(N_GLYPHS), 6), "funcs": rng.sample(range(6), 6),
                          "goals": [_goal(rng, L) for L in lengths], "max_actions": MAX_ACTIONS,
                          "limit_ms": LIMIT_MS})
    return items[:n]


def replay(goal, actions):
    state = (tuple(goal["start"]), 0, False)
    noop = wrong_confirm = steps = 0
    for a in actions[:MAX_ACTIONS]:
        steps += 1
        state, eff, done = step(state, a)
        noop += not eff
        if done:
            ok = list(state[0]) == goal["target"]
            return ok, steps, noop, 0 if ok else 1
    return False, steps, noop, wrong_confirm


def _goal_presses(a, r, limit):
    """Validated presses of one goal -> (actions, times, ok). Every action must be a
    function id 0-5 and every time a finite ms value 0..limit from the goal start, one time
    per action, in order. Malformed entries are flagged and not applied (ok = False: a goal
    whose press record is damaged is never scored as a success)."""
    ok = True
    raw_a = a.stream(r.get("actions", G.MISSING), "actions", cap=MAX_ACTIONS)
    raw_t = a.stream(r.get("times", G.MISSING), "times", cap=MAX_ACTIONS)
    if not isinstance(r.get("actions"), list) or len(r["actions"]) > MAX_ACTIONS:
        ok = False
    if not isinstance(r.get("times"), list) or len(r["times"]) > MAX_ACTIONS:
        ok = False
    if len(raw_a) != len(raw_t):
        a.malformed("times_actions_mismatch")
        ok = False
    acts, times = [], []
    for k, v in enumerate(raw_a):
        if not G.member(v, range(6)):
            a.malformed("invalid_action")
            ok = False
            continue
        st, t = a.time(raw_t[k] if k < len(raw_t) else G.MISSING, field="times", window=limit,
                       slack=TIME_SLACK_MS, floor=0, required=True)
        if st != G.TIMELY:
            ok = False
        acts.append(v)
        times.append(t)
    if not a.monotonic(times, "times"):
        ok = False
    vals = [t for t in times if t is not None]
    if len(set(vals)) < len(vals):
        a.malformed("duplicate_times")
        ok = False
    return acts, times, ok


@G.safe
def score(item, response):
    """response: {"goals": [{"actions": [function id 0-5, ...], "times": [ms from goal
    start, ...]}, ...]} (training goal first; one entry per started goal).
    Presses are validated: every action a function id 0-5, one time per action, times finite,
    >= 0, increasing and inside the 200 s limit (item limit_ms, view.js) + 1 s tolerance; at
    most max_actions presses and nothing after the confirm that ends a goal. Malformed entries
    are flagged and not applied, and a goal with any malformed press is never a success.
    The server replays the presses on the state machine; a goal succeeds when confirm is
    pressed outside edit mode with all three lamps right, the confirm has a valid time, and
    the goals so far (+ the 1.2 s pauses) end inside the limit.
    errors = presses with no effect + wrong confirms; excess = presses beyond the BFS optimum.
    hit = both transfer goals (goals 2 and 3, no legend) succeeded."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(3)
    limit = item.get("limit_ms", LIMIT_MS)
    goals = item["goals"]
    rg = a.stream(response.get("goals", G.MISSING), "goals", cap=len(goals) + 5)
    if len(rg) > len(goals):
        a.malformed("extra_goals")
    res, elapsed = [], 0.0
    for k, goal in enumerate(goals):
        if k >= len(rg):
            a.record(G.ABSENT)
            res.append({"ok": False, "steps": 0, "errors": 0, "excess": None, "time_ms": None})
            continue
        r = a.obj(rg[k], "goal")
        if r is None:
            a.record(G.INVALID)
            res.append({"ok": False, "steps": 0, "errors": 0, "excess": None, "time_ms": None})
            continue
        acts, times, valid = _goal_presses(a, r, limit)
        ok, steps, noop, wc = replay(goal, acts)
        if steps < len(acts) and (ok or wc):
            a.malformed("actions_after_confirm")
            valid = False
        t_end = times[steps - 1] if steps and steps <= len(times) else None
        if t_end is not None:
            elapsed += t_end + (BETWEEN_MS if k else 0)
            if elapsed > limit + TIME_SLACK_MS:
                a.malformed("goals_exceed_limit")
                valid = False
        status = G.ABSENT if not acts else (G.TIMELY if valid and t_end is not None else G.INVALID)
        a.record(status)
        if ok and not valid:
            a.flag("success_with_invalid_presses")
        good = ok and valid
        res.append({"ok": good, "steps": steps, "errors": noop + wc,
                    "excess": steps - goal["optimal"] if good else None,
                    "time_ms": t_end if valid else None})
    transfer = res[1:]
    errs = sum(r["errors"] for r in res)
    return a.finish(all(r["ok"] for r in transfer), errs + sum(not r["ok"] for r in res), {
        "training_success": res[0]["ok"], "transfer_successes": sum(r["ok"] for r in transfer),
        "transfer_steps": sum(r["steps"] for r in transfer),
        "transfer_excess_steps": sum(r["excess"] for r in transfer if r["excess"] is not None),
        "transfer_errors": sum(r["errors"] for r in transfer),
        "training_errors": res[0]["errors"],
        "goal_times_ms": [r["time_ms"] for r in res], "goals": res})


def _solve(goal):
    """Shortest action list for a goal (BFS with parents)."""
    s0 = (tuple(goal["start"]), 0, False)
    prev, q = {s0: None}, deque([s0])
    while q:
        s = q.popleft()
        if list(s[0]) == goal["target"] and not s[2]:
            path = []
            while prev[s] is not None:
                s, a = prev[s]
                path.append(a)
            return path[::-1] + [OK]
        for a in (LEFT, RIGHT, EDIT, CYCLE, CLEAR):
            n, _, _ = step(s, a)
            if n not in prev:
                prev[n] = (s, a)
                q.append(n)
    return [OK]


def example_response(item, correct=True):
    goals = []
    for g in item["goals"]:
        acts = _solve(g) if correct else [OK]
        goals.append({"actions": acts, "times": [800 * (i + 1) for i in range(len(acts))]})
    return {"goals": goals}
