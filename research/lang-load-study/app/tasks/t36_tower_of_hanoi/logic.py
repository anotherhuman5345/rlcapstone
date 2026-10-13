"""Tower of Hanoi (card 36): move a 3-disk tower to the target peg; a larger disk may never
rest on a smaller one. One trial is one puzzle. Even pairs use the standard setup (whole
tower on one peg -> another peg, optimum 2^3-1 = 7 moves) with different start/target pegs;
odd pairs start from a scattered legal position and need the whole tower on a target peg,
with both items of the pair at the same breadth-first-search optimum. The browser blocks
illegal moves but reports every attempt; the server replays the whole event list itself."""
from collections import deque

from app.tasks import _guard as G

TIMING = "limit"      # the solving move must come inside LIMIT_MS (see _guard.py)
DISKS = 3
PEGS = 3
LIMIT_MS = 90000      # the view ends the puzzle itself after this (task.json timeout is larger)
MAX_EVENTS = 1000
TIME_SLACK_MS = 1000  # timer tolerance at the limit
CEILING_MS = G.trial_ceiling(__file__)


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


def _replay(item, events, a):
    """Replay the event list from the start position. Malformed events (not an object, pegs
    that are not integers 0-2, a bad reset marker, a missing/invalid time) are flagged and
    not applied; well-formed moves that break the rules are illegal attempts.
    Returns (state, moves, illegal, malformed, resets, since_reset, final_t) where final_t
    is the time of the event that produced the final position (None if unknown)."""
    start = tuple(item["start"])
    state, moves, illegal, malformed, resets, since_reset = start, 0, 0, 0, 0, 0
    final_t, times = None, []
    for ev in events:
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
            state, resets, since_reset = start, resets + 1, 0
            final_t = (st, t)
            continue
        f, to = ev.get("from"), ev.get("to")
        if not (G.member(f, range(PEGS)) and G.member(to, range(PEGS))):
            a.malformed("invalid_move")
            malformed += 1
            continue
        nxt = _move(state, f, to)
        if nxt is None:
            illegal += 1
            continue
        state, moves, since_reset = nxt, moves + 1, since_reset + 1
        final_t = (st, t)
    a.monotonic(times, "t")
    return state, moves, illegal, malformed, resets, since_reset, final_t


@G.safe
def score(item, response):
    """response: {"events": [{"from": peg, "to": peg, "t": ms} | {"reset": true, "t": ms}],
    "first_move_ms", "rt_ms", "gave_up"}; pegs are 0-2, times from the Start press.
    The server replays the events from the start position: illegal attempts (empty source
    peg, larger disk onto smaller, same peg) are counted and not applied; a reset returns
    to the start position; malformed events are flagged and not applied.
    hit = the final position is the goal position (the tower is complete on the target
    peg) AND the move that completed it has a valid time inside the 90 s limit (a solve
    with a missing, non-finite, negative or late time does not count), regardless of how
    many moves it took; efficiency is in the metrics (moves, excess over the BFS optimum,
    illegal attempts, resets, times).
    errors = illegal attempts + malformed events."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    optimal = len(_bfs(item["start"], item["goal"]))
    events = a.stream(response.get("events", G.MISSING), "events", cap=MAX_EVENTS)
    state, moves, illegal, malformed, resets, since_reset, final_t = _replay(item, events, a)
    at_goal = state == tuple(item["goal"])
    timely = final_t is not None and final_t[0] == G.TIMELY
    solved = at_goal and timely
    if at_goal and not timely:
        a.flag("solved_outside_time_limit")
    return a.finish(solved, illegal + malformed, {
        "solved": solved, "moves": moves, "optimal": optimal,
        "excess_moves": moves - optimal if solved else None,
        "moves_after_last_reset": since_reset,
        "illegal_attempts": illegal, "malformed_events": malformed, "resets": resets,
        "first_move_ms": a.duration(response, "first_move_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "solve_ms": final_t[1] if solved else None,
        "rt_ms": a.duration(response, "rt_ms", window=LIMIT_MS + TIME_SLACK_MS),
        "gave_up": a.opt_bool(response, "gave_up")})


def example_response(item, correct=True):
    path = _bfs(item["start"], item["goal"])
    if not correct:
        path = path[:-1]
    events = [{"from": a, "to": b, "t": 1500 + 1200 * k} for k, (a, b) in enumerate(path)]
    return {"events": events, "first_move_ms": 1500, "rt_ms": 1500 + 1200 * len(path), "gave_up": not correct}
