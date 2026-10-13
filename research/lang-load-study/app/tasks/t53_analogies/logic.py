"""Visual analogies (card 53, visual mode only - no words, so nothing to mistranslate):
"A is to B as C is to ?". A changes into B by one or two picture operations; choose the
one of 4 options that shows C changed in the same way. Shapes are original asymmetric
polygons (no rotation or mirror symmetry, checked at import), so every operation is
visible and unambiguous.

Operations: rot90 (quarter turn clockwise), rot180 (half turn), mirror (left-right flip),
fill (solid <-> outline), size (large <-> small), count (one more copy). When fill or size
is used, C starts with the same fill / size as A, so the change has one direction.
One trial = 4 problems: 2 with one operation, 2 with two operations, shuffled. Both items
of a pair (k, k+1) use the same operations in the same positions, with other shapes.

Answer key (oracle, in score()): every sequence of 1 or 2 different operations is tried
on A; each sequence that reproduces B exactly (compared as geometry: transformed polygon
points + fill + count) is applied to C, and an option is correct if it equals one of those
results. The generator only keeps problems where exactly one option is correct. Distractors
are C with other operations (for two-operation problems, including each single half).
"""
import itertools
import statistics

BASE = {  # original polygons in [-1, 1]^2, screen coordinates (y down)
    "flag": [(-0.6, 1.0), (-0.6, -1.0), (0.8, -0.55), (-0.3, -0.05), (-0.3, 1.0)],
    "boot": [(-0.6, -1.0), (-0.1, -1.0), (-0.1, 0.4), (0.9, 0.4), (0.9, 1.0), (-0.6, 1.0)],
    "notch": [(-1.0, -0.6), (1.0, -0.2), (1.0, 0.6), (0.2, 0.6), (0.2, 0.1), (-1.0, 0.1)],
    "dart": [(-1.0, -0.3), (0.3, -0.3), (0.3, -0.85), (1.0, 0.1), (0.05, 0.8), (0.05, 0.3), (-1.0, 0.3)],
    "step": [(-0.9, 0.8), (-0.5, -0.8), (0.4, -0.8), (0.4, -0.3), (0.9, -0.3), (0.9, 0.8)],
    "kite": [(0.0, -1.0), (0.7, -0.1), (0.2, 1.0), (-0.4, 0.3), (-0.9, 0.2)],
}
OPS = ["rot90", "rot180", "mirror", "fill", "size", "count"]
MAX_COUNT = 3


def geometry(st):
    """Polygon points after mirror, then quarter turns clockwise, then size."""
    sc = 1.0 if st["big"] else 0.55
    pts = []
    for x, y in BASE[st["shape"]]:
        if st["mir"]:
            x = -x
        for _ in range(st["rot"] % 4):
            x, y = -y, x
        pts.append((round(x * sc, 3) + 0.0, round(y * sc, 3) + 0.0))
    return pts


def key(st):
    return (frozenset(geometry(st)), bool(st["fill"]), st["count"])


def apply(op, st):
    s = dict(st)
    if op == "rot90":
        s["rot"] = (s["rot"] + 1) % 4
    elif op == "rot180":
        s["rot"] = (s["rot"] + 2) % 4
    elif op == "mirror":  # flipping after rotating = mirror first, then the opposite turn
        s["mir"] = not s["mir"]
        s["rot"] = (-s["rot"]) % 4
    elif op == "fill":
        s["fill"] = not s["fill"]
    elif op == "size":
        s["big"] = not s["big"]
    elif op == "count":
        if s["count"] >= MAX_COUNT:
            return None
        s["count"] += 1
    return s


def apply_seq(seq, st):
    for op in seq:
        if st is None:
            return None
        st = apply(op, st)
    return st


def all_seqs():
    return [(o,) for o in OPS] + list(itertools.permutations(OPS, 2))


def accepted(a, b, c):
    """Oracle: keys of every C' = T(C) for each operation sequence T with T(A) == B."""
    kb, out = key(b), set()
    for seq in all_seqs():
        ta = apply_seq(seq, a)
        if ta is not None and key(ta) == kb:
            tc = apply_seq(seq, c)
            if tc is not None:
                out.add(key(tc))
    return out


def _check_asymmetric():
    for name in BASE:
        keys = {key({"shape": name, "rot": r, "mir": m, "big": True, "fill": False, "count": 1})
                for r in range(4) for m in (False, True)}
        assert len(keys) == 8, f"shape {name} has a symmetry"


_check_asymmetric()


