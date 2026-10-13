"""Category learning (card 44), adapted to one short trial.

Objects have 3 features with 4 values each (shape, colour, fill pattern; drawn in SVG by
view.js). A hidden rule puts an object in group 0 when ONE relevant feature has one of
two values (e.g. colour is blue or green), otherwise in group 1; the other two features
are irrelevant and balanced across groups.
Training: 16 objects, feedback after each response (correct/wrong + the right group).
Transfer: 8 objects never seen in training, no feedback.
Group names come from the text file ("groups"). The two items of a pair share the
relevant feature but use a different split of its values (and different objects), so they
have the same structure and difficulty. Answer keys come from `category()` (rule engine),
not from the browser.
"""
from app.tasks import _guard as G

TIMING = "window"      # every answer (training and transfer): 5000 ms limit (view.js answer(5000))
WINDOW_MS = 5000
RT_SLACK_MS = 50       # timer tolerance at the window end
CEILING_MS = G.trial_ceiling(__file__)
DIMS = 3
PARTITIONS = [(0, 1), (0, 2), (0, 3)]  # group-0 values; the other two values are group 1
N_TRAIN, N_TRANSFER = 16, 8


def category(rule, f):
    """Rule engine: 0 if the relevant feature value is in rule["a_values"], else 1."""
    return 0 if f[rule["dim"]] in rule["a_values"] else 1


def _balanced(rng, reps, exclude):
    """reps copies of each value per dimension, all objects distinct and not excluded."""
    while True:
        cols = []
        for _ in range(DIMS):
            c = [v for v in range(4) for _ in range(reps)]
            rng.shuffle(c)
            cols.append(c)
        objs = [tuple(col[i] for col in cols) for i in range(4 * reps)]
        if len(set(objs)) == len(objs) and not set(objs) & exclude:
            return [list(o) for o in objs]


def _make(rng, dim, part):
    a_values = list(part)
    rule = {"dim": dim, "a_values": a_values}
    train = _balanced(rng, N_TRAIN // 4, set())
    transfer = _balanced(rng, N_TRANSFER // 4, {tuple(o) for o in train})
    flip = rng.random() < 0.5  # which group is shown as "A"
    if flip:
        rule["a_values"] = [v for v in range(4) if v not in a_values]
    return {"rule": rule,
            "train": [{"f": f, "cat": category(rule, f)} for f in train],
            "transfer": [{"f": f} for f in transfer]}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        dim = rng.randrange(DIMS)
        p1, p2 = rng.sample(PARTITIONS, 2)
        items.append(_make(rng, dim, p1))
        items.append(_make(rng, dim, p2))
    return items[:n]


@G.safe
def score(item, response):
    """response: {"train": [{"choice": 0|1|null, "rt": ms}], "transfer": [same]}, one entry
    per object in display order (missing entries invalid, extra ones flagged).
    Every answer is classified (app/tasks/_guard.py): absent (no choice within the 5000 ms
    limit, view.js answer(5000), training and transfer), invalid (choice not 0/1, choice
    without rt or rt without choice, non-finite / negative / impossible rt), anticipatory
    (< 100 ms), late (beyond the limit + 50 ms timer tolerance) or timely. Only a timely
    answer can be correct; keys come from the rule engine category(), not the browser.
    hit = transfer accuracy >= 75 % (at least 6 of 8 new objects right); omissions and
    answers that are not timely are wrong. metrics: training accuracy in the first and
    second half, learning slope (second minus first half), final-block (last 8) and transfer
    accuracy, median correct transfer RT, omissions."""
    a = G.Audit(CEILING_MS)
    rule = item["rule"]
    if not isinstance(response, dict):
        return a.junk(len(item["train"]) + len(item["transfer"]))

    def judge(objs, field):
        out = []
        for o, r in zip(objs, a.entries(response.get(field, G.MISSING), len(objs), field)):
            st, ch, rt = a.keyed(r, (0, 1), key="choice", window=WINDOW_MS, slack=RT_SLACK_MS)
            good = st == G.TIMELY and ch == category(rule, o["f"])
            out.append((good, rt if good else None, st))
        return out
    tr = judge(item["train"], "train")
    tf = judge(item["transfer"], "transfer")

    def acc(rows):
        return round(sum(g for g, _, _ in rows) / len(rows), 3) if rows else None
    half = len(tr) // 2
    a1, a2 = acc(tr[:half]), acc(tr[half:])
    t_acc = acc(tf)
    errors = sum(not g for g, _, _ in tr + tf)
    return a.finish(t_acc is not None and t_acc >= 0.75, errors, {
        "train_acc_first_half": a1, "train_acc_second_half": a2,
        "learning_slope": round(a2 - a1, 3) if a1 is not None else None,
        "final_block_acc": a2, "transfer_acc": t_acc,
        "transfer_median_rt_correct": G.median([rt for g, rt, _ in tf if g]),
        "omissions": sum(st == G.ABSENT for _, _, st in tr + tf),
        "not_timely": sum(st in (G.INVALID, G.ANTICIPATORY, G.LATE) for _, _, st in tr + tf)})


def example_response(item, correct=True):
    rule = item["rule"]
    pick = (lambda f: category(rule, f)) if correct else (lambda f: 1 - category(rule, f))
    return {"train": [{"choice": pick(o["f"]), "rt": 900} for o in item["train"]],
            "transfer": [{"choice": pick(o["f"]), "rt": 800} for o in item["transfer"]]}
