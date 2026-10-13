"""Packing puzzle (card 40): fill a small rectangular board with all the given polyomino
pieces, without overlap. Pieces may be rotated (not mirrored). A board is made by cutting
a rectangle into random connected pieces of 3-5 cells; each piece is then shown in a random
rotation and the pieces are shuffled. An exact-cover solver counts every solution, so the
board is verified solvable and any valid solution is accepted, not only the authored one.
Pairs (k, k+1) share the board size, the number of pieces and the multiset of piece
sizes, and have the same solver count of solutions (at most 8, i.e. only one or two
essentially different packings); pairs cycle through 3x4 (3 pieces), 4x4 (4 pieces) and 4x5 (5 pieces).
Geometry convention, shared with view.js: rotating once turns a piece 90 degrees clockwise,
(r, c) -> (c, -r), then cells are shifted so the smallest row and column are 0 and sorted
row-major; the piece's "anchor" is its first cell in that order, and placing a piece at
(row, col) puts the anchor on that board cell."""

LEVELS = ((3, 4, (4, 4, 4)), (4, 4, (4, 4, 4, 4)), (4, 5, (5, 5, 5, 5)))
LIMIT_MS = 90000
MAX_EVENTS = 1000
MAX_SOLUTIONS = 5000
MAX_PAIR_SOLUTIONS = 8   # counts include board symmetries and swaps of identical pieces


def _normal(cells):
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def _rotate(cells, k):
    cells = list(cells)
    for _ in range(k % 4):
        cells = [(c, -r) for r, c in cells]
    return _normal(cells)


def _orientations(piece):
    return sorted(set(_rotate(piece, k) for k in range(4)))


def _placed(piece, rot, row, col):
    shape = _rotate(piece, rot)
    ar, ac = shape[0]
    return [(row + r - ar, col + c - ac) for r, c in shape]


def count_solutions(rows, cols, pieces, cap=MAX_SOLUTIONS):
    """Exact cover by backtracking: fill the first empty cell (row-major) with some unused
    piece in some rotation whose anchor lands there. Returns the number of solutions (<= cap)."""
    orients = [_orientations(p) for p in pieces]
    grid = [[False] * cols for _ in range(rows)]
    used = [False] * len(pieces)
    found = [0]

    def first_empty():
        for r in range(rows):
            for c in range(cols):
                if not grid[r][c]:
                    return r, c
        return None

    def rec():
        if found[0] >= cap:
            return
        cell = first_empty()
        if cell is None:
            found[0] += 1
            return
        r, c = cell
        for i, opts in enumerate(orients):
            if used[i]:
                continue
            for shape in opts:
                ar, ac = shape[0]
                cells = [(r + dr - ar, c + dc - ac) for dr, dc in shape]
                if all(0 <= rr < rows and 0 <= cc < cols and not grid[rr][cc] for rr, cc in cells):
                    for rr, cc in cells:
                        grid[rr][cc] = True
                    used[i] = True
                    rec()
                    used[i] = False
                    for rr, cc in cells:
                        grid[rr][cc] = False
    rec()
    return found[0]


def _partition(rng, rows, cols, sizes):
    """Cut the board into connected pieces of the given sizes (random growth, retried)."""
    for _ in range(2000):
        free = {(r, c) for r in range(rows) for c in range(cols)}
        pieces = []
        ok = True
        for size in sizes:
            seed = min(free)
            piece = {seed}
            free.discard(seed)
            while len(piece) < size:
                front = sorted({(r + dr, c + dc) for r, c in piece for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))} & free)
                if not front:
                    ok = False
                    break
                nxt = rng.choice(front)
                piece.add(nxt)
                free.discard(nxt)
            if not ok:
                break
            pieces.append(piece)
        if ok and not free:
            return [_normal(p) for p in pieces]
    raise RuntimeError("partition failed")


def _make(rng, rows, cols, sizes, avoid, want=None):
    tries = 0
    while True:
        tries += 1
        pieces = _partition(rng, rows, cols, list(sizes))
        if any(_is_line(p) for p in pieces) and rng.random() < 0.7:
            continue  # keep straight bars rare: they make boards too easy
        key = tuple(sorted(min(_orientations(p)) for p in pieces))
        # Small boards have only a few distinct piece sets; once they are used up,
        # allow repeats (each is still shown in new rotations and order).
        if key in avoid and tries < 400:
            continue
        shown = [list(map(list, _rotate(p, rng.randrange(4)))) for p in pieces]
        rng.shuffle(shown)
        n_sol = count_solutions(rows, cols, [tuple(map(tuple, p)) for p in shown])
        if 1 <= n_sol <= MAX_PAIR_SOLUTIONS and (want is None or n_sol == want):
            avoid.add(key)
            return {"rows": rows, "cols": cols, "pieces": shown, "n_solutions": n_sol, "limit_ms": LIMIT_MS}


