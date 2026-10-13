"""Go/no-go (card 24): press for a circle (go), do not press for a triangle (no-go).
Shapes follow a fixed 1000 ms onset schedule (shape 500 ms + blank 500 ms); a press never
moves the next onset. One trial is a block of 40 shapes with exactly 8 no-go (20 %),
the first two always go and never two no-go in a row. Both items of a pair share these
counts and constraints; only the order differs. Whether a shape is go is decided from
its shape here, not from anything the browser sends."""
import math

from app.tasks import _guard as G

TIMING = "window"
BLOCK = 40
NOGO = 8
CYCLE_MS = 1000
SHOW_MS = 500
ANTICIPATION_MS = G.ANTICIPATION_MS
WINDOW_MS = CYCLE_MS     # a press belongs to the shape whose 1000 ms window it falls in
RT_SLACK_MS = 50
CEILING_MS = G.trial_ceiling(__file__)


def _order(rng):
    while True:
        seq = ["triangle"] * NOGO + ["circle"] * (BLOCK - NOGO)
        rng.shuffle(seq)
        if seq[0] == seq[1] == "circle" and all(not (a == b == "triangle") for a, b in zip(seq, seq[1:])):
            return seq


def generate(rng, n, save_image):
    return [{"shapes": _order(rng), "cycle_ms": CYCLE_MS, "show_ms": SHOW_MS} for _ in range(n)]


def _dprime(hits, n_sig, fas, n_noise):
    """Log-linear correction: rates (count + 0.5) / (trials + 1)."""
    from statistics import NormalDist
    z = NormalDist().inv_cdf
    return round(z((hits + 0.5) / (n_sig + 1)) - z((fas + 0.5) / (n_noise + 1)), 3)


@G.safe
def score(item, response):
    """response: {"events": [{"rt": ms from shape onset of the FIRST valid press in that
    shape's 1000 ms window, or null; "extra": further presses in the window}],
    "interruptions": n} (a bare list of events is also accepted, without the metadata),
    one entry per shape in order. Only the response key/button counts; other keys and key
    auto-repeat are ignored in the browser.
    Each entry is classified (app/tasks/_guard.py): absent (rt null), invalid (not a
    finite non-negative number, impossible, or the entry is missing), anticipatory
    (< 100 ms), late (beyond the 1000 ms window + 50 ms tolerance; the browser never sends
    one) or timely. Whether a shape is go is decided from its shape here.
    Go (circle): hit = a TIMELY press; absent = omission; an anticipatory, late or invalid
    entry is an error, never a hit. No-go (triangle): correct rejection = absent only; any
    press (timely, anticipatory or late) is a commission; an invalid entry is never a
    correct rejection. errors = go events not hit + no-go events not correctly rejected.
    hit = go hit rate >= 0.80 AND at least half of the no-go shapes withheld.
    Metrics: omission and commission counts/rates, anticipations, invalid entries,
    median/mean/SD go RT (timely go hits), d' with the (count+0.5)/(n+1) correction."""
    a = G.Audit(CEILING_MS)
    shapes = item["shapes"]
    is_dict = isinstance(response, dict)
    if not (is_dict or isinstance(response, list)):
        return a.junk(len(shapes))
    raw = response.get("events") if is_dict else response
    go_rts, hits, omis, comm, antic, extra, cr, invalid = [], 0, 0, 0, 0, 0, 0, 0
    for s_, r in zip(shapes, a.entries(raw, len(shapes))):
        status, rt = a.press(r, window=CYCLE_MS, slack=RT_SLACK_MS)
        if isinstance(r, dict):
            x = a.opt_int(r, "extra")
            extra += x or 0
        antic += status == G.ANTICIPATORY
        invalid += status == G.INVALID
        if s_ == "circle":
            if status == G.TIMELY:
                hits += 1
                go_rts.append(rt)
            elif status == G.ABSENT:
                omis += 1
        else:
            if status == G.ABSENT:
                cr += 1
            elif status != G.INVALID:
                comm += 1
    n_go = sum(1 for s_ in shapes if s_ == "circle")
    n_nogo = len(shapes) - n_go
    sd = None
    if len(go_rts) > 1:
        m = sum(go_rts) / len(go_rts)
        sd = round(math.sqrt(sum((x - m) ** 2 for x in go_rts) / (len(go_rts) - 1)), 1)
    hit = n_go > 0 and n_nogo > 0 and hits / n_go >= 0.8 and cr / n_nogo >= 0.5
    meta = response if is_dict else {}
    inter = a.opt_int(meta, "interruptions", required=is_dict)
    return a.finish(hit, (n_go - hits) + (n_nogo - cr), {
        "go_hits": hits, "go_omissions": omis, "go_omission_rate": G.rate(omis, n_go),
        "go_hit_rate": G.rate(hits, n_go),
        "nogo_commissions": comm, "nogo_commission_rate": G.rate(comm, n_nogo),
        "nogo_correct_rejections": cr, "invalid_entries": invalid,
        "go_rt_median": G.median(go_rts), "go_rt_mean": G.mean(go_rts), "go_rt_sd": sd, "go_rt_n": len(go_rts),
        "dprime": _dprime(hits, n_go, comm, n_nogo) if n_go and n_nogo else None,
        "anticipations": antic, "extra_presses": extra, "interruptions": inter})


def example_response(item, correct=True):
    ev = []
    for s in item["shapes"]:
        press = (s == "circle") if correct else (s == "triangle")
        ev.append({"rt": 420 if press else None, "extra": 0})
    return {"events": ev, "interruptions": 0}
