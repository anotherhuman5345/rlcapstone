"""Novel vocabulary (card 42), adapted to one short trial.

Learn: 4 invented words, each shown with its definition for the same fixed time
(matched exposures, STUDY_MS each). Test: 8 questions in shuffled order:
  - 4 "meaning" questions: the word is shown, pick its definition (4 options = the 4
    learned definitions);
  - 4 "apply" questions: a NEW example (not the definition) is shown, pick the word it
    describes (4 options = the 4 learned words).
Definitions and examples live in text/<lang>.json ("meanings", "examples", same index);
items refer to them by index. Labels are language-neutral pseudo-words built only from
letters shared by the English and Turkish alphabets; the list was checked against an
English word list (/usr/share/dict/words) and by hand for Turkish (no Turkish words,
no Turkish suffix look-alikes such as -mek/-lar). The two items of a pair use disjoint
labels and disjoint meanings with the same 4 + 4 test structure.
"""

N_WORDS = 4
N_MEANINGS = 16  # length of "meanings"/"examples" in the text files
STUDY_MS = 6000

LABELS = ["tobrel", "vasken", "pelmor", "nuvik", "gorlem", "fendip", "solbek", "midrun",
          "kavlop", "rulvan", "brimet", "dafkor", "lupren", "mesdor", "nofrik", "pavtel",
          "tamlek", "vidrok", "bonsef", "dulmar", "gapnor", "hesvit", "jorbel", "pemsok",
          "rabdin", "sefkul", "tunbor", "vespal", "zorfin", "kibrun", "pirsom", "delvug"]


def _make(rng, labels, meanings):
    words = [{"label": lab, "meaning": m} for lab, m in zip(labels, meanings)]
    questions = []
    for w in range(N_WORDS):
        opts = list(range(N_WORDS))
        rng.shuffle(opts)
        questions.append({"kind": "meaning", "word": w, "options": opts})
        opts = list(range(N_WORDS))
        rng.shuffle(opts)
        questions.append({"kind": "apply", "word": w, "options": opts})
    rng.shuffle(questions)
    return {"words": words, "questions": questions, "study_ms": STUDY_MS}


def generate(rng, n, save_image):
    items = []
    for _ in range(0, n, 2):
        labs = rng.sample(LABELS, 2 * N_WORDS)
        mean = rng.sample(range(N_MEANINGS), 2 * N_WORDS)
        items.append(_make(rng, labs[:N_WORDS], mean[:N_WORDS]))
        items.append(_make(rng, labs[N_WORDS:], mean[N_WORDS:]))
    return items[:n]


def _key(q):
    """Oracle: the correct option is the queried word itself (index into item["words"]).
    For "meaning" questions options are word indices standing for their definitions;
    for "apply" questions options are word indices standing for their labels."""
    return q["word"]


def score(item, response):
    """response: [{"q": question index, "choice": word index or null, "rt": ms}] in order.
    hit = at least 6 of the 8 test questions correct (75 %); omissions count as wrong.
    metrics: overall accuracy, meaning-recognition accuracy, application accuracy,
    median correct RT, omissions."""
    try:
        qs = item["questions"]
        resp = response if isinstance(response, list) else []
        by_q = {}
        for r in resp:
            if isinstance(r, dict) and isinstance(r.get("q"), int) and r["q"] not in by_q:
                by_q[r["q"]] = r
        ok, rts, omis = [], [], 0
        acc_kind = {"meaning": [], "apply": []}
        for k, q in enumerate(qs):
            r = by_q.get(k, {})
            ch = r.get("choice")
            if ch is None:
                omis += 1
            good = isinstance(ch, int) and not isinstance(ch, bool) and ch == _key(q)
            ok.append(good)
            acc_kind[q["kind"]].append(good)
            rt = r.get("rt")
            if good and isinstance(rt, (int, float)) and rt > 0:
                rts.append(rt)
        n = len(qs)
        rts.sort()
        med = rts[len(rts) // 2] if len(rts) % 2 else (sum(rts[len(rts) // 2 - 1:len(rts) // 2 + 1]) / 2 if rts else None)

        def acc(v):
            return round(sum(v) / len(v), 3) if v else None
        return {"hit": n > 0 and sum(ok) >= 0.75 * n, "errors": n - sum(ok),
                "metrics": {"accuracy": acc(ok), "recognition_accuracy": acc(acc_kind["meaning"]),
                            "application_accuracy": acc(acc_kind["apply"]),
                            "median_rt_correct": med, "valid_rt_n": len(rts), "omissions": omis}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    out = []
    for k, q in enumerate(item["questions"]):
        ch = q["word"] if correct else (q["word"] + 1) % N_WORDS
        out.append({"q": k, "choice": ch, "rt": 1500 + 100 * k})
    return out
