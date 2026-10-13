"""Source memory (card 47): eight words are studied one at a time (2 s each), four inside
a circle on the left and four inside a square on the right. Then twelve test words (the
eight old ones plus four new ones, shuffled) are each answered Circle / Square / New.

Words come from text/<lang>.json "words" by index (same index = same concept in every
language). Sources are assigned at random, balanced 4/4, so a word's source cannot be
guessed from its meaning. The two items of a pair (k, k+1) have identical structure and
disjoint words; the pool is reshuffled and reused when it runs out (116 words, i.e.
about every 4 pairs), so a "new" word in a long form may have been seen in an earlier,
distant trial. The answer key is rebuilt here from the study list."""
import json
from pathlib import Path

N_OLD, N_NEW = 8, 4
SOURCES = ("circle", "square")
N_WORDS = len(json.loads((Path(__file__).parent / "text" / "en.json").read_text(encoding="utf-8"))["words"])


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
    need = N_OLD + N_NEW
    items = []
    for k in range(n):
        if k % 2 == 0:
            block = pool.take(2 * need)
        words = block[(k % 2) * need:(k % 2 + 1) * need]
        old, new = words[:N_OLD], words[N_OLD:]
        src = [SOURCES[j % 2] for j in range(N_OLD)]
        rng.shuffle(src)
        study = [{"word": w, "source": s} for w, s in zip(old, src)]
        test = old + new
        rng.shuffle(test)
        items.append({"study": study, "test": test})
    return items


def _key(item):
    """Oracle: the right answer for every test word ("circle", "square" or "new")."""
    src = {s["word"]: s["source"] for s in item["study"]}
    return [src.get(w, "new") for w in item["test"]]


def score(item, response):
    """response: {"answers": [{"answer": "circle"|"square"|"new"|null, "rt": ms}]} in test order.
    hit = at least 75% of the 12 test words get the fully right answer (old word with its
    correct shape, or "new" for a new word); omissions count as wrong.
    errors = test words not answered fully right.
    metrics: item recognition (hits/misses/false alarms/correct rejections, corrected d'),
    and source accuracy CONDITIONAL on recognised old words, with its denominator."""
    key = _key(item)
    resp = response if isinstance(response, dict) else {}
    ans = resp.get("answers") if isinstance(resp.get("answers"), list) else []
    hits = misses = fa = cr = omit = src_ok = 0
    exact, rts = 0, []
    for j, truth in enumerate(key):
        r = ans[j] if j < len(ans) and isinstance(ans[j], dict) else {}
        a = r.get("answer") if r.get("answer") in ("circle", "square", "new") else None
        if a is None:
            omit += 1
        said_old = a in SOURCES
        if truth == "new":
            fa += said_old
            cr += a == "new"
        else:
            hits += said_old
            misses += not said_old
            src_ok += a == truth
        if a == truth:
            exact += 1
            rt = r.get("rt")
            if isinstance(rt, (int, float)) and not isinstance(rt, bool):
                rts.append(rt)
    n_old = sum(1 for t in key if t != "new")
    n_new = len(key) - n_old
    from statistics import NormalDist
    z = NormalDist().inv_cdf
    hr, far = (hits + 0.5) / (n_old + 1), (fa + 0.5) / (n_new + 1)
    acc = exact / len(key)
    return {"hit": acc >= 0.75, "errors": len(key) - exact,
            "metrics": {"accuracy": round(acc, 3), "item_hits": hits, "item_misses": misses,
                        "false_alarms": fa, "correct_rejections": cr, "omissions": omit,
                        "hit_rate": round(hits / n_old, 3), "false_alarm_rate": round(fa / n_new, 3),
                        "d_prime_corrected": round(z(hr) - z(far), 3),
                        "source_correct": src_ok, "source_denominator": hits,
                        "source_accuracy_given_recognised": round(src_ok / hits, 3) if hits else None,
                        "rt_correct_mean": round(sum(rts) / len(rts), 1) if rts else None}}


def example_response(item, correct=True):
    flip = {"circle": "square", "square": "circle", "new": "circle"}
    return {"answers": [{"answer": t if correct else flip[t], "rt": 1400} for t in _key(item)]}
