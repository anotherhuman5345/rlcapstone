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

N_GLYPHS = 10
LEFT, RIGHT, EDIT, CYCLE, CLEAR, OK = range(6)
MAX_ACTIONS = 40
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
                          "limit_ms": 200000})
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


def score(item, response):
    """response: {"goals": [{"actions": [function id 0-5, ...], "times": [ms, ...]}, ...]}
    (training goal first). The server replays the presses on the state machine; a goal
    succeeds when confirm is pressed outside edit mode with all three lamps right.
    errors = presses with no effect + wrong confirms; excess = presses beyond the BFS optimum.
    hit = both transfer goals (goals 2 and 3, no legend) succeeded."""
    miss = {"hit": False, "errors": 3, "metrics": {}}
    if not isinstance(response, dict) or not isinstance(response.get("goals"), list):
        return miss
    res = []
    for k, goal in enumerate(item["goals"]):
        r = response["goals"][k] if k < len(response["goals"]) and isinstance(response["goals"][k], dict) else {}
        acts = [a for a in (r.get("actions") if isinstance(r.get("actions"), list) else [])
                if isinstance(a, int) and not isinstance(a, bool) and 0 <= a <= 5]
        times = r.get("times") if isinstance(r.get("times"), list) else []
        ok, steps, noop, wc = replay(goal, acts)
        t_end = times[-1] if times and isinstance(times[-1], (int, float)) and not isinstance(times[-1], bool) else None
        res.append({"ok": ok, "steps": steps, "errors": noop + wc,
                    "excess": steps - goal["optimal"] if ok else None, "time_ms": t_end})
    transfer = res[1:]
    errs = sum(r["errors"] for r in res)
    return {"hit": all(r["ok"] for r in transfer),
            "errors": errs + sum(not r["ok"] for r in res),
            "metrics": {"training_success": res[0]["ok"], "transfer_successes": sum(r["ok"] for r in transfer),
                        "transfer_steps": sum(r["steps"] for r in transfer),
                        "transfer_excess_steps": sum(r["excess"] for r in transfer if r["excess"] is not None),
                        "transfer_errors": sum(r["errors"] for r in transfer),
                        "training_errors": res[0]["errors"],
                        "goal_times_ms": [r["time_ms"] for r in res], "goals": res}}


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
