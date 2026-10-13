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
from statistics import NormalDist

from app.tasks import _guard as G

TIMING = "window"      # each test word: up to 6000 ms (view.js answer(6000))
WINDOW_MS = 6000
RT_SLACK_MS = 50       # timer tolerance at the window end
CEILING_MS = G.trial_ceiling(__file__)
ANSWERS = ("circle", "square", "new")

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


@G.safe
def score(item, response):
    """response: {"answers": [{"answer": "circle"|"square"|"new"|null, "rt": ms}]} in test
    order, one entry per test word (missing entries invalid, extra ones flagged).
    Every answer is classified (app/tasks/_guard.py): absent (no answer within the 6000 ms
    limit, view.js answer(6000)), invalid (unknown answer, answer without rt or rt without
    answer, non-finite / negative / impossible rt), anticipatory (< 100 ms), late (beyond
    the limit + 50 ms timer tolerance) or timely. Only a timely answer counts as given; any
    other entry is scored as no answer (omission). Keys come from the item (_key).
    hit = at least 75% of the 12 test words get a timely, fully right answer (old word with
    its correct shape, or "new" for a new word); omissions count as wrong.
    errors = test words not answered fully right.
    metrics: item recognition (hits/misses/false alarms/correct rejections, corrected d'),
    and source accuracy CONDITIONAL on recognised old words, with its denominator."""
    key = _key(item)
    au = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return au.junk(len(key))
    hits = misses = fa = cr = omit = src_ok = not_timely = 0
    exact, rts = 0, []
    for truth, r in zip(key, au.entries(response.get("answers", G.MISSING), len(key), "answers")):
        st, a, rt = au.keyed(r, ANSWERS, key="answer", window=WINDOW_MS, slack=RT_SLACK_MS)
        if st != G.TIMELY:
            a = None
            omit += 1
            not_timely += st != G.ABSENT
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
            rts.append(rt)
    n_old = sum(1 for t in key if t != "new")
    n_new = len(key) - n_old
    z = NormalDist().inv_cdf
    hr, far = (hits + 0.5) / (n_old + 1), (fa + 0.5) / (n_new + 1)
    acc = exact / len(key)
    return au.finish(acc >= 0.75, len(key) - exact, {
        "accuracy": round(acc, 3), "item_hits": hits, "item_misses": misses,
        "false_alarms": fa, "correct_rejections": cr, "omissions": omit, "not_timely": not_timely,
        "hit_rate": round(hits / n_old, 3), "false_alarm_rate": round(fa / n_new, 3),
        "d_prime_corrected": round(z(hr) - z(far), 3),
        "source_correct": src_ok, "source_denominator": hits,
        "source_accuracy_given_recognised": round(src_ok / hits, 3) if hits else None,
        "rt_correct_mean": G.mean(rts)})


def example_response(item, correct=True):
    flip = {"circle": "square", "square": "circle", "new": "circle"}
    return {"answers": [{"answer": t if correct else flip[t], "rt": 1400} for t in _key(item)]}
