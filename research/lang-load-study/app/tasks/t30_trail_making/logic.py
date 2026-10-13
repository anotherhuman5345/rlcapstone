"""Trail-making style (card 30): click 13 circles in order as fast as possible.
Condition "numbers": 1-2-3-...-13. Condition "alternating": 1-J-2-K-3-L-...-6-O-7
(numbers 1-7 alternate with letters J-O). Letters J K L M N O are used because they are
familiar in both English and Turkish AND consecutive in both alphabets (A-H would not
be: Turkish has C-Ç-D and G-Ğ-H). Both conditions have 13 nodes.
Layouts are random but checked (minimum spacing; the ideal path never passes close to
another node). The two items of a pair have the same condition and mirror-image
layouts (same path length and geometry); pairs alternate numbers / alternating.
Nodes are stored in screen order (top-to-bottom), not in answer order, so the keyboard
Tab order does not reveal the sequence; score() derives the order from the labels.
This is not the normed clinical Trail Making Test."""
import math

from app.tasks import _guard as G

TIMING = "limit"        # the click that connects the last node must come inside LIMIT_MS
CEILING_MS = G.trial_ceiling(__file__)
TIME_SLACK_MS = 1000    # timer tolerance at the limit
MAX_CLICKS = 2000
N_NODES = 13
LETTERS = ["J", "K", "L", "M", "N", "O"]
W, H = 1200, 800
MIN_DIST = 165
PATH_CLEAR = 60
LIMIT_MS = 100000       # item["limit_ms"]; view.js: deadline = setTimeout(() => end(true), it.limit_ms)


def expected_labels(condition, n=N_NODES):
    if condition == "numbers":
        return [str(i + 1) for i in range(n)]
    seq = []
    for i in range(n):
        seq.append(str(i // 2 + 1) if i % 2 == 0 else LETTERS[i // 2])
    return seq


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L)) if L else 0.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _layout(rng):
    while True:
        pts = []
        tries = 0
        while len(pts) < N_NODES and tries < 5000:
            tries += 1
            p = (rng.uniform(0.06, 0.94) * W, rng.uniform(0.08, 0.92) * H)
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= MIN_DIST for q in pts):
                pts.append(p)
        if len(pts) < N_NODES:
            continue
        ok = all(_seg_dist(pts[j], pts[i], pts[i + 1]) >= PATH_CLEAR
                 for i in range(N_NODES - 1) for j in range(N_NODES) if j not in (i, i + 1))
        if ok:
            return pts


def _item(condition, pts):
    labels = expected_labels(condition)
    nodes = [{"x": round(x / W, 4), "y": round(y / H, 4), "label": lab} for (x, y), lab in zip(pts, labels)]
    nodes.sort(key=lambda d: (round(d["y"], 1), d["x"]))
    return {"condition": condition, "nodes": nodes, "limit_ms": LIMIT_MS}


def generate(rng, n, save_image):
    items = []
    p = 0
    while len(items) < n:
        cond = "numbers" if p % 2 == 0 else "alternating"
        pts = _layout(rng)
        items.append(_item(cond, pts))
        items.append(_item(cond, [(W - x, y) for x, y in pts]))
        p += 1
    return items[:n]


def _path(nodes, idxs):
    return round(sum(math.hypot((nodes[a]["x"] - nodes[b]["x"]) * W, (nodes[a]["y"] - nodes[b]["y"]) * H)
                     for a, b in zip(idxs, idxs[1:])), 1)


@G.safe
def score(item, response):
    """response: {"clicks": [{"node": index into item["nodes"], "t": ms since Start}],
    "finished": bool}.
    Oracle: the next correct node is the one whose label is next in expected_labels().
    A click on any other node is a wrong click (not advancing). The browser never records a
    repeat click on the node just connected, nor any click after the last node is connected:
    such clicks are flagged and ignored. Malformed clicks (not an object, a node that is not
    an index into item["nodes"], a missing/invalid time) are flagged and not applied; click
    times must not go backwards (flagged).
    hit = all 13 nodes connected in order AND the click that connected the last node has a
    valid time inside the 100 s limit (a missing, non-finite, negative or late time never
    counts). The browser's own "finished" field is not trusted (a mismatch is flagged).
    Metrics: completion time (ms to last correct click), wrong clicks, nodes connected,
    ideal path length and the participant's click-path length (both in 1200x800 px)."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    nodes = item["nodes"]
    order_labels = expected_labels(item["condition"], len(nodes))
    by_label = {d["label"]: i for i, d in enumerate(nodes)}
    order = [by_label[lab] for lab in order_labels]
    clicks = a.stream(response.get("clicks", G.MISSING), "clicks", cap=MAX_CLICKS)
    ptr, wrong, last, visited, times, after = 0, 0, None, [], [], 0
    for c in clicks:
        if ptr >= len(order):
            after += 1
            continue
        if not isinstance(c, dict):
            a.malformed("click_not_object")
            continue
        st, t = a.time(c.get("t", G.MISSING), field="t", window=LIMIT_MS, slack=TIME_SLACK_MS,
                       required=True)
        times.append(t if st != G.INVALID else None)
        node = c.get("node")
        if not G.member(node, range(len(nodes))):
            a.malformed("invalid_node")
            continue
        if ptr > 0 and node == order[ptr - 1]:
            a.flag("repeat_click")
            continue
        visited.append(node)
        if node == order[ptr]:
            ptr += 1
            last = (st, t)
        else:
            wrong += 1
    if after:
        a.flag("clicks_after_completion", after)
    a.monotonic(times, "t")
    connected = ptr == len(order)
    timely = last is not None and last[0] == G.TIMELY
    done = connected and timely
    if connected and not timely:
        a.flag("completed_outside_time_limit")
    finished = a.opt_bool(response, "finished")
    if finished is not None and finished != connected:
        a.flag("finished_mismatch")
    return a.finish(done, wrong, {
        "condition": item["condition"], "completed": done, "nodes_connected": ptr,
        "completion_time_ms": round(last[1], 1) if done else None,
        "wrong_clicks": wrong,
        "ideal_path_px": _path(nodes, order),
        "click_path_px": _path(nodes, visited) if len(visited) > 1 else 0.0})


def example_response(item, correct=True):
    labels = expected_labels(item["condition"], len(item["nodes"]))
    by_label = {d["label"]: i for i, d in enumerate(item["nodes"])}
    order = [by_label[lab] for lab in labels]
    if correct:
        clicks = [{"node": i, "t": 1500 * (k + 1)} for k, i in enumerate(order)]
        clicks.insert(3, {"node": order[5], "t": 5000})  # one wrong click still completes
    else:
        clicks = [{"node": i, "t": 1500 * (k + 1)} for k, i in enumerate(order[:6])]
    return {"clicks": clicks, "finished": correct}
