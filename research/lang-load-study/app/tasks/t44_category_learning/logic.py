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


def _rows(objs, part):
    part = part if isinstance(part, list) else []
    return [part[k] if k < len(part) and isinstance(part[k], dict) else {} for k in range(len(objs))]


def score(item, response):
    """response: {"train": [{"choice": 0|1|null, "rt": ms}], "transfer": [same]}.
    hit = transfer accuracy >= 75 % (at least 6 of 8 new objects right); omissions are
    wrong. metrics: training accuracy in the first and second half, learning slope
    (second minus first half), final-block (last 8) and transfer accuracy, median
    correct transfer RT, omissions."""
    try:
        rule = item["rule"]
        resp = response if isinstance(response, dict) else {}

        def judge(objs, part):
            out = []
            for o, r in zip(objs, _rows(objs, part)):
                ch = r.get("choice")
                good = ch in (0, 1) and not isinstance(ch, bool) and ch == category(rule, o["f"])
                out.append((good, r.get("rt"), ch is None))
            return out
        tr = judge(item["train"], resp.get("train"))
        tf = judge(item["transfer"], resp.get("transfer"))

        def acc(rows):
            return round(sum(g for g, _, _ in rows) / len(rows), 3) if rows else None
        half = len(tr) // 2
        a1, a2 = acc(tr[:half]), acc(tr[half:])
        t_acc = acc(tf)
        rts = sorted(rt for g, rt, _ in tf if g and isinstance(rt, (int, float)) and rt > 0)
        med = rts[len(rts) // 2] if rts else None
        errors = sum(not g for g, _, _ in tr + tf)
        return {"hit": t_acc is not None and t_acc >= 0.75, "errors": errors,
                "metrics": {"train_acc_first_half": a1, "train_acc_second_half": a2,
                            "learning_slope": round(a2 - a1, 3) if a1 is not None else None,
                            "final_block_acc": a2, "transfer_acc": t_acc,
                            "transfer_median_rt_correct": med,
                            "omissions": sum(om for _, _, om in tr + tf)}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    rule = item["rule"]
    pick = (lambda f: category(rule, f)) if correct else (lambda f: 1 - category(rule, f))
    return {"train": [{"choice": pick(o["f"]), "rt": 900} for o in item["train"]],
            "transfer": [{"choice": pick(o["f"]), "rt": 800} for o in item["transfer"]]}
