"""Maze planning (card 35): move a dot from the start to the exit of a square-grid maze
with the arrow keys, the on-screen arrows, or by tapping a neighbouring cell. The maze is
visible throughout; planning time (Start to first move) is recorded apart from movement
time. One trial = one maze.

Mazes are a random spanning tree (always connected) with a few extra openings, so there
are some loops and several routes but one shortest length. Size alternates 8x8 / 12x12
across pairs; within a pair (k, k+1) both mazes have the same size and their shortest
paths differ by at most 10% (so L1 and L2 mazes are equally hard). Start and exit are
opposite corners.

Cell walls: "open" is a row-major list of bitmasks, 1 = open to the north (up), 2 = east,
4 = south, 8 = west. score() replays the moves against these walls and compares with a
BFS shortest path; nothing the browser claims about position or success is trusted."""

import math
from collections import deque

from app.tasks import _guard as G

TIMING = "limit"        # the move that reaches the exit must come inside LIMIT_MS
LIMIT_MS = 120000       # view.js: timer = setTimeout(() => end(true), 120000)
TIME_SLACK_MS = 1000    # timer tolerance at the limit
MAX_MOVES = 3000
CEILING_MS = G.trial_ceiling(__file__)

DIRS = {"U": (-1, 0, 1, 4), "R": (0, 1, 2, 8), "D": (1, 0, 4, 1), "L": (0, -1, 8, 2)}
SIZES = (8, 12)


