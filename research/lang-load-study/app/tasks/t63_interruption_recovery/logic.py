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
from app.tasks import _guard as G

TIMING = "limit"
N_STEPS_POOL = 16      # length of text "steps"
PROC_LEN, PALETTE = 6, 8
INTERRUPT_AFTER = 3
PARITY_N, PARITY_MS = 6, 1500
LIMIT_MS = 140000      # item limit_ms: view.js ends the trial with setTimeout(end, it.limit_ms) from Start
BETWEEN_MS = 1500      # view.js: pause between the cases (setTimeout(startCase, 1500))
TIME_SLACK_MS = 1000   # timer tolerance at the limit
RESUME_SLACK_MS = 50   # resume_at comes from a setTimeout that never fires early
MAX_CLICKS = 50
CEILING_MS = G.trial_ceiling(__file__)


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
                          "limit_ms": LIMIT_MS})
    return items[:n]


def _case_clicks(a, case, r, limit):
    """Validated clicks of one case -> (seq, times, ok). A click must be [step_id, t] with
    step_id on the case's palette and t a finite time 0..limit from the case start; times
    must increase. Malformed clicks are flagged and not applied (ok = False)."""
    raw = a.stream(r.get("clicks", G.MISSING), "clicks", cap=MAX_CLICKS)
    if len(raw) > PROC_LEN:
        a.malformed("extra_clicks")          # the case ends after 6 clicks
    seq, times, ok = [], [], True
    for c in raw[:PROC_LEN]:
        if not isinstance(c, list) or len(c) != 2:
            a.malformed("invalid_click")
            ok = False
            continue
        sid = a.choice(c[0], case["palette"], "click_step")
        st, t = a.time(c[1], field="click_t", window=limit, slack=TIME_SLACK_MS, floor=0, required=True)
        if sid is None:
            a.malformed("missing_click_step")
        if sid is None or sid is G.BAD or st == G.INVALID:
            ok = False
            continue
        if st == G.LATE:
            ok = False
        seq.append(sid)
        times.append(t)
    if not a.monotonic(times, "click_t"):
        ok = False
    if len(set(times)) < len(times):
        a.malformed("duplicate_click_t")
        ok = False
    return seq, times, ok and len(raw) <= PROC_LEN


@G.safe
def score(item, response):
    """response: {"cases": [{"clicks": [[step_id, t_ms], ...], "resume_at": t_ms or null}, ...]
    (one per started case, times from the case start), "parity": [{"key": "even"|"odd"|null,
    "rt": ms}, ...] (one per digit)}.
    Clicks are validated: step_id on the case's palette, t finite, >= 0, inside the
    140 s limit (item limit_ms, view.js), strictly increasing, at most 6 per case; resume_at
    must be a valid time in the interrupted case (at least the 9 s digit task after click 3,
    and before click 4) and null in the control case. Malformed clicks are flagged and not
    applied. Per case the clicked sequence is compared with the procedure position by position.
    A case counts as carried out only when its clicks are all well formed and its final
    (6th) click is inside the limit; the two cases together (+ the 1.5 s pause) must end
    inside the limit too.
    Resumption lag = time of the first click after the interruption minus resume_at;
    its cost = lag minus the same inter-click interval (click 3 -> 4) in the control case.
    Parity answers are classified (absent / invalid / anticipatory / late beyond the 1.5 s
    digit / timely); only timely answers equal to the digit's parity count.
    hit = both cases carried out exactly (all 6 steps, right order, nothing extra) with
    valid timing."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(2 * PROC_LEN)
    limit = item.get("limit_ms", LIMIT_MS)
    rc = a.stream(response.get("cases", G.MISSING), "cases", cap=len(item["cases"]) + 5)
    if len(rc) > len(item["cases"]):
        a.malformed("extra_cases")
    exact, timing_ok, errors, post_err, lag, ctrl_gap, completed, ends = [], [], 0, None, None, None, 0, []
    for k, case in enumerate(item["cases"]):
        r = rc[k] if k < len(rc) else {}
        if not isinstance(r, dict):
            a.malformed("case_not_object")
            r = {}
        seq, times, ok = _case_clicks(a, case, r, limit) if k < len(rc) else ([], [], False)
        proc = case["procedure"]
        wrong = [i for i in range(PROC_LEN) if i >= len(seq) or seq[i] != proc[i]]
        errors += len(wrong) + max(0, len(seq) - PROC_LEN)
        s = INTERRUPT_AFTER
        if k < len(rc):
            ra_raw = r.get("resume_at", G.MISSING)
            if ra_raw is G.MISSING:
                a.malformed("missing_resume_at")
                ok = False
            elif case["interrupt_after"] is None:
                if ra_raw is not None:
                    a.malformed("resume_at_in_control_case")
                    ok = False
            else:
                need = len(times) > s
                st, ra = a.time(ra_raw, field="resume_at", window=limit, slack=TIME_SLACK_MS, floor=0,
                                required=need)
                if st in (G.INVALID, G.LATE):
                    ok = False
                    ra = None
                if ra is not None:
                    busy = PARITY_N * item.get("parity_ms", PARITY_MS)
                    if len(times) < s or ra < times[s - 1] + busy - RESUME_SLACK_MS:
                        a.malformed("resume_before_interruption_end")
                        ok = False
                    elif len(times) > s and times[s] < ra:
                        a.malformed("click_during_interruption")
                        ok = False
                    elif len(times) > s:
                        lag = times[s] - ra
        if case["interrupt_after"] is not None:
            post_err = sum(1 for i in wrong if i >= s)
        elif len(times) > s:
            ctrl_gap = times[s] - times[s - 1]
        done = len(seq) >= PROC_LEN
        completed += done
        exact.append(seq == proc)
        timing_ok.append(ok and done)
        ends.append(times[-1] if done and times else None)
    if all(t is not None for t in ends) and sum(ends) + BETWEEN_MS > limit + TIME_SLACK_MS:
        a.malformed("cases_exceed_limit")
        timing_ok = [False] * len(timing_ok)
    for e, t in zip(exact, timing_ok):
        if e and not t:
            a.flag("exact_case_with_invalid_timing")

    raw_p = response.get("parity", G.MISSING)
    if raw_p is G.MISSING:
        a.malformed("missing_parity")
        raw_p = []
    par_ok, par_rts = 0, []
    p_ms = item.get("parity_ms", PARITY_MS)
    for d, p in zip(item["parity_digits"], a.entries(raw_p, len(item["parity_digits"]), "parity")):
        st, key, rt = a.keyed(p, ("even", "odd"), window=p_ms)
        if st == G.TIMELY and key == ("even" if d % 2 == 0 else "odd"):
            par_ok += 1
            par_rts.append(rt)
    i_int = 0 if item["cases"][0]["interrupt_after"] is not None else 1
    good = [e and t for e, t in zip(exact, timing_ok)]
    return a.finish(all(good) and len(good) == 2, errors, {
        "interrupted_case_exact": exact[i_int], "control_case_exact": exact[1 - i_int],
        "interrupted_case_ok": good[i_int], "control_case_ok": good[1 - i_int],
        "cases_completed": completed, "post_interruption_errors": post_err,
        "resumption_lag_ms": round(lag, 1) if lag is not None else None,
        "control_interval_ms": round(ctrl_gap, 1) if ctrl_gap is not None else None,
        "resumption_cost_ms": round(lag - ctrl_gap, 1) if lag is not None and ctrl_gap is not None else None,
        "parity_accuracy": round(par_ok / len(item["parity_digits"]), 3),
        "parity_rt_mean": G.mean(par_rts)})


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
