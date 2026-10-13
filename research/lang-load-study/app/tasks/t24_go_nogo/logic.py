"""Go/no-go (card 24): press for a circle (go), do not press for a triangle (no-go).
Shapes follow a fixed 1000 ms onset schedule (shape 500 ms + blank 500 ms); a press never
moves the next onset. One trial is a block of 40 shapes with exactly 8 no-go (20 %),
the first two always go and never two no-go in a row. Both items of a pair share these
counts and constraints; only the order differs. Whether a shape is go is decided from
its shape here, not from anything the browser sends."""
import math

BLOCK = 40
NOGO = 8
CYCLE_MS = 1000
SHOW_MS = 500
ANTICIPATION_MS = 100


def _order(rng):
    while True:
        seq = ["triangle"] * NOGO + ["circle"] * (BLOCK - NOGO)
        rng.shuffle(seq)
        if seq[0] == seq[1] == "circle" and all(not (a == b == "triangle") for a, b in zip(seq, seq[1:])):
            return seq


def generate(rng, n, save_image):
    return [{"shapes": _order(rng), "cycle_ms": CYCLE_MS, "show_ms": SHOW_MS} for _ in range(n)]


def _events(response):
    ev = response.get("events") if isinstance(response, dict) else response
    return ev if isinstance(ev, list) else []


def _rt(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v) if 0 <= v < CYCLE_MS + 50 else None


def _dprime(hits, n_sig, fas, n_noise):
    """Log-linear correction: rates (count + 0.5) / (trials + 1)."""
    from statistics import NormalDist
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_sig + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


def score(item, response):
    """response: {"events": [{"rt": ms from shape onset of the FIRST valid press in that
    shape's 1000 ms window, or null; "extra": further presses in the window}],
    "interruptions": n} (a bare list is also accepted), one entry per shape in order.
    Only the response key/button counts; other keys and key auto-repeat are ignored in
    the browser. A press = an entry with a valid rt.
    Go (circle): press = hit, no press = omission. No-go (triangle): press = commission,
    no press = correct rejection. Presses < 100 ms are flagged as anticipations but still
    count as presses. errors = omissions + commissions.
    hit = go hit rate >= 0.80 AND at least half of the no-go shapes withheld.
    Metrics: omission and commission counts/rates, median/mean/SD go RT (correct go only,
    anticipations excluded), d' with the (count+0.5)/(n+1) correction."""
    try:
        shapes = item["shapes"]
        resp = _events(response)
        go_rts, hits, omis, comm, antic, extra = [], 0, 0, 0, 0, 0
        for k, s in enumerate(shapes):
            r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
            rt = _rt(r.get("rt"))
            pressed = rt is not None
            if isinstance(r.get("extra"), int) and not isinstance(r.get("extra"), bool):
                extra += max(0, r["extra"])
            if pressed and rt < ANTICIPATION_MS:
                antic += 1
            if s == "circle":
                if pressed:
                    hits += 1
                    if rt >= ANTICIPATION_MS:
                        go_rts.append(rt)
                else:
                    omis += 1
            elif pressed:
                comm += 1
        n_go = sum(1 for s in shapes if s == "circle")
        n_nogo = len(shapes) - n_go
        go_rts.sort()
        med = mean = sd = None
        if go_rts:
            m = len(go_rts) // 2
            med = round(go_rts[m] if len(go_rts) % 2 else (go_rts[m - 1] + go_rts[m]) / 2, 1)
            mean = sum(go_rts) / len(go_rts)
            sd = round(math.sqrt(sum((x - mean) ** 2 for x in go_rts) / (len(go_rts) - 1)), 1) if len(go_rts) > 1 else None
            mean = round(mean, 1)
        hit = hits / n_go >= 0.8 and (n_nogo - comm) / n_nogo >= 0.5
        inter = response.get("interruptions") if isinstance(response, dict) else None
        return {"hit": bool(hit), "errors": omis + comm,
                "metrics": {"go_hits": hits, "go_omissions": omis, "go_omission_rate": round(omis / n_go, 3),
                            "nogo_commissions": comm, "nogo_commission_rate": round(comm / n_nogo, 3),
                            "nogo_correct_rejections": n_nogo - comm,
                            "go_rt_median": med, "go_rt_mean": mean, "go_rt_sd": sd, "go_rt_n": len(go_rts),
                            "dprime": _dprime(hits, n_go, comm, n_nogo),
                            "anticipations": antic, "extra_presses": extra,
                            "interruptions": inter if isinstance(inter, int) else None}}
    except Exception:
        return {"hit": False, "errors": 0, "metrics": {}}


def example_response(item, correct=True):
    ev = []
    for s in item["shapes"]:
        press = (s == "circle") if correct else (s == "triangle")
        ev.append({"rt": 420 if press else None, "extra": 0})
    return {"events": ev, "interruptions": 0}
