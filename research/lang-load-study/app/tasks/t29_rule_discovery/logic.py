"""Rule discovery (card 29): sort a card onto one of four reference cards by an
unannounced rule (same COLOR, same SHAPE, or same COUNT) learned from correct/wrong
feedback. After CRITERION correct sorts in a row the rule changes, without warning, to
the next rule in item["rules"]; the trial ends when all three rules have been found or
after MAX_TRIALS sorts. Reference card i has color i, shape i and i+1 figures. Every
card to sort differs in color, shape and count (one of the 24 such cards), so the three
rules always point to three different reference cards and one reference card is never
right: no card makes the rules agree. Both items of a pair share the rule order (the
main source of difficulty) and differ in card order. Original drawn stimuli."""

CRITERION = 4
MAX_TRIALS = 36
WINDOW_MS = 5000
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


def score(item, response):
    """response: [{"choice": 0-3 | null, "rt": ms, "rule": rule name active before the
    sort}] in sort order.
    hit = all three rules found (criterion reached in every phase) within MAX_TRIALS.
    errors = wrong sorts + omissions. Metrics: categories completed, trials to criterion
    per rule, trials to first category, perseverative errors (sorted by the previous,
    now-wrong rule), other errors, total correct, median RT, rule_mismatch (the browser's
    active rule differed from the server replay)."""
    try:
        resp = response if isinstance(response, list) else []
        choices = []
        for r in resp:
            c = r.get("choice") if isinstance(r, dict) else None
            choices.append(c if isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 3 else None)
        rows, cats = replay(item, choices)
    except (TypeError, KeyError, IndexError):
        return {"hit": False, "errors": 0, "metrics": {}}
    n_rules = len(item["rules"])
    to_crit = [sum(1 for r in rows if r["phase"] == p) if cats > p else None for p in range(n_rules)]
    rts = sorted(float(r["rt"]) for r in resp[: len(rows)] if isinstance(r, dict)
                 and isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) and r["rt"] > 0)
    mismatch = any(isinstance(r, dict) and r.get("rule") is not None and r.get("rule") != item["rules"][row["phase"]]
                   for r, row in zip(resp, rows))
    persev = sum(r["persev"] for r in rows)
    errors = sum(not r["ok"] for r in rows)
    return {"hit": cats >= n_rules and len(rows) > 0, "errors": errors,
            "metrics": {"categories_completed": cats, "sorts": len(rows),
                        "total_correct": sum(r["ok"] for r in rows),
                        "trials_to_criterion": to_crit, "trials_to_first_category": to_crit[0] if to_crit else None,
                        "perseverative_errors": persev,
                        "other_errors": errors - persev - sum(1 for r in rows if r["choice"] is None),
                        "omissions": sum(1 for r in rows if r["choice"] is None),
                        "median_rt": round(rts[len(rts) // 2], 1) if rts else None,
                        "rule_mismatch": mismatch}}


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
