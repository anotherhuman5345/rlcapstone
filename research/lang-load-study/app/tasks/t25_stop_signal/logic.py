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
import math

GO = 24
STOP = 8
SSD_START, SSD_STEP, SSD_MIN, SSD_MAX = 250, 50, 50, 900
LIMIT_MS = 1000
ANTICIPATION_MS = 100
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


def _events(response):
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def _rt(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if 0 <= v <= LIMIT_MS + 50 else None


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2, 1)


def staircase(stopped_flags):
    """SSD used on each stop event, given whether each stop succeeded (oracle)."""
    ssd, out = SSD_START, []
    for ok in stopped_flags:
        out.append(ssd)
        ssd = min(SSD_MAX, ssd + SSD_STEP) if ok else max(SSD_MIN, ssd - SSD_STEP)
    return out


def score(item, response):
    """response: {"events": [{"key": "left"|"right"|null, "rt": ms from arrow onset,
    "ssd": delay used (stop events) or null}], "audio": bool, "interruptions": n}
    (a bare list is also accepted), in event order.
    Go event: correct = key matches the arrow within 1000 ms; no key = omission; wrong
    key = choice error. Stop event: success = no key at all within the 1000 ms window.
    errors = go omissions + go choice errors + failed stops.
    hit = go accuracy >= 0.80 AND stop success >= 0.25 (the person really tries to stop;
    with the staircase about 50 % is expected).
    Metrics: go accuracy/omissions/choice errors, go RT median/mean (correct, >= 100 ms),
    stop success rate, signal-respond RT mean (should be faster than go RT: race check),
    SSD trajectory (oracle), mean SSD, boundary hits, browser/oracle SSD mismatches,
    go-RT slowing from first to second half (a waiting-strategy flag), no SSRT."""
    try:
        evs = item["events"]
        resp = _events(response)
        rows = []
        for k, e in enumerate(evs):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            key = r.get("key") if r.get("key") in ("left", "right") else None
            rows.append({"e": e, "key": key, "rt": _rt(r.get("rt")) if key else None, "ssd_b": r.get("ssd")})
        go = [r for r in rows if not r["e"]["stop"]]
        stop = [r for r in rows if r["e"]["stop"]]
        go_ok = [r for r in go if r["key"] == r["e"]["dir"]]
        omis = sum(1 for r in go if r["key"] is None)
        choice_err = len(go) - len(go_ok) - omis
        stopped = [r["key"] is None for r in stop]
        ssds = staircase(stopped)
        mismatch = sum(1 for r, s in zip(stop, ssds) if r["ssd_b"] != s)
        go_rts = [r["rt"] for r in go_ok if r["rt"] is not None and r["rt"] >= ANTICIPATION_MS]
        sr_rts = [r["rt"] for r in stop if r["rt"] is not None]
        half = len(rows) // 2
        first = _median([r["rt"] for r in rows[:half] if r in go_ok and r["rt"] and r["rt"] >= ANTICIPATION_MS])
        second = _median([r["rt"] for r in rows[half:] if r in go_ok and r["rt"] and r["rt"] >= ANTICIPATION_MS])
        go_acc = len(go_ok) / len(go)
        stop_rate = sum(stopped) / len(stop)
        go_mean = round(sum(go_rts) / len(go_rts), 1) if go_rts else None
        sr_mean = round(sum(sr_rts) / len(sr_rts), 1) if sr_rts else None
        inter = response.get("interruptions") if isinstance(response, dict) else None
        audio = response.get("audio") if isinstance(response, dict) else None
        return {"hit": go_acc >= 0.8 and stop_rate >= 0.25,
                "errors": omis + choice_err + (len(stop) - sum(stopped)),
                "metrics": {"go_accuracy": round(go_acc, 3), "go_omissions": omis, "go_choice_errors": choice_err,
                            "go_rt_median": _median(go_rts), "go_rt_mean": go_mean, "go_rt_n": len(go_rts),
                            "stop_success_rate": round(stop_rate, 3),
                            "signal_respond_rt_mean": sr_mean,
                            "race_check_ok": (sr_mean < go_mean) if sr_mean is not None and go_mean is not None else None,
                            "ssd_trajectory": ssds, "ssd_mean": round(sum(ssds) / len(ssds), 1),
                            "ssd_boundary_hits": sum(1 for s in ssds if s in (SSD_MIN, SSD_MAX)),
                            "ssd_mismatches": mismatch,
                            "go_rt_slowing_ms": round(second - first, 1) if first is not None and second is not None else None,
                            "ssrt": None,
                            "audio": audio if isinstance(audio, bool) else None,
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


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
