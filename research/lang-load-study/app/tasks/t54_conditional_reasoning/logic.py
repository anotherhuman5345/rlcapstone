"""Conditional reasoning (card 54): an if-then rule is written in words (sentences built
only from phrases stored in text/<lang>.json, negation stored as its own phrase), and
shapes are shown one at a time. For each shape answer "follows" or "breaks".

Shapes have three two-valued features: colour (red/blue), form (circle/square),
size (large/small). A literal is {"attr", "val", "neg"}; a rule is {"p": lit, "q": lit}.

One trial = 2 parts, 4 shapes each (8 judgements):
  part 1  one rule; the 4 shapes cover the 4 truth-table rows TT, TF, FT, FF of (P, Q).
          FT (P false, Q true) follows the rule under implication but would break it
          under "if and only if" - the key implication-vs-equivalence probe.
  part 2  two rules; one shape breaks only rule 1, one breaks only rule 2, one follows
          both with a false antecedent and true consequent (FT), one follows both.
Negation pattern (none / in the if-part / in the then-part, for each of the 3 rules) is
drawn per pair and used by both items of the pair (k, k+1), with different features and shapes.

Answer key (oracle, in score()): truth table - a shape follows a rule unless P is true
and Q is false; it follows a part's rules only if it follows every rule.
"""
from app.tasks import _guard as G

TIMING = "untimed"   # view.js answer() has no time limit; rt is descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)

ATTRS = {"color": ["red", "blue"], "shape": ["circle", "square"], "size": ["big", "small"]}
NEG_PATTERNS = ["none", "if", "then"]


def holds(lit, obj):
    return (obj.get(lit["attr"]) == lit["val"]) != bool(lit["neg"])


def follows(rules, obj):
    """Truth-table oracle: material implication for every rule."""
    return all((not holds(r["p"], obj)) or holds(r["q"], obj) for r in rules)


def _lit(rng, attr, neg):
    return {"attr": attr, "val": rng.choice(ATTRS[attr]), "neg": neg}


def _rule(rng, a1, a2, pattern):
    return {"p": _lit(rng, a1, pattern == "if"), "q": _lit(rng, a2, pattern == "then")}


def _all_objects():
    return [{"color": c, "shape": s, "size": z} for c in ATTRS["color"] for s in ATTRS["shape"] for z in ATTRS["size"]]


def _row(rule, obj):
    return ("T" if holds(rule["p"], obj) else "F") + ("T" if holds(rule["q"], obj) else "F")


def _part1(rng, pattern):
    a1, a2 = rng.sample(list(ATTRS), 2)
    rule = _rule(rng, a1, a2, pattern)
    objs = _all_objects()
    cases = []
    for row in ["TT", "TF", "FT", "FF"]:
        cases.append({"obj": rng.choice([o for o in objs if _row(rule, o) == row]), "row": row})
    rng.shuffle(cases)
    return {"rules": [rule], "cases": cases}


def _part2(rng, pattern, pattern2):
    while True:
        x, y, z = rng.sample(list(ATTRS), 3)
        r1 = _rule(rng, x, y, pattern)
        r2 = _rule(rng, z, rng.choice([x, y]), pattern2)
        objs = _all_objects()
        only1 = [o for o in objs if not follows([r1], o) and follows([r2], o)]
        only2 = [o for o in objs if follows([r1], o) and not follows([r2], o)]
        ok = [o for o in objs if follows([r1, r2], o)]
        trap = [o for o in ok if "FT" in (_row(r1, o), _row(r2, o))]
        if only1 and only2 and trap and len(ok) >= 2:
            t = rng.choice(trap)
            other = rng.choice([o for o in ok if o != t])
            cases = [{"obj": rng.choice(only1), "row": "breaks_1"}, {"obj": rng.choice(only2), "row": "breaks_2"},
                     {"obj": t, "row": "follows_ft"}, {"obj": other, "row": "follows"}]
            rng.shuffle(cases)
            return {"rules": [r1, r2], "cases": cases}


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        p1, p2 = rng.choice(NEG_PATTERNS), rng.choice(NEG_PATTERNS)
        p3 = "none" if p2 == "none" else rng.choice(["if", "then"])
        for _ in range(2):
            items.append({"parts": [_part1(rng, p1), _part2(rng, p2, p3)], "negation": [p1, p2, p3]})
    return items[:n]


@G.safe
def score(item, response):
    """response: [{"choice": "follows" | "breaks" | null, "rt": ms}] for the 8 shapes in
    order (part 1 then part 2), one entry per shape (missing entries are omissions, extra
    ones ignored; both flagged). Any other choice value is flagged and scored wrong.
    hit = at least 6 of 8 judgements correct (75 %); the key is recomputed from the rules
    by the truth-table oracle follows().
    "equivalence_errors" counts FT shapes (rule follows by implication) marked "breaks".
    Judging is unspeeded: rt is descriptive, checked (finite, >= 100 ms, below the trial
    timeout) and null when bad (flagged); correctness stands."""
    a = G.Audit(CEILING_MS)
    parts = item["parts"]
    if not isinstance(response, list):
        return a.junk(sum(len(p["cases"]) for p in parts))
    cases = [(pi, part, c) for pi, part in enumerate(parts) for c in part["cases"]]
    rows = []
    for (pi, part, c), r in zip(cases, a.entries(response, len(cases))):
        key = "follows" if follows(part["rules"], c["obj"]) else "breaks"
        ft = any(_row(rule, c["obj"]) == "FT" for rule in part["rules"]) and key == "follows"
        ev = a.obj(r)
        choice, rt = None, None
        if ev is not None:
            if "choice" not in ev:
                a.malformed("missing_choice")
            else:
                choice = a.choice(ev["choice"], ("follows", "breaks"), "choice")
                choice = None if choice is G.BAD else choice
            rt = a.duration(ev, "rt")
        rows.append({"part": pi, "row": c["row"], "ok": choice == key, "ft": ft, "choice": choice, "rt": rt})
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"] is not None]

    def acc(sel):
        return round(sum(r["ok"] for r in sel) / len(sel), 3) if sel else None
    return a.finish(bool(rows) and n_ok >= 6, len(rows) - n_ok, {
        "accuracy": acc(rows),
        "accuracy_one_rule": acc([r for r in rows if r["part"] == 0]),
        "accuracy_two_rules": acc([r for r in rows if r["part"] == 1]),
        "correct_by_row_one_rule": {r["row"]: r["ok"] for r in rows if r["part"] == 0},
        "equivalence_errors": sum(1 for r in rows if r["ft"] and r["choice"] == "breaks"),
        "negation": item.get("negation"),
        "median_rt_correct": G.median(rts),
        "omissions": sum(r["choice"] is None for r in rows)})


def example_response(item, correct=True):
    out = []
    for part in item["parts"]:
        for c in part["cases"]:
            key = "follows" if follows(part["rules"], c["obj"]) else "breaks"
            if not correct:
                key = {"follows": "breaks", "breaks": "follows"}[key]
            out.append({"choice": key, "rt": 2500})
    return out
