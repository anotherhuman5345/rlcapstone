"""Sliding-tile puzzle (card 38): a 3x3 board with tiles 1-8 and one gap. Slide tiles next
to the gap until the board reads 1-8 in order with the gap last. Boards are scrambled from
the goal by random legal moves (so every board is reachable); the true minimum number of
moves is then found by breadth-first search (the scramble length is not assumed optimal).
Pairs (k, k+1) are two different boards with the same minimum (8 or 10 moves, alternating
across pairs). The server replays every recorded tile press itself."""
from collections import deque

N = 3
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
LEVELS = (8, 10)
LIMIT_MS = 90000
MAX_EVENTS = 2000


def _slide(state, tile):
    """State after sliding `tile` into the gap, or None if it is not next to the gap."""
    if not isinstance(tile, int) or isinstance(tile, bool) or not 1 <= tile <= 8:
        return None
    z, t = state.index(0), state.index(tile)
    if abs(z // N - t // N) + abs(z % N - t % N) != 1:
        return None
    s = list(state)
    s[z], s[t] = s[t], s[z]
    return tuple(s)


def _neighbours(state):
    z = state.index(0)
    r, c = divmod(z, N)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            tile = state[rr * N + cc]
            yield tile, _slide(state, tile)


def _solve(start):
    """Shortest list of tiles to slide from start to GOAL (breadth-first search)."""
    start = tuple(start)
    prev = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if s == GOAL:
            path = []
            while prev[s] is not None:
                s, tile = prev[s]
                path.append(tile)
            return path[::-1]
        for tile, n in _neighbours(s):
            if n not in prev:
                prev[n] = (s, tile)
                q.append(n)
    return None


def _solvable(state):
    tiles = [t for t in state if t]
    inv = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])
    return inv % 2 == 0


def _scramble(rng, level, avoid):
    while True:
        s, last = GOAL, None
        for _ in range(level + rng.randint(0, 8)):
            opts = [(t, n) for t, n in _neighbours(s) if t != last]
            last, s = rng.choice(opts)
        if s not in avoid and _solvable(s) and len(_solve(s)) == level:
            return s


def generate(rng, n, save_image):
    items, seen = [], set()
    while len(items) < n:
        level = LEVELS[(len(items) // 2) % len(LEVELS)]
        s = _scramble(rng, level, seen)
        seen.add(s)
        items.append({"size": N, "start": list(s), "goal": list(GOAL), "optimal": level, "limit_ms": LIMIT_MS})
    return items[:n]


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def score(item, response):
    """response: {"events": [{"tile": 1-8, "t": ms} | {"reset": true, "t": ms}], "first_move_ms",
    "rt_ms", "gave_up"}; arrow keys are sent as the tile they move (0 if no tile can move that
    way). The server replays the events: pressing a tile that is not next to the gap is an
    illegal attempt (counted, not applied); a reset restores the start board.
    hit = the final board is the goal (1-8 in order, gap last). Metrics: moves, excess over
    the BFS minimum, illegal attempts, resets, first-move and solve times. errors = illegal
    attempts."""
    miss = {"hit": False, "errors": 0, "metrics": {}}
    try:
        if not isinstance(response, dict):
            return miss
        start = tuple(item["start"])
        optimal = len(_solve(start))
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
            nxt = _slide(state, ev.get("tile"))
            if nxt is None:
                illegal += 1
                continue
            state, moves = nxt, moves + 1
            if state == GOAL and solved_at is None:
                solved_at = _num(ev.get("t"))
        solved = state == GOAL
        return {"hit": solved, "errors": illegal,
                "metrics": {"solved": solved, "moves": moves, "optimal": optimal,
                            "excess_moves": moves - optimal if solved else None,
                            "illegal_attempts": illegal, "resets": resets,
                            "first_move_ms": _num(response.get("first_move_ms")),
                            "solve_ms": solved_at, "rt_ms": _num(response.get("rt_ms")),
                            "gave_up": response.get("gave_up") is True}}
    except Exception:
        return miss


def example_response(item, correct=True):
    path = _solve(item["start"])
    if not correct:
        path = path[:-1]
    events = [{"tile": t, "t": 2000 + 900 * k} for k, t in enumerate(path)]
    return {"events": events, "first_move_ms": 2000, "rt_ms": 2000 + 900 * len(path), "gave_up": not correct}
