"""Interruption recovery (card 63), adapted to one trial of two matched cases.

Each case is a 6-step procedure. The procedure list stays on screen; the participant
carries it out by clicking step buttons from a palette of 8 (the 6 steps + 2 unused
ones, in a different order). Nothing marks which steps are already done. The case
ends after 6 clicks. In one of the two cases (fixed stage: after the 3rd click) the
screen is replaced by an unrelated even/odd digit task lasting a fixed 9 s
(6 digits x 1.5 s); then the procedure comes back exactly as it was, with no cue.
The other case is the no-interruption control.

Step names come from text "steps" by index. Pairs (k, k+1) share the case order and
interruption stage; step names and orders differ.
"""

N_STEPS_POOL = 16      # length of text "steps"
PROC_LEN, PALETTE = 6, 8
INTERRUPT_AFTER = 3
PARITY_N, PARITY_MS = 6, 1500


def _case(rng, interrupted):
    steps = rng.sample(range(N_STEPS_POOL), PALETTE)
    proc = steps[:PROC_LEN]
    palette = rng.sample(steps, PALETTE)
    return {"procedure": proc, "palette": palette, "interrupt_after": INTERRUPT_AFTER if interrupted else None}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        first_interrupted = rng.random() < 0.5
        for _ in range(2):
            cases = [_case(rng, first_interrupted), _case(rng, not first_interrupted)]
            digits = [rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9]) for _ in range(PARITY_N)]
            items.append({"cases": cases, "parity_digits": digits, "parity_ms": PARITY_MS,
                          "limit_ms": 140000})
    return items[:n]


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def score(item, response):
    """response: {"cases": [{"clicks": [[step_id, t_ms], ...], "resume_at": t_ms or null}, ...]
    (one per case, times from the case start), "parity": [{"key": "even"|"odd"|null,
    "rt": ms}, ...]}.
    Per case the clicked sequence is compared with the procedure position by position.
    Resumption lag = time of the first click after the interruption minus resume_at;
    its cost = lag minus the same inter-click interval (click 3 -> 4) in the control case.
    hit = both cases carried out exactly (all 6 steps, right order, nothing extra)."""
    miss = {"hit": False, "errors": 2 * PROC_LEN, "metrics": {}}
    if not isinstance(response, dict) or not isinstance(response.get("cases"), list):
        return miss
    rc = response["cases"]
    exact, errors, post_err, lag, ctrl_gap, completed = [], 0, None, None, None, 0
    for k, case in enumerate(item["cases"]):
        r = rc[k] if k < len(rc) and isinstance(rc[k], dict) else {}
        clicks = [c for c in (r.get("clicks") or []) if isinstance(c, list) and len(c) == 2] \
            if isinstance(r.get("clicks"), list) else []
        seq = [c[0] for c in clicks]
        times = [_num(c[1]) for c in clicks]
        proc = case["procedure"]
        wrong = [i for i in range(PROC_LEN) if i >= len(seq) or seq[i] != proc[i]]
        errors += len(wrong) + max(0, len(seq) - PROC_LEN)
        exact.append(seq == proc)
        completed += len(seq) >= PROC_LEN
        s = INTERRUPT_AFTER
        if case["interrupt_after"] is not None:
            post_err = sum(1 for i in wrong if i >= s)
            ra = _num(r.get("resume_at"))
            if ra is not None and len(times) > s and times[s] is not None:
                lag = times[s] - ra
        elif len(times) > s and times[s] is not None and times[s - 1] is not None:
            ctrl_gap = times[s] - times[s - 1]
    pr = response.get("parity") if isinstance(response.get("parity"), list) else []
    par_ok = 0
    for k, d in enumerate(item["parity_digits"]):
        p = pr[k] if k < len(pr) and isinstance(pr[k], dict) else {}
        par_ok += p.get("key") == ("even" if d % 2 == 0 else "odd")
    i_int = 0 if item["cases"][0]["interrupt_after"] is not None else 1
    return {"hit": all(exact) and len(exact) == 2,
            "errors": errors,
            "metrics": {"interrupted_case_exact": exact[i_int], "control_case_exact": exact[1 - i_int],
                        "cases_completed": completed, "post_interruption_errors": post_err,
                        "resumption_lag_ms": round(lag, 1) if lag is not None else None,
                        "control_interval_ms": round(ctrl_gap, 1) if ctrl_gap is not None else None,
                        "resumption_cost_ms": round(lag - ctrl_gap, 1) if lag is not None and ctrl_gap is not None else None,
                        "parity_accuracy": round(par_ok / len(item["parity_digits"]), 3)}}


def example_response(item, correct=True):
    cases = []
    for case in item["cases"]:
        proc = case["procedure"] if correct else case["procedure"][::-1]
        t, clicks, resume = 0, [], None
        for i, sid in enumerate(proc):
            t += 1500
            if case["interrupt_after"] is not None and i == case["interrupt_after"]:
                t += 9000
                resume = t
                t += 2500
            clicks.append([sid, t])
        cases.append({"clicks": clicks, "resume_at": resume})
    parity = [{"key": "even" if d % 2 == 0 else "odd", "rt": 600} for d in item["parity_digits"]]
    return {"cases": cases, "parity": parity}
