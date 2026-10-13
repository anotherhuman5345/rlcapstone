"""Paired-associate learning (card 41): six novel line symbols are each paired with a
word. Two study/test cycles inside one trial: study the six pairs (2.5 s each), then
for each symbol pick its word from eight options (the six studied words plus two
unstudied lure words); then study again in a new order and test again.

Symbols are random strokes on a 3x3 lattice drawn by the browser as SVG, new for every
item, so no symbol-word pair is ever repeated. Words come from text/<lang>.json
"words" by index (the same index is the same concept in every language). Within a
pair (k, k+1) the two items use disjoint words; the word pool is reshuffled and reused
once it runs out (96 words = 12 items), so long forms repeat words but not pairs.
Pairs (k, k+1) have identical structure (6 pairs, 2 lures, 2 cycles)."""
import json
from pathlib import Path

N_PAIRS, N_LURES, CYCLES = 6, 2, 2
N_WORDS = len(json.loads((Path(__file__).parent / "text" / "en.json").read_text(encoding="utf-8"))["words"])
STEPS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def _glyph(rng):
    """A walk of 4 strokes between neighbouring points of a 3x3 lattice, no stroke twice."""
    while True:
        p = (rng.randint(0, 2), rng.randint(0, 2))
        pts, edges = [list(p)], set()
        for _ in range(4):
            opts = [(p[0] + dx, p[1] + dy) for dx, dy in STEPS
                    if 0 <= p[0] + dx <= 2 and 0 <= p[1] + dy <= 2
                    and frozenset([p, (p[0] + dx, p[1] + dy)]) not in edges]
            if not opts:
                break
            q = rng.choice(opts)
            edges.add(frozenset([p, q]))
            pts.append(list(q))
            p = q
        if len(edges) == 4:
            return pts, edges


def _symbols(rng, k):
    out, sets = [], []
    while len(out) < k:
        pts, edges = _glyph(rng)
        if all(len(edges ^ e) >= 4 for e in sets):  # clearly different from the others
            out.append(pts)
            sets.append(edges)
    return out


class _Pool:
    def __init__(self, rng):
        self.rng, self.left = rng, []

    def take(self, k):
        if len(self.left) < k:
            self.left = list(range(N_WORDS))
            self.rng.shuffle(self.left)
        got, self.left = self.left[:k], self.left[k:]
        return got


def generate(rng, n, save_image):
    pool = _Pool(rng)
    need = N_PAIRS + N_LURES
    items = []
    for k in range(n):
        if k % 2 == 0:
            block = pool.take(2 * need)       # both items of a pair: disjoint words
        words = block[(k % 2) * need:(k % 2 + 1) * need]
        studied, lures = words[:N_PAIRS], words[N_PAIRS:]
        options = studied + lures
        rng.shuffle(options)
        orders = []
        for _ in range(2 * CYCLES):
            o = list(range(N_PAIRS))
            rng.shuffle(o)
            orders.append(o)
        items.append({"symbols": _symbols(rng, N_PAIRS), "words": studied, "lures": lures,
                      "options": options, "study_orders": orders[:CYCLES], "test_orders": orders[CYCLES:]})
    return items


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def score(item, response):
    """response: {"cycles": [[{"choice": word index or null, "rt": ms}, ...], ...]}: one list
    per test cycle, in that cycle's test_orders order. Symbol s is correct when the choice is
    item["words"][s]. Errors are split into intrusions (another studied word), lure errors
    (an unstudied word) and omissions (no choice within the time limit).
    hit = the last cycle has at least 5 of 6 symbols right (accuracy >= 0.8).
    errors = wrong or missing answers over both cycles."""
    resp = response if isinstance(response, dict) else {}
    cyc = resp.get("cycles") if isinstance(resp.get("cycles"), list) else []
    words, lures = item["words"], set(item["lures"])
    accs, intr, lure_err, omit, rts = [], 0, 0, 0, []
    for c, order in enumerate(item["test_orders"]):
        rows = cyc[c] if c < len(cyc) and isinstance(cyc[c], list) else []
        right = 0
        for j, s in enumerate(order):
            r = rows[j] if j < len(rows) and isinstance(rows[j], dict) else {}
            ch = r.get("choice")
            ch = ch if isinstance(ch, int) and not isinstance(ch, bool) else None
            if ch == words[s]:
                right += 1
                if _num(r.get("rt")):
                    rts.append(r["rt"])
            elif ch is None:
                omit += 1
            elif ch in words:
                intr += 1
            elif ch in lures:
                lure_err += 1
            else:
                omit += 1   # not an offered option: treated as no answer
        accs.append(right / len(order))
    total = sum(len(o) for o in item["test_orders"])
    return {"hit": accs[-1] >= 0.8, "errors": total - round(sum(a * len(o) for a, o in zip(accs, item["test_orders"]))),
            "metrics": {"accuracy_by_cycle": [round(a, 3) for a in accs], "final_accuracy": round(accs[-1], 3),
                        "learning_gain": round(accs[-1] - accs[0], 3), "intrusions": intr,
                        "lure_errors": lure_err, "omissions": omit,
                        "rt_correct_mean": round(sum(rts) / len(rts), 1) if rts else None}}


def example_response(item, correct=True):
    words = item["words"]
    cycles = []
    for order in item["test_orders"]:
        cycles.append([{"choice": words[s] if correct else words[(s + 1) % len(words)], "rt": 1500}
                       for s in order])
    return {"cycles": cycles}
