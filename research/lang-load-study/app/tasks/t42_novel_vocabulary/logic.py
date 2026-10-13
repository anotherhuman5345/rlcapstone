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

from app.tasks import _guard as G

TIMING = "window"      # each question: up to 20000 ms (view.js ask(): setTimeout(() => done(null), 20000))
WINDOW_MS = 20000
RT_SLACK_MS = 50       # timer tolerance at the window end
CEILING_MS = G.trial_ceiling(__file__)
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


@G.safe
def score(item, response):
    """response: [{"q": question index, "choice": word index or null, "rt": ms}] in order,
    one entry per question (missing entries are invalid, extra ones flagged; an entry whose
    "q" is not its position is flagged and invalid).
    Every answer is classified (app/tasks/_guard.py): absent (no choice within the 20 s
    limit, view.js ask(): setTimeout(..., 20000)), invalid (choice not a word index 0-3,
    choice without rt or rt without choice, non-finite / negative / impossible rt),
    anticipatory (< 100 ms), late (beyond the limit + 50 ms timer tolerance) or timely. Only
    a timely answer can be correct; the key is recomputed from the question (oracle).
    hit = at least 6 of the 8 test questions correct (75 %); omissions and answers that are
    not timely count as wrong.
    metrics: overall accuracy, meaning-recognition accuracy, application accuracy,
    median correct RT, omissions."""
    a = G.Audit(CEILING_MS)
    qs = item["questions"]
    n = len(qs)
    if not isinstance(response, list):
        return a.junk(n)
    ok, rts, omis, not_timely = [], [], 0, 0
    acc_kind = {"meaning": [], "apply": []}
    for k, (q, r) in enumerate(zip(qs, a.entries(response, n, "answers"))):
        if isinstance(r, dict) and r.get("q", G.MISSING) != k:
            if "q" not in r:
                a.malformed("missing_q")
            elif not G.is_int(r["q"]):
                a.malformed("invalid_q")
            else:
                a.malformed("q_out_of_order")
            a.record(G.INVALID)
            st, ch, rt = G.INVALID, None, None
        else:
            st, ch, rt = a.keyed(r, range(N_WORDS), key="choice", window=WINDOW_MS, slack=RT_SLACK_MS)
        omis += st == G.ABSENT
        not_timely += st in (G.INVALID, G.ANTICIPATORY, G.LATE)
        good = st == G.TIMELY and ch == _key(q)
        ok.append(good)
        acc_kind[q["kind"]].append(good)
        if good:
            rts.append(rt)

    def acc(v):
        return round(sum(v) / len(v), 3) if v else None
    return a.finish(n > 0 and sum(ok) >= 0.75 * n, n - sum(ok), {
        "accuracy": acc(ok), "recognition_accuracy": acc(acc_kind["meaning"]),
        "application_accuracy": acc(acc_kind["apply"]),
        "median_rt_correct": G.median(rts), "valid_rt_n": len(rts), "omissions": omis,
        "not_timely": not_timely})


def example_response(item, correct=True):
    out = []
    for k, q in enumerate(item["questions"]):
        ch = q["word"] if correct else (q["word"] + 1) % N_WORDS
        out.append({"q": k, "choice": ch, "rt": 1500 + 100 * k})
    return out
