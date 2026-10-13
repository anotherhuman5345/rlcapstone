"""Probability reasoning (card 58): two explicitly described events, A and B; choose
which is more likely, or "equally likely". Each event is written out (text file
templates filled with the item's numbers) AND drawn (bags with exactly that many red and
blue balls, or two dice with the target total), so text and diagram encode the same
numbers. One trial = 4 comparisons, one of each type, shuffled:

  urn      one draw from bag A vs bag B; the bag with the higher proportion of red
           also has at least as many red balls
  trap     one draw; the bag with the higher proportion has FEWER red balls
           (ratio-bias probe: choosing the bag with more red balls is the error)
  dice     two fair dice: total s vs total t (some pairs are exact ties)
  draws    two draws, both red: bag A WITH replacement vs bag B WITHOUT replacement
           (bags differ, so either may win)

Pairs (k, k+1) use the same type order, the same tie / which-mode-wins structure and
similar probability gaps, with different numbers.

Answer key (oracle, in score()): every outcome is enumerated (each ball / die face is a
distinct equally likely outcome; ordered draws via itertools.product with replacement,
itertools.permutations without) and the two probabilities compared exactly as fractions.
"""
import itertools
from fractions import Fraction

from app.tasks import _guard as G

TIMING = "untimed"   # view.js answer() has no time limit; rt is descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)

TYPES = ["urn", "trap", "dice", "draws"]


def prob(ev):
    """Oracle: probability of an event by enumerating the outcome space."""
    k = ev["kind"]
    if k == "dice_sum":
        space = list(itertools.product(range(1, 7), repeat=2))
        return Fraction(sum(1 for a, b in space if a + b == ev["total"]), len(space))
    balls = ["r"] * ev["red"] + ["b"] * ev["blue"]
    if k == "bag1":
        return Fraction(sum(1 for x in balls if x == "r"), len(balls))
    idx = range(len(balls))
    space = list(itertools.product(idx, repeat=2)) if ev["replace"] else list(itertools.permutations(idx, 2))
    return Fraction(sum(1 for i, j in space if balls[i] == "r" and balls[j] == "r"), len(space))


def key_of(comp):
    pa, pb = prob(comp["a"]), prob(comp["b"])
    return "a" if pa > pb else "b" if pb > pa else "equal"


def _bag(rng, lo=4, hi=12):
    n = rng.randint(lo, hi)
    r = rng.randint(1, n - 1)
    return {"kind": "bag1", "red": r, "blue": n - r}


def _comp(rng, typ, flag):
    while True:
        if typ in ("urn", "trap"):
            a, b = _bag(rng), _bag(rng)
            pa, pb = Fraction(a["red"], a["red"] + a["blue"]), Fraction(b["red"], b["red"] + b["blue"])
            if pa == pb:
                continue
            hi, lo = (a, b) if pa > pb else (b, a)
            gap = abs(pa - pb)
            if typ == "urn" and hi["red"] >= lo["red"] and Fraction(1, 10) <= gap <= Fraction(1, 4):
                return {"type": typ, "a": a, "b": b}
            if typ == "trap" and hi["red"] < lo["red"] and Fraction(1, 20) <= gap <= Fraction(1, 5):
                return {"type": typ, "a": a, "b": b}
        elif typ == "dice":
            s, t = rng.sample(range(2, 13), 2)
            ways = lambda x: 6 - abs(7 - x)
            if (flag == "tie" and ways(s) == ways(t)) or (flag == "diff" and 1 <= abs(ways(s) - ways(t)) <= 2):
                return {"type": typ, "a": {"kind": "dice_sum", "total": s}, "b": {"kind": "dice_sum", "total": t}}
        else:
            x, y = _bag(rng, 4, 9), _bag(rng, 4, 9)
            ea = {"kind": "bag2", "red": x["red"], "blue": x["blue"], "replace": True}
            eb = {"kind": "bag2", "red": y["red"], "blue": y["blue"], "replace": False}
            if rng.random() < 0.5:
                ea, eb = eb, ea
            comp = {"type": typ, "a": ea, "b": eb}
            pa, pb = prob(ea), prob(eb)
            if pa == pb or abs(pa - pb) < Fraction(1, 25) or min(pa, pb) == 0:
                continue
            winner = ea if pa > pb else eb
            if (flag == "replace") == winner["replace"]:
                return comp


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        order = TYPES[:]
        rng.shuffle(order)
        flags = {"dice": rng.choice(["tie", "diff"]), "draws": rng.choice(["replace", "keep"])}
        for _ in range(2):
            items.append({"comparisons": [_comp(rng, t, flags.get(t)) for t in order]})
    return items[:n]


@G.safe
def score(item, response):
    """response: [{"choice": "a" | "b" | "equal" | null, "rt": ms}] in comparison order, one
    entry per comparison (missing entries are omissions, extra ones ignored; both flagged).
    Any other choice value is flagged and scored wrong.
    Correct = the choice matches the enumerated comparison. hit = at least 3 of 4 correct.
    Error categories: ratio_bias (trap: picked the bag with more red balls), replacement
    (draws: wrong), tie_missed (exact tie not called equal), false_tie (equal when not).
    Untimed: rt is descriptive, checked (finite, >= 100 ms, below the trial timeout) and
    null when bad (flagged); correctness stands."""
    a = G.Audit(CEILING_MS)
    comps = item["comparisons"]
    if not isinstance(response, list):
        return a.junk(len(comps))
    rows = []
    errs = {"ratio_bias": 0, "replacement": 0, "tie_missed": 0, "false_tie": 0}
    for k, (c, r) in enumerate(zip(comps, a.entries(response, len(comps)))):
        key = key_of(c)
        ev = a.obj(r)
        choice, rt = None, None
        if ev is not None:
            if "choice" not in ev:
                a.malformed("missing_choice")
            else:
                choice = a.choice(ev["choice"], ("a", "b", "equal"), "choice")
                choice = None if choice is G.BAD else choice
            rt = a.duration(ev, "rt")
        ok = choice == key
        if not ok and choice is not None:
            if key == "equal":
                errs["tie_missed"] += 1
            elif choice == "equal":
                errs["false_tie"] += 1
            elif c["type"] == "trap":
                errs["ratio_bias"] += 1
            elif c["type"] == "draws":
                errs["replacement"] += 1
        rows.append({"type": c["type"], "ok": ok, "rt": rt, "omit": choice is None})
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"] is not None]
    return a.finish(bool(rows) and n_ok >= 3, len(rows) - n_ok, {
        "accuracy": round(n_ok / (len(rows) or 1), 3),
        "correct_by_type": {r["type"]: r["ok"] for r in rows},
        "rt_by_type": {r["type"]: r["rt"] for r in rows},
        "error_categories": errs,
        "median_rt_correct": G.median(rts),
        "omissions": sum(r["omit"] for r in rows)})


def example_response(item, correct=True):
    out = []
    for c in item["comparisons"]:
        key = key_of(c)
        out.append({"choice": key if correct else ("a" if key != "a" else "b"), "rt": 7000})
    return out
