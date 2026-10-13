"""Artificial grammar learning (card 43), adapted to one short trial.

A hidden finite-state grammar (5 states, 5 symbols, Reber-style topology) generates
letter strings. Study: 10 grammatical strings are shown together for STUDY_MS (fixed).
Test: 12 NEW strings one at a time (6 legal, 6 illegal, shuffled); classify each as
"follows the pattern" (legal) or "breaks it" (illegal).

Illegal strings are made from novel legal strings of the same length by changing one
letter, so length and most fragments are matched across classes. Keys are NOT taken
from the generator: score() re-parses each test string with an independent
nondeterministic-automaton parser (`parse`). No test string appears in the study list.
The two items of a pair use the same grammar with disjoint letter sets (different
surface, same structure), so they are equally hard.
"""

# Transition table: state -> list of (symbol slot, next state); None = accept.
GRAMMAR = {
    0: [(0, 1), (1, 2)],
    1: [(2, 1), (3, 3)],
    2: [(0, 2), (4, 4)],
    3: [(3, 2), (2, None)],
    4: [(1, 3), (4, None)],
}
LETTERS = list("BDFGKMPRSTVXZ")  # no I/i: avoids the Turkish dotted/dotless pair
MIN_LEN, MAX_LEN = 3, 8
N_STUDY, N_TEST = 10, 12
STUDY_MS = 25000


def _walk(rng):
    while True:
        s, out = 0, []
        while s is not None and len(out) <= MAX_LEN:
            slot, s = rng.choice(GRAMMAR[s])
            out.append(slot)
        if s is None and MIN_LEN <= len(out) <= MAX_LEN:
            return tuple(out)


def parse(string, alphabet):
    """Independent oracle: simulate the automaton over the set of possible states."""
    if not isinstance(string, str) or not string:
        return False
    states = {0}
    accepted = False
    for ch in string:
        if ch not in alphabet:
            return False
        slot = alphabet.index(ch)
        nxt, accepted = set(), False
        for st in states:
            for sym, to in GRAMMAR[st]:
                if sym == slot:
                    if to is None:
                        accepted = True
                    else:
                        nxt.add(to)
        states = nxt
        if not states and not accepted:
            return False
    # accepted only if the LAST symbol could take us to the accept state
    return accepted


def _skeleton(rng):
    """Slot-level structure shared by both items of a pair."""
    study = set()
    while len(study) < N_STUDY:
        study.add(_walk(rng))
    legal = set()
    while len(legal) < N_TEST // 2:
        w = _walk(rng)
        if w not in study:
            legal.add(w)
    illegal = set()
    while len(illegal) < N_TEST // 2:
        base = list(_walk(rng))
        pos = rng.randrange(1, len(base) - 1)  # keep legal first and last letters
        base[pos] = rng.choice([x for x in range(5) if x != base[pos]])
        illegal.add(tuple(base))
    return sorted(study), sorted(legal), sorted(illegal)


def _render(slots, alphabet):
    return "".join(alphabet[s] for s in slots)


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        study, legal, illegal = _skeleton(rng)
        letters = rng.sample(LETTERS, 10)
        for alphabet in (letters[:5], letters[5:]):
            # keep only illegal strings the parser rejects (re-draw the pair otherwise)
            test = [_render(s, alphabet) for s in legal + illegal]
            st = [_render(s, alphabet) for s in study]
            order = list(range(N_TEST))
            rng.shuffle(order)
            items.append({"alphabet": "".join(alphabet), "study": st,
                          "test": [test[i] for i in order], "study_ms": STUDY_MS})
        a, b = items[-2], items[-1]
        bad = any(sum(parse(t, it["alphabet"]) for t in it["test"]) != N_TEST // 2
                  or set(it["test"]) & set(it["study"]) for it in (a, b))
        if bad:
            del items[-2:]
    return items[:n]


def score(item, response):
    """response: [{"i": test index, "legal": true|false|null, "rt": ms}].
    hit = at least 8 of 12 test strings classified correctly (67 %; chance is 50 %).
    Omissions count as wrong. metrics: accuracy, hits/false alarms for "legal",
    d' with the (x+0.5)/(n+1) correction, median correct RT, omissions."""
    try:
        alpha = item["alphabet"]
        keys = [parse(t, alpha) for t in item["test"]]
        resp = response if isinstance(response, list) else []
        by_i = {}
        for r in resp:
            if isinstance(r, dict) and isinstance(r.get("i"), int) and r["i"] not in by_i:
                by_i[r["i"]] = r
        ok, rts = [], []
        hits = fas = omis = 0
        for k, key in enumerate(keys):
            r = by_i.get(k, {})
            ans = r.get("legal")
            if not isinstance(ans, bool):
                ans = None
                omis += 1
            good = ans is not None and ans == key
            ok.append(good)
            hits += key and ans is True
            fas += (not key) and ans is True
            rt = r.get("rt")
            if good and isinstance(rt, (int, float)) and rt > 0:
                rts.append(rt)
        n_sig = sum(keys)
        n_noise = len(keys) - n_sig
        from statistics import NormalDist, median
        z = NormalDist().inv_cdf
        dprime = round(z((hits + .5) / (n_sig + 1)) - z((fas + .5) / (n_noise + 1)), 3)
        return {"hit": sum(ok) >= 8, "errors": len(keys) - sum(ok),
                "metrics": {"accuracy": round(sum(ok) / len(keys), 3), "legal_hits": hits,
                            "false_alarms": fas, "dprime": dprime,
                            "median_rt_correct": median(rts) if rts else None,
                            "valid_rt_n": len(rts), "omissions": omis}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    return [{"i": k, "legal": parse(t, item["alphabet"]) == correct, "rt": 1200}
            for k, t in enumerate(item["test"])]
