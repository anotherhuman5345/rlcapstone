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


def score(item, response):
    """response: {"moves": [{"d": "U"|"R"|"D"|"L", "t": ms since Start}, ...]} (every key or
    tap, including ones that hit a wall).
    hit = the replayed moves reach the exit using at most shortest + ceil(25% of shortest)
    steps. errors = wall bumps + excess steps. Metrics: reached, steps, shortest, excess
    steps, bumps, planning time (first move), movement time (first to last move), total."""
    raw = response.get("moves") if isinstance(response, dict) else None
    raw = raw if isinstance(raw, list) else []
    moves, times = [], []
    for m in raw:
        if isinstance(m, dict):
            moves.append(m.get("d") if isinstance(m.get("d"), str) else None)
            t = m.get("t")
            times.append(t if isinstance(t, (int, float)) and not isinstance(t, bool) else None)
    best = shortest(item)
    reached, steps, bumps = replay(item, moves)
    excess = steps - best if reached else None
    limit = best + math.ceil(0.25 * best)
    ts = [t for t in times if t is not None]
    hit = bool(reached and steps <= limit)
    return {"hit": hit, "errors": bumps + (excess if excess else 0),
            "metrics": {"reached": reached, "steps": steps, "shortest": best, "excess_steps": excess,
                        "bumps": bumps, "size": item["size"],
                        "plan_ms": ts[0] if ts else None,
                        "move_ms": round(ts[-1] - ts[0], 1) if len(ts) > 1 else None,
                        "total_ms": ts[-1] if ts else None}}


def example_response(item, correct=True):
    moves = _path(item)
    if not correct:
        moves = moves[: len(moves) // 2]
    return {"moves": [{"d": d, "t": 3000 + 400 * i} for i, d in enumerate(moves)]}
