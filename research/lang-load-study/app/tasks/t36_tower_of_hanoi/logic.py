"""Tower of Hanoi (card 36): move a 3-disk tower to the target peg; a larger disk may never
rest on a smaller one. One trial is one puzzle. Even pairs use the standard setup (whole
tower on one peg -> another peg, optimum 2^3-1 = 7 moves) with different start/target pegs;
odd pairs start from a scattered legal position and need the whole tower on a target peg,
with both items of the pair at the same breadth-first-search optimum. The browser blocks
illegal moves but reports every attempt; the server replays the whole event list itself."""
from collections import deque

DISKS = 3
PEGS = 3
LIMIT_MS = 90000      # the view ends the puzzle itself after this (task.json timeout is larger)
MAX_EVENTS = 1000


def _tops(state):
    """Smallest disk on each peg (or None). state[d] = peg of disk d, disk 0 smallest."""
    tops = [None] * PEGS
    for d in range(len(state) - 1, -1, -1):
        tops[state[d]] = d
    return tops


def _move(state, a, b):
    """New state after moving the top disk of peg a to peg b, or None if illegal."""
    if a == b or not (0 <= a < PEGS and 0 <= b < PEGS):
        return None
    tops = _tops(state)
    if tops[a] is None or (tops[b] is not None and tops[b] < tops[a]):
        return None
    s = list(state)
    s[tops[a]] = b
    return tuple(s)


def _bfs(start, goal):
    """Shortest legal path start -> goal as a list of (from, to)."""
    start, goal = tuple(start), tuple(goal)
    prev = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if s == goal:
            path = []
            while prev[s] is not None:
                s, mv = prev[s]
                path.append(mv)
            return path[::-1]
        for a in range(PEGS):
            for b in range(PEGS):
                n = _move(s, a, b)
                if n is not None and n not in prev:
                    prev[n] = (s, (a, b))
                    q.append(n)
    return None


def _all_states():
    out = [()]
    for _ in range(DISKS):
        out = [s + (p,) for s in out for p in range(PEGS)]
    return out


def generate(rng, n, save_image):
    items = []
    scattered_d = 6
    while len(items) < n:
        pair_no = len(items) // 2
        if pair_no % 2 == 0:
            combos = [(s, g) for s in range(PEGS) for g in range(PEGS) if s != g]
            rng.shuffle(combos)
            pair = [((s,) * DISKS, (g,) * DISKS) for s, g in combos[:2]]
        else:
            cands = []
            for st in _all_states():
                if len(set(st)) == 1:
                    continue
                for g in range(PEGS):
                    goal = (g,) * DISKS
                    if len(_bfs(st, goal)) == scattered_d:
                        cands.append((st, goal))
            rng.shuffle(cands)
            pair = cands[:2]
        for st, goal in pair:
            items.append({"disks": DISKS, "start": list(st), "goal": list(goal),
                          "optimal": len(_bfs(st, goal)), "limit_ms": LIMIT_MS})
    return items[:n]


def _replay(item, response):
    start, goal = tuple(item["start"]), tuple(item["goal"])
    events = response.get("events")
    if not isinstance(events, list):
        events = []
    state, moves, illegal, resets, since_reset = start, 0, 0, 0, 0
    solved_at = None
    for ev in events[:MAX_EVENTS]:
        if not isinstance(ev, dict):
            illegal += 1
            continue
        if ev.get("reset") is True:
            state, resets, since_reset = start, resets + 1, 0
            continue
        a, b = ev.get("from"), ev.get("to")
        nxt = _move(state, a, b) if isinstance(a, int) and isinstance(b, int) else None
        if nxt is None:
            illegal += 1
            continue
        state, moves, since_reset = nxt, moves + 1, since_reset + 1
        if state == goal and solved_at is None:
            solved_at = ev.get("t") if isinstance(ev.get("t"), (int, float)) else None
    return state == goal, moves, illegal, resets, since_reset, solved_at


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def score(item, response):
    """response: {"events": [{"from": peg, "to": peg, "t": ms} | {"reset": true, "t": ms}],
    "first_move_ms", "rt_ms", "gave_up"}; pegs are 0-2, times from the Start press.
    The server replays the events from the start position: illegal attempts (empty source
    peg, larger disk onto smaller, same peg) are counted and not applied; a reset returns
    to the start position. hit = the final position is the goal position (the tower is
    complete on the target peg), regardless of how many moves it took; efficiency is in
    the metrics (moves, excess over the BFS optimum, illegal attempts, resets, times).
    errors = illegal attempts."""
    miss = {"hit": False, "errors": 0, "metrics": {}}
    try:
        if not isinstance(response, dict):
            return miss
        optimal = len(_bfs(item["start"], item["goal"]))
        solved, moves, illegal, resets, since_reset, solved_at = _replay(item, response)
        return {"hit": bool(solved), "errors": illegal,
                "metrics": {"solved": bool(solved), "moves": moves, "optimal": optimal,
                            "excess_moves": moves - optimal if solved else None,
                            "moves_after_last_reset": since_reset,
                            "illegal_attempts": illegal, "resets": resets,
                            "first_move_ms": _num(response.get("first_move_ms")),
                            "solve_ms": _num(solved_at), "rt_ms": _num(response.get("rt_ms")),
                            "gave_up": response.get("gave_up") is True}}
    except Exception:
        return miss


def example_response(item, correct=True):
    path = _bfs(item["start"], item["goal"])
    if not correct:
        path = path[:-1]
    events = [{"from": a, "to": b, "t": 1500 + 1200 * k} for k, (a, b) in enumerate(path)]
    return {"events": events, "first_move_ms": 1500, "rt_ms": 1500 + 1200 * len(path), "gave_up": not correct}
