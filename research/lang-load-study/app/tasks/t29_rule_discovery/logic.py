"""Rule discovery (card 29): sort a card onto one of four reference cards by an
unannounced rule (same COLOR, same SHAPE, or same COUNT) learned from correct/wrong
feedback. After CRITERION correct sorts in a row the rule changes, without warning, to
the next rule in item["rules"]; the trial ends when all three rules have been found or
after MAX_TRIALS sorts. Reference card i has color i, shape i and i+1 figures. Every
card to sort differs in color, shape and count (one of the 24 such cards), so the three
rules always point to three different reference cards and one reference card is never
right: no card makes the rules agree. Both items of a pair share the rule order (the
main source of difficulty) and differ in card order. Original drawn stimuli."""

from app.tasks import _guard as G

TIMING = "window"     # each sort has a 5000 ms window (view.js answer(it.window_ms), item window_ms)
CRITERION = 4
MAX_TRIALS = 36
WINDOW_MS = 5000
RT_SLACK_MS = 50      # timer tolerance at the window end
CEILING_MS = G.trial_ceiling(__file__)
RULES = ["color", "shape", "count"]
FEATURE = {"color": 0, "shape": 1, "count": 2}
COLORS = ["#D55E00", "#009E73", "#F0E442", "#0072B2"]  # vermillion, green, yellow, blue
SHAPES = ["triangle", "star", "cross", "circle"]
CARDS = [(c, s, k) for c in range(4) for s in range(4) for k in range(4) if len({c, s, k}) == 3]


def _sequence(rng):
    while True:
        seq = []
        for _ in range((MAX_TRIALS + len(CARDS) - 1) // len(CARDS)):
            block = CARDS[:]
            rng.shuffle(block)
            seq += block
        seq = seq[:MAX_TRIALS]
        if all(a != b for a, b in zip(seq, seq[1:])):
            return [list(c) for c in seq]


def generate(rng, n, save_image):
    items = []
    order = None
    for k in range(n):
        if k % 2 == 0:
            order = RULES[:]
            rng.shuffle(order)
        items.append({"rules": order, "cards": _sequence(rng), "colors": COLORS, "shapes": SHAPES,
                      "criterion": CRITERION, "max_trials": MAX_TRIALS, "window_ms": WINDOW_MS})
    return items


def replay(item, choices):
    """Apply the sorting rules to choices (reference index 0-3 or None). Oracle: the
    correct reference is the one sharing the card's value on the active rule's feature."""
    rules = item["rules"]
    phase, streak, rows = 0, 0, []
    for t, ch in enumerate(choices[: item["max_trials"]]):
        if phase >= len(rules):
            break
        card = item["cards"][t]
        target = card[FEATURE[rules[phase]]]
        old = card[FEATURE[rules[phase - 1]]] if phase > 0 else None
        ok = ch == target
        rows.append({"phase": phase, "ok": ok, "choice": ch,
                     "persev": (not ok) and ch is not None and ch == old})
        streak = streak + 1 if ok else 0
        if streak >= item["criterion"]:
            phase, streak = phase + 1, 0
    return rows, phase


def _rule_field(a, r, active):
    """The browser's "rule" (rule name active before the sort): a mismatch metric only,
    never used for scoring. Missing / invalid values are flagged; returns True on mismatch."""
    v = r.get("rule", G.MISSING)
    if v is G.MISSING:
        a.malformed("missing_rule")
        return False
    if not G.member(v, RULES):
        a.malformed("invalid_rule")
        return False
    return v != active


@G.safe
def score(item, response):
    """response: [{"choice": 0-3 | null, "rt": ms, "rule": rule name active before the
    sort}] in sort order.
    Every sort is classified (app/tasks/_guard.py): absent (no choice: the 5000 ms window,
    view.js answer(it.window_ms), ran out), invalid (choice not an integer 0-3, choice without
    rt or rt without choice, non-finite / negative / impossible rt), anticipatory (< 100 ms),
    late (beyond the window + 50 ms timer tolerance) or timely. The server replays the sorts
    with the task rules (oracle); only a timely sort counts as made, every other one is
    replayed as an omission. The browser's "rule" field is only compared (rule_mismatch),
    never trusted. Sorts after the replay ended are flagged.
    hit = all three rules found (criterion reached in every phase) within MAX_TRIALS.
    errors = wrong sorts + omissions (incl. sorts that were not timely). Metrics: categories
    completed, trials to criterion per rule, trials to first category, perseverative errors
    (sorted by the previous, now-wrong rule), other errors, total correct, median RT (timely
    sorts), rule_mismatch (the browser's active rule differed from the server replay)."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, list):
        return a.junk()
    raw = a.stream(response, "sorts", cap=item["max_trials"])
    evs = [a.keyed(r, range(4), key="choice", window=WINDOW_MS, slack=RT_SLACK_MS) for r in raw]
    choices = [k if st == G.TIMELY else None for st, k, _ in evs]
    rows, cats = replay(item, choices)
    if len(raw) > len(rows):
        a.flag("sorts_after_end", len(raw) - len(rows))
    mismatch = False
    for r, row in zip(raw, rows):
        if isinstance(r, dict) and _rule_field(a, r, item["rules"][row["phase"]]):
            mismatch = True
    n_rules = len(item["rules"])
    to_crit = [sum(1 for r in rows if r["phase"] == p) if cats > p else None for p in range(n_rules)]
    rts = [rt for (st, _, rt) in evs[: len(rows)] if st == G.TIMELY]
    persev = sum(r["persev"] for r in rows)
    errors = sum(not r["ok"] for r in rows)
    omissions = sum(1 for r in rows if r["choice"] is None)
    not_timely = sum(1 for (st, _, _) in evs[: len(rows)] if st in (G.INVALID, G.ANTICIPATORY, G.LATE))
    return a.finish(cats >= n_rules and len(rows) > 0, errors, {
        "categories_completed": cats, "sorts": len(rows),
        "total_correct": sum(r["ok"] for r in rows),
        "trials_to_criterion": to_crit, "trials_to_first_category": to_crit[0] if to_crit else None,
        "perseverative_errors": persev,
        "other_errors": errors - persev - omissions,
        "omissions": omissions, "not_timely_sorts": not_timely,
        "median_rt": G.median(rts),
        "rule_mismatch": mismatch})


def example_response(item, correct=True):
    """correct=True sorts by the active rule; False always picks the card no rule supports."""
    out, phase, streak = [], 0, 0
    for t in range(item["max_trials"]):
        if phase >= len(item["rules"]):
            break
        card = item["cards"][t]
        rule = item["rules"][phase]
        ch = card[FEATURE[rule]] if correct else ({0, 1, 2, 3} - set(card)).pop()
        out.append({"choice": ch, "rt": 1200, "rule": rule})
        if correct:
            streak += 1
            if streak >= item["criterion"]:
                phase, streak = phase + 1, 0
    return out
