"""Tower of London style (card 37): three coloured balls sit on three pegs that hold at most
3, 2 and 1 balls. Move one top ball at a time until the pegs match the target picture.
Start and target positions are drawn at random (original configurations, not a published
item set) and a breadth-first search over all 36 positions gives the minimum number of
moves. Pairs (k, k+1) are two different puzzles with the same minimum; the minimum varies
across pairs (3, 4, 5, 6 moves). The server replays every recorded event itself."""
from collections import deque
from itertools import permutations

CAPS = (3, 2, 1)
BALLS = 3
LIMIT_MS = 90000
MAX_EVENTS = 1000
LEVELS = (3, 4, 5, 6)


def _norm(state):
    return tuple(tuple(p) for p in state)


def _move(state, a, b):
    """State after moving the top ball of peg a onto peg b, or None if not allowed."""
    if not (isinstance(a, int) and isinstance(b, int)) or isinstance(a, bool) or isinstance(b, bool):
        return None
    if a == b or not (0 <= a < 3 and 0 <= b < 3):
        return None
    if not state[a] or len(state[b]) >= CAPS[b]:
        return None
    s = [list(p) for p in state]
    s[b].append(s[a].pop())
    return _norm(s)


def _neighbours(state):
    for a in range(3):
        for b in range(3):
            n = _move(state, a, b)
            if n is not None:
                yield (a, b), n


def _bfs(start, goal):
    start, goal = _norm(start), _norm(goal)
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
        for mv, n in _neighbours(s):
            if n not in prev:
                prev[n] = (s, mv)
                q.append(n)
    return None


def _all_states():
    out = []
    for order in permutations(range(BALLS)):
        for c0 in range(4):
            for c1 in range(4 - c0):
                c2 = 3 - c0 - c1
                if c0 <= CAPS[0] and c1 <= CAPS[1] and c2 <= CAPS[2]:
                    out.append(_norm([order[:c0], order[c0:c0 + c1], order[c0 + c1:]]))
    return sorted(set(out))


def generate(rng, n, save_image):
    states = _all_states()
    dist = {(s, g): len(_bfs(s, g)) for s in states for g in states if s != g}
    items = []
    while len(items) < n:
        level = LEVELS[(len(items) // 2) % len(LEVELS)]
        cands = [sg for sg, d in sorted(dist.items()) if d == level]
        a = rng.choice(cands)
        # The partner: a different start AND a different target, same minimum moves.
        b = rng.choice([c for c in cands if c[0] != a[0] and c[1] != a[1]])
        for s, g in (a, b):
            items.append({"caps": list(CAPS), "start": [list(p) for p in s], "goal": [list(p) for p in g],
                          "optimal": level, "limit_ms": LIMIT_MS})
    return items[:n]


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def score(item, response):
    """response: {"events": [{"from": peg, "to": peg, "t": ms} | {"reset": true, "t": ms}],
    "first_move_ms", "rt_ms", "gave_up"}; pegs 0-2 (capacities 3, 2, 1), times from Start.
    The server replays the events from the start position: an attempt from an empty peg,
    onto a full peg or onto the same peg is an illegal attempt (counted, not applied); a
    reset restores the start. hit = the final position equals the target position.
    Planning quality is in the metrics: moves, excess over the BFS minimum, "perfect"
    (solved in exactly the minimum with no reset), planning latency (first_move_ms).
    errors = illegal attempts."""
    miss = {"hit": False, "errors": 0, "metrics": {}}
    try:
        if not isinstance(response, dict):
            return miss
        start, goal = _norm(item["start"]), _norm(item["goal"])
        optimal = len(_bfs(start, goal))
        events = response.get("events")
        events = events if isinstance(events, list) else []
        state, moves, illegal, resets, solved_at = start, 0, 0, 0, None
        for ev in events[:MAX_EVENTS]:
            if not isinstance(ev, dict):
                illegal += 1
                continue
            if ev.get("reset") is True:
                state, resets = start, resets + 1
                continue
            nxt = _move(state, ev.get("from"), ev.get("to"))
            if nxt is None:
                illegal += 1
                continue
            state, moves = nxt, moves + 1
            if state == goal and solved_at is None:
                solved_at = _num(ev.get("t"))
        solved = state == goal
        return {"hit": solved, "errors": illegal,
                "metrics": {"solved": solved, "moves": moves, "optimal": optimal,
                            "excess_moves": moves - optimal if solved else None,
                            "perfect": solved and moves == optimal and resets == 0,
                            "illegal_attempts": illegal, "resets": resets,
                            "first_move_ms": _num(response.get("first_move_ms")),
                            "solve_ms": solved_at, "rt_ms": _num(response.get("rt_ms")),
                            "gave_up": response.get("gave_up") is True}}
    except Exception:
        return miss


def example_response(item, correct=True):
    path = _bfs(item["start"], item["goal"])
    if not correct:
        path = path[:-1]
    events = [{"from": a, "to": b, "t": 4000 + 1500 * k} for k, (a, b) in enumerate(path)]
    return {"events": events, "first_move_ms": 4000, "rt_ms": 4000 + 1500 * len(path), "gave_up": not correct}
