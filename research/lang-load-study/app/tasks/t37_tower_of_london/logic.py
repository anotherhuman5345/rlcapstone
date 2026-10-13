"""Tower of London style (card 37): three coloured balls sit on three pegs that hold at most
3, 2 and 1 balls. Move one top ball at a time until the pegs match the target picture.
Start and target positions are drawn at random (original configurations, not a published
item set) and a breadth-first search over all 36 positions gives the minimum number of
moves. Pairs (k, k+1) are two different puzzles with the same minimum; the minimum varies
across pairs (3, 4, 5, 6 moves). The server replays every recorded event itself."""
import functools
import json
from collections import deque
from itertools import permutations

from app.tasks import _guard as G

TIMING = "limit"      # the solving move must come inside LIMIT_MS
CAPS = (3, 2, 1)
BALLS = 3
LIMIT_MS = 90000      # view.js: setTimeout(() => end(true, false), it.limit_ms || 90000)
MAX_EVENTS = 1000
TIME_SLACK_MS = 1000  # timer tolerance at the limit
CEILING_MS = G.trial_ceiling(__file__)
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


@functools.lru_cache(maxsize=256)
def _optimal(key):
    start, goal = json.loads(key)
    return len(_bfs(start, goal))


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


def _replay(start, goal, events, a):
    """Replay the event list from the start position. Malformed events (not an object, pegs
    that are not integers 0-2, a bad reset marker, a missing/invalid time) are flagged and
    not applied; well-formed moves that break the rules are illegal attempts. The browser
    locks the board once the target is reached, so any event after that is flagged.
    Returns (state, moves, illegal, malformed, resets, final_t) where final_t is
    (status, t) of the event that produced the final position (None if unknown)."""
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
            if ev.get("reset") is not True or "from" in ev or "to" in ev:
                a.malformed("invalid_reset")
                malformed += 1
                continue
            state, resets = start, resets + 1
            final_t = (st, t)
            continue
        f, to = ev.get("from"), ev.get("to")
        if not (G.member(f, range(3)) and G.member(to, range(3))):
            a.malformed("invalid_move")
            malformed += 1
            continue
        nxt = _move(state, f, to)
        if nxt is None:
            illegal += 1
            continue
        state, moves = nxt, moves + 1
        final_t = (st, t)
        reached = reached or state == goal
    if after_solve:
        a.flag("events_after_solve", after_solve)
    a.monotonic(times, "t")
    return state, moves, illegal, malformed, resets, final_t


@G.safe
def score(item, response):
    """response: {"events": [{"from": peg, "to": peg, "t": ms} | {"reset": true, "t": ms}],
    "first_move_ms", "rt_ms", "gave_up"}; pegs 0-2 (capacities 3, 2, 1), times from Start.
    The server replays the events from the start position: an attempt from an empty peg,
    onto a full peg or onto the same peg is an illegal attempt (counted, not applied); a
    reset restores the start; malformed events are flagged and not applied.
    hit = the final position equals the target position AND the move that produced it has
    a valid time inside the 90 s limit (a solve with a missing, non-finite, negative or
    late time does not count). Planning quality is in the metrics: moves, excess over the
    BFS minimum, "perfect" (solved in exactly the minimum with no reset), planning latency
    (first_move_ms). errors = illegal attempts + malformed events."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    start, goal = _norm(item["start"]), _norm(item["goal"])
    optimal = _optimal(json.dumps([item["start"], item["goal"]]))
    events = a.stream(response.get("events", G.MISSING), "events", cap=MAX_EVENTS)
    state, moves, illegal, malformed, resets, final_t = _replay(start, goal, events, a)
    at_goal = state == goal
    timely = final_t is not None and final_t[0] == G.TIMELY
    solved = at_goal and timely
    if at_goal and not timely:
        a.flag("solved_outside_time_limit")
    return a.finish(solved, illegal + malformed, {
        "solved": solved, "moves": moves, "optimal": optimal,
        "excess_moves": moves - optimal if solved else None,
        "perfect": solved and moves == optimal and resets == 0,
        "illegal_attempts": illegal, "malformed_events": malformed, "resets": resets,
        "first_move_ms": a.duration(response, "first_move_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "solve_ms": final_t[1] if solved else None,
        "rt_ms": a.duration(response, "rt_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "gave_up": a.opt_bool(response, "gave_up")})


def example_response(item, correct=True):
    path = _bfs(item["start"], item["goal"])
    if not correct:
        path = path[:-1]
    events = [{"from": a, "to": b, "t": 4000 + 1500 * k} for k, (a, b) in enumerate(path)]
    return {"events": events, "first_move_ms": 4000, "rt_ms": 4000 + 1500 * len(path), "gave_up": not correct}
