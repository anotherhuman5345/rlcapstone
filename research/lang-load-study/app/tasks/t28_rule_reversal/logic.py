"""Rule reversal (card 28): two figures are shown side by side; one of them is the
"correct" one. The participant picks one and gets feedback (correct / wrong). After
CRITERION consecutive correct picks the rule reverses (the other figure becomes correct),
twice. The trial ends when the third phase reaches criterion, or after MAX_TRIALS picks.
Left/right position is randomized (balanced in blocks of two), so position never predicts
the answer. The item stores the two figures, which one is correct first, and the
position of figure 0 on every possible pick; the reversal schedule depends on the
participant's own picks, so score() replays the picks with the same rules (the oracle)
rather than trusting the browser. Both items of a pair use the same schedule constants
and different figures/positions, so they are equally hard."""

from app.tasks import _guard as G

TIMING = "window"     # each pick has a 3000 ms window (view.js answer(it.window_ms), item window_ms)
CRITERION = 4
REVERSALS = 2
MAX_TRIALS = 36
WINDOW_MS = 3000
RT_SLACK_MS = 50      # timer tolerance at the window end
SIDES = ("left", "right")
CEILING_MS = G.trial_ceiling(__file__)
FIGURES = ["triangle", "circle", "square", "star", "diamond", "cross"]
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        figs = rng.sample(range(len(FIGURES)), 2)
        cols = rng.sample(range(len(COLORS)), 2)
        left = []
        for _ in range(MAX_TRIALS // 2):
            blk = [0, 1]
            rng.shuffle(blk)
            left += blk
        items.append({"figures": [FIGURES[f] for f in figs], "colors": [COLORS[c] for c in cols],
                      "first": rng.choice([0, 1]), "left": left, "criterion": CRITERION,
                      "reversals": REVERSALS, "max_trials": MAX_TRIALS, "window_ms": WINDOW_MS})
    return items


def replay(item, choices):
    """Apply the task rules to a list of side choices ("left"/"right"/None).
    Returns per-pick rows and summary; picks after the task ended are ignored."""
    rule, streak, revs, phase, done = item["first"], 0, 0, 0, False
    rows = []
    for t, ch in enumerate(choices[: item["max_trials"]]):
        if done:
            break
        fig_left = item["left"][t]
        chosen = fig_left if ch == "left" else (1 - fig_left) if ch == "right" else None
        ok = chosen == rule
        rows.append({"phase": phase, "rule": rule, "chosen": chosen, "ok": ok})
        streak = streak + 1 if ok else 0
        if streak >= item["criterion"]:
            if revs < item["reversals"]:
                rule, revs, streak, phase = 1 - rule, revs + 1, 0, phase + 1
            else:
                done = True
    return rows, done


def _rule_field(a, r, active):
    """The browser's "rule" (figure index active before the pick): a mismatch metric only,
    never used for scoring. Missing / invalid values are flagged; returns True on mismatch."""
    v = r.get("rule", G.MISSING)
    if v is G.MISSING:
        a.malformed("missing_rule")
        return False
    if not G.member(v, (0, 1)):
        a.malformed("invalid_rule")
        return False
    return v != active


@G.safe
def score(item, response):
    """response: [{"choice": "left"|"right"|null, "rt": ms, "rule": figure index the
    browser had active before the pick}] in pick order.
    Every pick is classified (app/tasks/_guard.py): absent (no choice: the 3000 ms window,
    view.js answer(it.window_ms), ran out), invalid (unknown side, choice without rt or rt
    without choice, non-finite / negative / impossible rt), anticipatory (< 100 ms), late
    (beyond the window + 50 ms timer tolerance) or timely. The server replays the picks with
    the task rules (oracle); only a timely pick counts as made, every other one is replayed as
    an omission. The browser's "rule" field is only compared (rule_mismatch), never trusted.
    Picks after the replay ended (criterion reached or MAX_TRIALS) are flagged.
    hit = all three phases reached criterion (both reversals learned) within MAX_TRIALS.
    errors = wrong picks + omissions (incl. picks that were not timely). Metrics: trials to
    criterion per phase, errors after the first reversal, perseverative picks (old-rule figure
    chosen after a reversal before the first correct pick), median RT (timely picks), and
    whether the browser's active rule ever differed from the server replay (rule_mismatch)."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, list):
        return a.junk()
    raw = a.stream(response, "picks", cap=item["max_trials"])
    evs = [a.keyed(r, SIDES, key="choice", window=WINDOW_MS, slack=RT_SLACK_MS) for r in raw]
    choices = [k if st == G.TIMELY else None for st, k, _ in evs]
    rows, done = replay(item, choices)
    if len(raw) > len(rows):
        a.flag("picks_after_end", len(raw) - len(rows))
    mismatch = False
    for r, row in zip(raw, rows):
        if isinstance(r, dict) and _rule_field(a, r, row["rule"]):
            mismatch = True
    n_phases = item["reversals"] + 1
    to_crit = []
    for p in range(n_phases):
        prow = [r for r in rows if r["phase"] == p]
        reached = any(r["phase"] > p for r in rows) or (done and p == n_phases - 1)
        to_crit.append(len(prow) if reached else None)
    persev = 0
    for p in range(1, n_phases):
        for r in [r for r in rows if r["phase"] == p]:
            if r["ok"]:
                break
            if r["chosen"] == 1 - r["rule"]:
                persev += 1
    rts = [rt for (st, _, rt) in evs[: len(rows)] if st == G.TIMELY]
    errors = sum(not r["ok"] for r in rows)
    not_timely = sum(1 for (st, _, _) in evs[: len(rows)] if st in (G.INVALID, G.ANTICIPATORY, G.LATE))
    return a.finish(bool(done) and len(rows) > 0, errors, {
        "completed": bool(done), "picks": len(rows),
        "accuracy": round(sum(r["ok"] for r in rows) / len(rows), 3) if rows else 0.0,
        "trials_to_criterion": to_crit,
        "reversals_reached": sum(1 for p in range(1, n_phases) if any(r["phase"] >= p for r in rows)),
        "errors_after_reversal": sum(1 for r in rows if r["phase"] > 0 and not r["ok"]),
        "perseverative_picks": persev,
        "omissions": sum(1 for r in rows if r["chosen"] is None),
        "not_timely_picks": not_timely,
        "median_rt": G.median(rts),
        "rule_mismatch": mismatch})


def example_response(item, correct=True):
    """correct=True: always pick the currently correct figure; False: always the other."""
    out, rule, streak, revs = [], item["first"], 0, 0
    for t in range(item["max_trials"]):
        want = rule if correct else 1 - rule
        side = "left" if item["left"][t] == want else "right"
        out.append({"choice": side, "rt": 700, "rule": rule})
        if correct:
            streak += 1
            if streak >= item["criterion"]:
                if revs >= item["reversals"]:
                    break
                rule, revs, streak = 1 - rule, revs + 1, 0
    return out
