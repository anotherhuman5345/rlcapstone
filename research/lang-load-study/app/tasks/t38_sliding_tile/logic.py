"""Sliding-tile puzzle (card 38): a 3x3 board with tiles 1-8 and one gap. Slide tiles next
to the gap until the board reads 1-8 in order with the gap last. Boards are scrambled from
the goal by random legal moves (so every board is reachable); the true minimum number of
moves is then found by breadth-first search (the scramble length is not assumed optimal).
Pairs (k, k+1) are two different boards with the same minimum (8 or 10 moves, alternating
across pairs). The server replays every recorded tile press itself."""
import functools
from collections import deque

from app.tasks import _guard as G

TIMING = "limit"      # the solving slide must come inside LIMIT_MS
N = 3
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
LEVELS = (8, 10)
LIMIT_MS = 90000      # view.js: setTimeout(() => end(true, false), it.limit_ms || 90000)
MAX_EVENTS = 2000
TIME_SLACK_MS = 1000  # timer tolerance at the limit
CEILING_MS = G.trial_ceiling(__file__)


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


@functools.lru_cache(maxsize=256)
def _optimal(start):
    """BFS minimum for a start board (tuple); memoized per item."""
    return len(_solve(start))


def _replay(start, events, a):
    """Replay the events from the start board. Malformed events (not an object, a tile that
    is not an integer 0-8, a bad reset marker, a missing/invalid time) are flagged and not
    applied; a well-formed press of a tile that cannot move (0 = arrow key with no tile) is
    an illegal attempt. The browser locks the board once it is solved, so any event after
    that is flagged. Returns (state, moves, illegal, malformed, resets, final_t) where
    final_t is (status, t) of the event that produced the final board (None if unknown)."""
    state, moves, illegal, malformed, resets = start, 0, 0, 0, 0
    final_t, reached, times, after_solve = None, False, [], 0
    for ev in events:
        if reached:
            after_solve += 1
        if not isinstance(ev, dict):
            a.malformed("event_not_object")
            malformed += 1
            continue
        st, t = a.time(ev.get("t", G.MISSING), field="t", window=LIMIT_MS, slack=TIME_SLACK_MS, required=True)
        times.append(t if st != G.INVALID else None)
        if "reset" in ev:
            if ev.get("reset") is not True or "tile" in ev:
                a.malformed("invalid_reset")
                malformed += 1
                continue
            state, resets = start, resets + 1
            final_t = (st, t)
            continue
        tile = ev.get("tile")
        if not G.member(tile, range(N * N)):
            a.malformed("invalid_tile")
            malformed += 1
            continue
        nxt = _slide(state, tile)
        if nxt is None:
            illegal += 1
            continue
        state, moves = nxt, moves + 1
        final_t = (st, t)
        reached = reached or state == GOAL
    if after_solve:
        a.flag("events_after_solve", after_solve)
    a.monotonic(times, "t")
    return state, moves, illegal, malformed, resets, final_t


@G.safe
def score(item, response):
    """response: {"events": [{"tile": 1-8, "t": ms} | {"reset": true, "t": ms}], "first_move_ms",
    "rt_ms", "gave_up"}; arrow keys are sent as the tile they move (0 if no tile can move that
    way). The server replays the events: pressing a tile that is not next to the gap is an
    illegal attempt (counted, not applied); a reset restores the start board; malformed
    events are flagged and not applied.
    hit = the final board is the goal (1-8 in order, gap last) AND the slide that produced it
    has a valid time inside the 90 s limit (a missing, non-finite, negative or late time does
    not count). Metrics: moves, excess over the BFS minimum, illegal attempts, resets,
    first-move and solve times. errors = illegal attempts + malformed events."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    start = tuple(item["start"])
    optimal = _optimal(start)
    events = a.stream(response.get("events", G.MISSING), "events", cap=MAX_EVENTS)
    state, moves, illegal, malformed, resets, final_t = _replay(start, events, a)
    at_goal = state == GOAL
    timely = final_t is not None and final_t[0] == G.TIMELY
    solved = at_goal and timely
    if at_goal and not timely:
        a.flag("solved_outside_time_limit")
    return a.finish(solved, illegal + malformed, {
        "solved": solved, "moves": moves, "optimal": optimal,
        "excess_moves": moves - optimal if solved else None,
        "illegal_attempts": illegal, "malformed_events": malformed, "resets": resets,
        "first_move_ms": a.duration(response, "first_move_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "solve_ms": final_t[1] if solved else None,
        "rt_ms": a.duration(response, "rt_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "gave_up": a.opt_bool(response, "gave_up")})


def example_response(item, correct=True):
    path = _solve(item["start"])
    if not correct:
        path = path[:-1]
    events = [{"tile": t, "t": 2000 + 900 * k} for k, t in enumerate(path)]
    return {"events": events, "first_move_ms": 2000, "rt_ms": 2000 + 900 * len(path), "gave_up": not correct}