def _is_line(p):
    return len({r for r, _ in p}) == 1 or len({c for _, c in p}) == 1


def generate(rng, n, save_image):
    items, avoid = [], set()
    while len(items) < n:
        rows, cols, sizes = LEVELS[(len(items) // 2) % len(LEVELS)]
        first = _make(rng, rows, cols, sizes, avoid)
        items.append(first)
        items.append(_make(rng, rows, cols, sizes, avoid, want=first["n_solutions"]))
    return items[:n]


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def score(item, response):
    """response: {"events": [{"op": "place", "piece": i, "rot": 0-3, "row": r, "col": c, "t": ms}
    | {"op": "remove", "piece": i, "t": ms}], "first_move_ms", "rt_ms", "gave_up"}.
    The server replays the events on an empty board: a placement that is off the board,
    overlaps a placed piece, or uses an already-placed piece is an invalid attempt (counted,
    not applied); "remove" takes a placed piece back. hit = after the replay every piece is
    on the board and every cell is covered exactly once (any valid solution counts).
    errors = invalid placement attempts. Metrics: placements, removals, time."""
    miss = {"hit": False, "errors": 0, "metrics": {}}
    try:
        if not isinstance(response, dict):
            return miss
        rows, cols = item["rows"], item["cols"]
        pieces = [tuple(map(tuple, p)) for p in item["pieces"]]
        events = response.get("events")
        events = events if isinstance(events, list) else []
        where = {}          # piece -> list of cells
        occ = {}            # cell -> piece
        placements = invalid = removals = 0
        solved_at = None
        for ev in events[:MAX_EVENTS]:
            if not isinstance(ev, dict):
                invalid += 1
                continue
            i = ev.get("piece")
            if not _is_int(i) or not 0 <= i < len(pieces):
                invalid += 1
                continue
            if ev.get("op") == "remove":
                if i in where:
                    for cell in where.pop(i):
                        occ.pop(cell, None)
                    removals += 1
                continue
            rot, r, c = ev.get("rot"), ev.get("row"), ev.get("col")
            if ev.get("op") != "place" or not (_is_int(rot) and _is_int(r) and _is_int(c)) or i in where:
                invalid += 1
                continue
            cells = _placed(pieces[i], rot, r, c)
            if not all(0 <= rr < rows and 0 <= cc < cols and (rr, cc) not in occ for rr, cc in cells):
                invalid += 1
                continue
            where[i] = cells
            for cell in cells:
                occ[cell] = i
            placements += 1
            if len(occ) == rows * cols and solved_at is None:
                solved_at = _num(ev.get("t"))
        solved = len(where) == len(pieces) and len(occ) == rows * cols
        return {"hit": solved, "errors": invalid,
                "metrics": {"solved": solved, "placements": placements, "invalid_attempts": invalid,
                            "removals": removals, "pieces_placed": len(where), "pieces": len(pieces),
                            "cells_covered": len(occ), "cells": rows * cols,
                            "n_solutions": count_solutions(rows, cols, pieces),
                            "first_move_ms": _num(response.get("first_move_ms")),
                            "solve_ms": solved_at, "rt_ms": _num(response.get("rt_ms")),
                            "gave_up": response.get("gave_up") is True}}
    except Exception:
        return miss


def _one_solution(rows, cols, pieces):
    """First solution found by the solver, as placement events."""
    orients = [[(k, _rotate(p, k)) for k in range(4)] for p in pieces]
    grid = [[False] * cols for _ in range(rows)]
    used = [None] * len(pieces)

    def rec():
        cell = next(((r, c) for r in range(rows) for c in range(cols) if not grid[r][c]), None)
        if cell is None:
            return True
        r, c = cell
        for i, opts in enumerate(orients):
            if used[i] is not None:
                continue
            for k, shape in opts:
                ar, ac = shape[0]
                cells = [(r + dr - ar, c + dc - ac) for dr, dc in shape]
                if all(0 <= rr < rows and 0 <= cc < cols and not grid[rr][cc] for rr, cc in cells):
                    for rr, cc in cells:
                        grid[rr][cc] = True
                    used[i] = (k, r, c)
                    if rec():
                        return True
                    used[i] = None
                    for rr, cc in cells:
                        grid[rr][cc] = False
        return False
    rec()
    return used


def example_response(item, correct=True):
    pieces = [tuple(map(tuple, p)) for p in item["pieces"]]
    sol = _one_solution(item["rows"], item["cols"], pieces)
    events = [{"op": "place", "piece": i, "rot": k, "row": r, "col": c, "t": 3000 + 2000 * i}
              for i, (k, r, c) in enumerate(sol)]
    if not correct:
        events = events[:-1] + [{"op": "remove", "piece": 0, "t": 20000}]
    return {"events": events, "first_move_ms": 3000, "rt_ms": 25000, "gave_up": not correct}
