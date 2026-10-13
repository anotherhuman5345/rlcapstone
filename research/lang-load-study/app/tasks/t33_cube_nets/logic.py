"""Cube-net matching (card 33): a cube with a different original mark on each face is
shown from one corner (three faces visible). Which of four flat nets folds into this
cube? One trial = one cube and four nets; exactly one net is right.

Geometry: a net is 6 grid cells (one of the 11 cube nets, in any turn/flip) and each cell
carries a mark id and a quarter-turn r (0-3, clockwise) of that mark. The 3D solver folds
the net away from the viewer (printed side out), tracking every face's outward normal and
the direction its mark points; two cubes match when one of the 24 rotations of the cube
maps the three shown faces (mark and mark direction) onto the view. Marks have no
rotational symmetry, so a turned mark is a different face.

Every distractor is checked by the solver to fit NO rotation of the shown cube: each is the
cube unfolded onto another net shape and then broken in one way (a mark turned, two marks
swapped, or two faces exchanged), so a distractor is never just a turned copy of the key.
The key is not stored; score() folds the chosen net and compares it with the view.
All items have the same structure, so pairs (k, k+1) are matched by construction."""

from itertools import permutations, product

VIEW = ((1, 0, 0), (0, -1, 0), (0, 0, 1))  # faces seen from the corner (1, -1, 1)
MARKS = 6