def _state(rng, shape):
    return {"shape": shape, "rot": rng.randrange(4), "mir": rng.random() < 0.5, "big": rng.random() < 0.5,
            "fill": rng.random() < 0.5, "count": rng.randint(1, 2)}


def _fig(st):
    return {"state": st, "pts": [list(p) for p in geometry(st)], "fill": st["fill"], "count": st["count"]}


def _problem(rng, seq):
    while True:
        sa, sc = rng.sample(sorted(BASE), 2)
        a, c = _state(rng, sa), _state(rng, sc)
        # fill and size are toggles: C starts like A so "becomes small" and "toggles size"
        # (or "becomes outlined" and "toggles fill") always mean the same answer
        if "fill" in seq:
            c["fill"] = a["fill"]
        if "size" in seq:
            c["big"] = a["big"]
        b, d = apply_seq(seq, a), apply_seq(seq, c)
        if b is None or d is None:
            continue
        acc = accepted(a, b, c)
        if acc != {key(d)}:
            continue
        # near misses first: each half of a two-step change, and C unchanged
        near = ([(o,) for o in seq] if len(seq) == 2 else []) + [()]
        others = [s for s in all_seqs() if s != seq]
        rng.shuffle(others)
        dis, seen = [], {key(d)}
        for s in near + others:
            st = apply_seq(s, c)
            if st is None or key(st) in seen or key(st) in acc:
                continue
            seen.add(key(st))
            dis.append(st)
            if len(dis) == 3:
                break
        if len(dis) < 3:
            continue
        opts = [d] + dis
        rng.shuffle(opts)
        return {"ops": list(seq), "a": _fig(a), "b": _fig(b), "c": _fig(c), "options": [_fig(o) for o in opts]}


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        singles = rng.sample(OPS, 2)
        doubles = []
        while len(doubles) < 2:
            pair = tuple(rng.sample(OPS, 2))
            both_turns = set(pair) == {"rot90", "rot180"}  # would look like one turn
            if not both_turns and all(set(pair) != set(d) for d in doubles):
                doubles.append(pair)
        plan = [(s,) for s in singles] + doubles
        rng.shuffle(plan)
        for _ in range(2):
            items.append({"problems": [_problem(rng, seq) for seq in plan]})
    return items[:n]


def correct_options(p):
    acc = accepted(p["a"]["state"], p["b"]["state"], p["c"]["state"])
    return [i for i, o in enumerate(p["options"]) if key(o["state"]) in acc]


def score(item, response):
    """response: [{"choice": 0-3 | null, "rt": ms}] in problem order (choice = option index).
    hit = at least 3 of the 4 problems correct (chance is 1/4 per problem)."""
    probs = item.get("problems", []) if isinstance(item, dict) else []
    resp = response if isinstance(response, list) else []
    rows = []
    for k, p in enumerate(probs):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        ch = r.get("choice")
        ch = ch if isinstance(ch, int) and not isinstance(ch, bool) and 0 <= ch < len(p["options"]) else None
        ok = ch is not None and ch in correct_options(p)
        rt = r.get("rt") if isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) else None
        partial = False
        if ch is not None and not ok and len(p["ops"]) == 2:
            ck = key(p["options"][ch]["state"])
            partial = any(key(apply(o, p["c"]["state"]) or p["c"]["state"]) == ck for o in p["ops"])
        rows.append({"n_ops": len(p["ops"]), "ops": "+".join(p["ops"]), "ok": ok, "rt": rt,
                     "omit": ch is None, "partial": partial})
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"]]

    def acc(sel):
        return round(sum(r["ok"] for r in sel) / len(sel), 3) if sel else None
    return {"hit": bool(rows) and n_ok >= 3, "errors": len(rows) - n_ok,
            "metrics": {"accuracy": acc(rows),
                        "accuracy_one_op": acc([r for r in rows if r["n_ops"] == 1]),
                        "accuracy_two_ops": acc([r for r in rows if r["n_ops"] == 2]),
                        "correct_by_relation": {r["ops"]: r["ok"] for r in rows},
                        "partial_errors": sum(r["partial"] for r in rows),
                        "median_rt_correct": round(statistics.median(rts), 1) if rts else None,
                        "omissions": sum(r["omit"] for r in rows)}}


def example_response(item, correct=True):
    out = []
    for p in item["problems"]:
        good = correct_options(p)
        ch = good[0] if correct else next(i for i in range(len(p["options"])) if i not in good)
        out.append({"choice": ch, "rt": 6000})
    return out