def _carve(rng, size):
    cells = [0] * (size * size)
    seen = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        r, c = stack[-1]
        nbs = [(d, r + dr, c + dc) for d, (dr, dc, _, _) in DIRS.items()
               if 0 <= r + dr < size and 0 <= c + dc < size and (r + dr, c + dc) not in seen]
        if not nbs:
            stack.pop()
            continue
        d, nr, nc = rng.choice(nbs)
        _, _, bit, back = DIRS[d]
        cells[r * size + c] |= bit
        cells[nr * size + nc] |= back
        seen.add((nr, nc))
        stack.append((nr, nc))
    walls = [(r, c, d) for r in range(size) for c in range(size) for d in ("R", "D")
             if (d == "R" and c + 1 < size or d == "D" and r + 1 < size) and not cells[r * size + c] & DIRS[d][2]]
    for r, c, d in rng.sample(walls, size * size // 12):  # a few loops
        dr, dc, bit, back = DIRS[d]
        cells[r * size + c] |= bit
        cells[(r + dr) * size + c + dc] |= back
    return cells


def shortest(item):
    """BFS oracle: fewest moves from start to exit, or None if unreachable."""
    size = item["size"]
    start, goal = tuple(item["start"]), tuple(item["exit"])
    dist = {start: 0}
    q = deque([start])
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return dist[(r, c)]
        for dr, dc, bit, _ in DIRS.values():
            nb = (r + dr, c + dc)
            if item["open"][r * size + c] & bit and nb not in dist:
                dist[nb] = dist[(r, c)] + 1
                q.append(nb)
    return None


def _path(item):
    size = item["size"]
    start, goal = tuple(item["start"]), tuple(item["exit"])
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for d, (dr, dc, bit, _) in DIRS.items():
            nb = (cur[0] + dr, cur[1] + dc)
            if item["open"][cur[0] * size + cur[1]] & bit and nb not in prev:
                prev[nb] = (cur, d)
                q.append(nb)
    moves, cur = [], goal
    while prev[cur]:
        cur, d = prev[cur]
        moves.append(d)
    return moves[::-1]


def _maze(rng, size):
    corners = [(0, 0), (0, size - 1), (size - 1, size - 1), (size - 1, 0)]
    k = rng.randrange(4)
    item = {"size": size, "open": _carve(rng, size), "start": list(corners[k]), "exit": list(corners[(k + 2) % 4])}
    return item


def generate(rng, n, save_image):
    items = []
    for k in range(n):
        size = SIZES[(k // 2) % 2]
        if k % 2 == 0:
            m = _maze(rng, size)
            ref = shortest(m)
        else:
            for _ in range(400):
                m = _maze(rng, size)
                if abs(shortest(m) - ref) <= 0.1 * ref:
                    break
        items.append(m)
    return items


def replay(item, moves):
    """Walk the moves through the walls. Returns (reached, steps, bumps); moves after the exit are ignored."""
    size = item["size"]
    r, c = item["start"]
    goal = tuple(item["exit"])
    steps = bumps = 0
    for d in moves:
        if (r, c) == goal:
            break
        if d not in DIRS:
            bumps += 1
            continue
        dr, dc, bit, _ = DIRS[d]
        if item["open"][r * size + c] & bit:
            r, c = r + dr, c + dc
            steps += 1
        else:
            bumps += 1
    return (r, c) == goal, steps, bumps


@G.safe
def score(item, response):
    """response: {"moves": [{"d": "U"|"R"|"D"|"L", "t": ms since Start}, ...], "reached"} (every
    key or tap, including ones that hit a wall).
    The server replays the moves against the walls. Malformed moves (not an object, a
    direction that is not U/R/D/L, a missing/invalid time) are flagged and not applied; move
    times must not go backwards (flagged). The browser stops recording at the exit, so moves
    after it are flagged and ignored. The browser's "reached" is not trusted (a mismatch is
    flagged).
    hit = the replayed moves reach the exit using at most shortest + ceil(25% of shortest)
    steps AND the move that reached the exit has a valid time inside the 120 s limit (a
    missing, non-finite, negative or late time never counts). errors = wall bumps + excess
    steps + malformed moves. Metrics: reached, steps, shortest, excess steps, bumps,
    planning time (first move), movement time (first to last move), total."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    raw = a.stream(response.get("moves", G.MISSING), "moves", cap=MAX_MOVES)
    size, opened = item["size"], item["open"]
    r, c = item["start"]
    goal = tuple(item["exit"])
    steps = bumps = malformed = after = 0
    times, ts, exit_t = [], [], None
    for m in raw:
        if (r, c) == goal:
            after += 1
            continue
        if not isinstance(m, dict):
            a.malformed("move_not_object")
            malformed += 1
            continue
        st, t = a.time(m.get("t", G.MISSING), field="t", window=LIMIT_MS, slack=TIME_SLACK_MS, required=True)
        times.append(t if st != G.INVALID else None)
        d = m.get("d")
        if not G.member(d, DIRS):
            a.malformed("invalid_d")
            malformed += 1
            continue
        if st != G.INVALID:
            ts.append(t)
        dr, dc, bit, _ = DIRS[d]
        if opened[r * size + c] & bit:
            r, c = r + dr, c + dc
            steps += 1
            if (r, c) == goal:
                exit_t = (st, t)
        else:
            bumps += 1
    if after:
        a.flag("moves_after_exit", after)
    a.monotonic(times, "t")
    best = _shortest_cached(item)
    at_exit = (r, c) == goal
    timely = exit_t is not None and exit_t[0] == G.TIMELY
    reached = at_exit and timely
    if at_exit and not timely:
        a.flag("reached_outside_time_limit")
    claimed = a.opt_bool(response, "reached")
    if claimed is not None and claimed != at_exit:
        a.flag("reached_mismatch")
    excess = steps - best if reached else None
    limit = best + math.ceil(0.25 * best)
    hit = bool(reached and steps <= limit)
    return a.finish(hit, bumps + (excess if excess else 0) + malformed, {
        "reached": reached, "steps": steps, "shortest": best, "excess_steps": excess,
        "bumps": bumps, "malformed_moves": malformed, "size": size,
        "plan_ms": ts[0] if ts else None,
        "move_ms": round(ts[-1] - ts[0], 1) if len(ts) > 1 else None,
        "total_ms": ts[-1] if ts else None})


_SHORTEST = {}


def _shortest_cached(item):
    """shortest(item), memoized per maze (the harness scores each item many times)."""
    key = (item["size"], tuple(item["open"]), tuple(item["start"]), tuple(item["exit"]))
    if key not in _SHORTEST:
        if len(_SHORTEST) > 512:
            _SHORTEST.clear()
        _SHORTEST[key] = shortest(item)
    return _SHORTEST[key]


def example_response(item, correct=True):
    moves = _path(item)
    if not correct:
        moves = moves[: len(moves) // 2]
    return {"moves": [{"d": d, "t": 3000 + 400 * i} for i, d in enumerate(moves)], "reached": correct}