def _neg(v):
    return (-v[0], -v[1], -v[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rotations():
    out = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            m = [[0] * 3 for _ in range(3)]
            for i in range(3):
                m[i][perm[i]] = signs[i]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det == 1:
                out.append(tuple(tuple(r) for r in m))
    return out


ROTATIONS = _rotations()


def _apply(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _frames(cells):
    """Fold a layout: {cell: (normal, u, w)}; u = net right, w = net down, seen from outside."""
    cells = [tuple(c) for c in cells]
    cellset = set(cells)
    frames = {cells[0]: ((0, 0, 1), (1, 0, 0), (0, -1, 0))}
    queue = [cells[0]]
    while queue:
        c = queue.pop(0)
        n, u, w = frames[c]
        for (dc, dr) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c[0] + dc, c[1] + dr)
            if nb not in cellset or nb in frames:
                continue
            if dc == 1:
                f = (u, _neg(n), w)
            elif dc == -1:
                f = (_neg(u), n, w)
            elif dr == 1:
                f = (w, u, _neg(n))
            else:
                f = (_neg(w), u, n)
            frames[nb] = f
            queue.append(nb)
    return frames


def _up_dirs(u, w):
    return [_neg(w), u, w, _neg(u)]  # mark turned 0, 90, 180, 270 degrees clockwise


def fold(net):
    """net: [[col, row, mark, r], ...] -> {normal: (mark, up)} or None if it is not a cube."""
    try:
        cells = [(int(c[0]), int(c[1])) for c in net]
        marks = [(int(c[2]), int(c[3]) % 4) for c in net]
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    if len(cells) != 6 or len(set(cells)) != 6:
        return None
    frames = _frames(cells)
    if len(frames) != 6:
        return None
    cube = {}
    for c, (m, r) in zip(cells, marks):
        n, u, w = frames[c]
        cube[n] = (m, _up_dirs(u, w)[r])
    return cube if len(cube) == 6 else None


def matches(cube, view):
    """True when some rotation of `cube` shows `view` ({normal: (mark, up)})."""
    if not cube:
        return False
    for q in ROTATIONS:
        rot = {_apply(q, n): (m, _apply(q, up)) for n, (m, up) in cube.items()}
        if all(rot.get(n) == v for n, v in view.items()):
            return True
    return False


def _norm(cells):
    mx = min(c for c, _ in cells)
    my = min(r for _, r in cells)
    return tuple(sorted((c - mx, r - my) for c, r in cells))


def _layouts():
    """All fixed hexominoes that fold into a cube (the 11 nets in every turn and flip)."""
    shapes = {((0, 0),)}
    for _ in range(5):
        grown = set()
        for s in shapes:
            for (c, r) in s:
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (c + dc, r + dr)
                    if nb not in s:
                        grown.add(_norm(s + (nb,)))
        shapes = grown
    out = []
    for s in sorted(shapes):
        cs = set(s)
        if any({(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)} <= cs for c, r in s):
            continue
        fr = _frames(list(s))
        if len({f[0] for f in fr.values()}) == 6:
            out.append(s)
    return out


LAYOUTS = _layouts()


def _unfold(cube, layout):
    frames = _frames(list(layout))
    net = []
    for c in layout:
        n, u, w = frames[c]
        m, up = cube[n]
        net.append([c[0], c[1], m, _up_dirs(u, w).index(up)])
    return net


def _random_cube(rng):
    normals = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    marks = list(range(MARKS))
    rng.shuffle(marks)
    cube = {}
    for n, m in zip(normals, marks):
        ups = [v for v in normals if v != n and v != _neg(n)]
        cube[n] = (m, rng.choice(ups))
    return cube


def _rotated(cube, q):
    return {_apply(q, n): (m, _apply(q, up)) for n, (m, up) in cube.items()}


def _break(net, kind, rng):
    net = [list(c) for c in net]
    if kind == "turn":
        c = rng.choice(net)
        c[3] = (c[3] + rng.choice((1, 2, 3))) % 4
    elif kind == "swap_marks":
        a, b = rng.sample(range(6), 2)
        net[a][2], net[b][2] = net[b][2], net[a][2]
    else:  # exchange two whole faces (mark and its turn)
        a, b = rng.sample(range(6), 2)
        net[a][2:], net[b][2:] = net[b][2:], net[a][2:]
    return net


def _puzzle(rng):
    cube = _random_cube(rng)
    view = {n: cube[n] for n in VIEW}
    shapes = rng.sample(LAYOUTS, 4)
    key_net = _unfold(_rotated(cube, rng.choice(ROTATIONS)), shapes[0])
    options = [key_net]
    for kind, shape in zip(("turn", "swap_marks", rng.choice(("exchange", "turn"))), shapes[1:]):
        while True:
            net = _break(_unfold(_rotated(cube, rng.choice(ROTATIONS)), shape), kind, rng)
            if fold(net) and not matches(fold(net), view) and net not in options:
                options.append(net)
                break
    rng.shuffle(options)
    return {"view": [[list(n), m, list(up)] for n, (m, up) in view.items()], "options": options}


def generate(rng, n, save_image):
    return [_puzzle(rng) for _ in range(n)]


def _view(item):
    return {tuple(n): (m, tuple(up)) for n, m, up in item["view"]}


def score(item, response):
    """response: {"choice": option index 0-3 or null, "rt": ms from Start}.
    hit = the chosen net folds (3D solver) into a cube that some rotation turns into the
    shown view. Metrics: correct, rt (correct only), rt_any, omission, valid_options (how
    many of the four nets fit the view; always 1 for a well-formed item)."""
    view = _view(item)
    c, rt = (response.get("choice"), response.get("rt")) if isinstance(response, dict) else (None, None)
    c = c if isinstance(c, int) and not isinstance(c, bool) and 0 <= c < len(item["options"]) else None
    rt = rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0 else None
    ok = c is not None and matches(fold(item["options"][c]), view)
    return {"hit": ok, "errors": 0 if ok else 1,
            "metrics": {"correct": ok, "rt": rt if ok else None, "rt_any": rt, "omission": c is None,
                        "valid_options": sum(matches(fold(o), view) for o in item["options"])}}


def example_response(item, correct=True):
    view = _view(item)
    fits = [matches(fold(o), view) for o in item["options"]]
    return {"choice": fits.index(True) if correct else fits.index(False), "rt": 12000}
