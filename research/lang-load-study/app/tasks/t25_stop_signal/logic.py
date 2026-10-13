"""Stop-signal (card 25): an arrow points left or right; press the matching key as fast as
possible. On 25 % of events the arrow turns red inside a red ring (and, if sound is on, a
short beep plays) a moment after it appears: then try NOT to press.
One trial is a block of 32 events: 24 go + 8 stop, left and right equally often in both
(12+12 go, 4+4 stop), the first two events always go and never two stop events in a row.
Both items of a pair share these counts and constraints; only the order differs.

Stop-signal delay (SSD) staircase, run live in the browser and re-run here as the
oracle: starts at 250 ms each block, +50 ms after a successful stop, -50 ms after a
failed stop, bounded to [50, 900] ms. If a press comes before the scheduled SSD the
signal is not shown and the stop counts as failed. The browser's SSDs are compared with
the oracle's (ssd_mismatches); the oracle's values are the ones reported.
No SSRT is computed: 8 stop events per block cannot support a validated estimator, and
go-RT-minus-SSD is not a validated SSRT."""
from app.tasks import _guard as G

TIMING = "window"      # every event has a 1000 ms response window (see _guard.py)
GO = 24
STOP = 8
SSD_START, SSD_STEP, SSD_MIN, SSD_MAX = 250, 50, 50, 900
LIMIT_MS = 1000
WINDOW_MS = LIMIT_MS
RT_SLACK_MS = 50       # timer tolerance: an rt up to 1050 ms is still inside the window
ANTICIPATION_MS = G.ANTICIPATION_MS
CEILING_MS = G.trial_ceiling(__file__)
FLIP = {"left": "right", "right": "left"}


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        while True:
            ev = ([{"dir": d, "stop": False} for d in ("left", "right") for _ in range(GO // 2)]
                  + [{"dir": d, "stop": True} for d in ("left", "right") for _ in range(STOP // 2)])
            ev = [dict(e) for e in ev]
            rng.shuffle(ev)
            if not ev[0]["stop"] and not ev[1]["stop"] and all(not (a["stop"] and b["stop"]) for a, b in zip(ev, ev[1:])):
                break
        items.append({"events": ev, "limit_ms": LIMIT_MS,
                      "ssd": {"start": SSD_START, "step": SSD_STEP, "min": SSD_MIN, "max": SSD_MAX}})
    return items


def staircase(stopped_flags):
    """SSD used on each stop event, given whether each stop succeeded (oracle)."""
    ssd, out = SSD_START, []
    for ok in stopped_flags:
        out.append(ssd)
        ssd = min(SSD_MAX, ssd + SSD_STEP) if ok else max(SSD_MIN, ssd - SSD_STEP)
    return out


@G.safe
def score(item, response):
    """response: {"events": [{"key": "left"|"right"|null, "rt": ms from arrow onset,
    "ssd": delay used (stop events) or null}], "audio": bool, "interruptions": n}
    (a bare list of events is also accepted, without the metadata), in event order.

    Every event is classified first (app/tasks/_guard.py): absent (no key, no rt), invalid
    (unknown key, key without rt or rt without key, non-finite/negative/impossible rt,
    entry missing), anticipatory (rt < 100 ms), late (rt beyond the 1000 ms window + 50 ms
    tolerance; the browser never sends one) or timely.
    Go event: correct = a TIMELY press of the arrow's key; no press = omission; a timely
    wrong key = choice error; anticipatory, late and invalid presses are errors of their
    own kind and never correct. Stop event: success = absent (no key at all within the
    window); any press is a failed stop (signal-respond); an invalid entry is neither a
    success nor a usable failure (it counts against stopping and is flagged).
    errors = go events not correct + stop events not successful.
    hit = go accuracy >= 0.80 AND stop success >= 0.25 (the person really tries to stop;
    with the staircase about 50 % is expected). Go accuracy and stopping are reported
    separately, with every event's status in metrics["events"].
    Metrics: go accuracy/omissions/choice errors/anticipations, go RT median/mean (correct,
    timely), stop success rate, signal-respond RT mean (timely presses on stop events;
    should be faster than go RT: race check), SSD trajectory (oracle), mean SSD, boundary
    hits, browser/oracle SSD mismatches, go-RT slowing from first to second half (a
    waiting-strategy flag), no SSRT."""
    a = G.Audit(CEILING_MS)
    evs = item["events"]
    is_dict = isinstance(response, dict)
    if not (is_dict or isinstance(response, list)):
        return a.junk(len(evs))
    raw = response.get("events") if is_dict else response
    rows = []
    for k, (e, r) in enumerate(zip(evs, a.entries(raw, len(evs)))):
        status, key, rt = a.keyed(r, FLIP, window=LIMIT_MS, slack=RT_SLACK_MS)
        ssd_b = r.get("ssd", G.MISSING) if isinstance(r, dict) else G.MISSING
        if e["stop"]:
            if not (G.is_int(ssd_b) and SSD_MIN <= ssd_b <= SSD_MAX):
                if ssd_b is not G.MISSING or isinstance(r, dict):
                    a.malformed("invalid_ssd")
                ssd_b = None
            if status == G.ABSENT:
                outcome = "stopped"
            elif status == G.INVALID:
                outcome = "invalid"
            else:
                outcome = "failed"
        else:
            if isinstance(r, dict) and ssd_b is not None and ssd_b is not G.MISSING:
                a.malformed("invalid_ssd")
            outcome = {G.ABSENT: "omission", G.INVALID: "invalid", G.ANTICIPATORY: "anticipation",
                       G.LATE: "late"}.get(status) or ("correct" if key == e["dir"] else "choice_error")
        rows.append({"i": k, "type": "stop" if e["stop"] else "go", "dir": e["dir"], "status": status,
                     "key": key, "rt": rt, "outcome": outcome, "ssd_b": ssd_b})
    go = [r for r in rows if r["type"] == "go"]
    stop = [r for r in rows if r["type"] == "stop"]
    count = lambda rs, o: sum(1 for r in rs if r["outcome"] == o)  # noqa: E731
    go_ok = [r for r in go if r["outcome"] == "correct"]
    stopped = [r["outcome"] == "stopped" for r in stop]
    ssds = staircase(stopped)
    for r, s in zip(stop, ssds):
        r["ssd"] = s
    mismatch = sum(1 for r, s in zip(stop, ssds) if r["ssd_b"] != s)
    go_rts = [r["rt"] for r in go_ok]
    sr_rts = [r["rt"] for r in stop if r["outcome"] == "failed" and r["status"] == G.TIMELY]
    half = len(rows) // 2
    first = G.median([r["rt"] for r in rows[:half] if r["outcome"] == "correct"])
    second = G.median([r["rt"] for r in rows[half:] if r["outcome"] == "correct"])
    go_acc = len(go_ok) / len(go) if go else 0.0
    stop_rate = sum(stopped) / len(stop) if stop else 0.0
    go_mean, sr_mean = G.mean(go_rts), G.mean(sr_rts)
    meta = response if is_dict else {}
    audio = a.opt_bool(meta, "audio", required=is_dict)
    inter = a.opt_int(meta, "interruptions", required=is_dict)
    return a.finish(
        bool(go) and bool(stop) and go_acc >= 0.8 and stop_rate >= 0.25,
        (len(go) - len(go_ok)) + (len(stop) - sum(stopped)),
        {"go_accuracy": round(go_acc, 3), "go_correct": len(go_ok), "go_n": len(go),
         "go_omissions": count(go, "omission"), "go_choice_errors": count(go, "choice_error"),
         "go_anticipations": count(go, "anticipation"), "go_late": count(go, "late"),
         "go_invalid": count(go, "invalid"),
         "go_rt_median": G.median(go_rts), "go_rt_mean": go_mean, "go_rt_n": len(go_rts),
         "stop_success_rate": round(stop_rate, 3), "stop_n": len(stop),
         "stop_successes": sum(stopped), "stop_failures": count(stop, "failed"),
         "stop_invalid": count(stop, "invalid"),
         "signal_respond_rt_mean": sr_mean,
         "race_check_ok": (sr_mean < go_mean) if sr_mean is not None and go_mean is not None else None,
         "ssd_trajectory": ssds, "ssd_mean": round(sum(ssds) / len(ssds), 1) if ssds else None,
         "ssd_boundary_hits": sum(1 for s in ssds if s in (SSD_MIN, SSD_MAX)),
         "ssd_mismatches": mismatch,
         "go_rt_slowing_ms": round(second - first, 1) if first is not None and second is not None else None,
         "ssrt": None, "audio": audio, "interruptions": inter,
         "events": [{"i": r["i"], "type": r["type"], "status": r["status"], "outcome": r["outcome"],
                     "rt": r["rt"], "ssd": r.get("ssd")} for r in rows]})


def example_response(item, correct=True):
    """correct: every go answered correctly, stops alternate success/failure (SSDs follow
    the staircase). wrong: every go answered with the wrong key, no stop withheld."""
    out, n_stop, ok_flags = [], 0, []
    for e in item["events"]:
        if e["stop"]:
            success = correct and n_stop % 2 == 0
            ok_flags.append(success)
            ssd = staircase(ok_flags)[-1]
            out.append({"key": None if success else e["dir"], "rt": None if success else 380, "ssd": ssd})
            n_stop += 1
        else:
            out.append({"key": e["dir"] if correct else FLIP[e["dir"]], "rt": 450, "ssd": None})
    return {"events": out, "audio": True, "interruptions": 0}
