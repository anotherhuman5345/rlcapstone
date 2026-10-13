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

CRITERION = 4
REVERSALS = 2
MAX_TRIALS = 36
WINDOW_MS = 3000
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


def score(item, response):
    """response: [{"choice": "left"|"right"|null, "rt": ms, "rule": figure index the
    browser had active before the pick}] in pick order.
    hit = all three phases reached criterion (both reversals learned) within MAX_TRIALS.
    errors = wrong picks + omissions. Metrics: trials to criterion per phase, errors after
    the first reversal, perseverative picks (old-rule figure chosen after a reversal before
    the first correct pick), median RT, and whether the browser's active rule ever differed
    from the server replay (rule_mismatch)."""
    try:
        resp = response if isinstance(response, list) else []
        choices = []
        for r in resp:
            c = r.get("choice") if isinstance(r, dict) else None
            choices.append(c if c in ("left", "right") else None)
        rows, done = replay(item, choices)
    except (TypeError, KeyError, IndexError):
        return {"hit": False, "errors": 0, "metrics": {}}
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
    rts = sorted(float(r["rt"]) for r in resp[: len(rows)] if isinstance(r, dict)
                 and isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) and r["rt"] > 0)
    mismatch = any(isinstance(r, dict) and r.get("rule") is not None and r.get("rule") != row["rule"]
                   for r, row in zip(resp, rows))
    errors = sum(not r["ok"] for r in rows)
    return {"hit": bool(done) and len(rows) > 0, "errors": errors,
            "metrics": {"completed": bool(done), "picks": len(rows),
                        "accuracy": round(sum(r["ok"] for r in rows) / len(rows), 3) if rows else 0.0,
                        "trials_to_criterion": to_crit,
                        "reversals_reached": sum(1 for p in range(1, n_phases) if any(r["phase"] >= p for r in rows)),
                        "errors_after_reversal": sum(1 for r in rows if r["phase"] > 0 and not r["ok"]),
                        "perseverative_picks": persev,
                        "omissions": sum(1 for r in rows if r["chosen"] is None),
                        "median_rt": round(rts[len(rts) // 2], 1) if rts else None,
                        "rule_mismatch": mismatch}}


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
