"""Tracking plus arithmetic (card 62), adapted to one 46 s trial.

A dot glides smoothly over a 1 : 0.6 field along a sum-of-sines path (time-based, so
its speed does not depend on the frame rate). Keep the pointer (mouse, finger, or the
arrow keys / on-screen arrows) on it. Meanwhile 6 written sums (two-digit + one-digit)
appear every 7 s; pick the answer from 3 options (click, or keys 1-3) within 6 s.

Coordinates are in field-width units: x in [0, 1], y in [0, 0.6]. The browser sends the
cursor position every 100 ms; the server recomputes the target position itself and
measures the distance. Pairs (k, k+1) share amplitudes, frequencies and the carry
pattern of the sums; phases and numbers differ.
"""
import math

from app.tasks import _guard as G

TIMING = "window"
DURATION_MS = 46000
SAMPLE_MS = 100
N_SUMS = 6
SUM_FIRST_MS, SUM_EVERY_MS, SUM_WINDOW_MS = 4000, 7000, 6000
HEIGHT = 0.6
MAX_MEAN_DIST = 0.08   # mean distance (field widths) still counted as tracking
WINDOW_MS = SUM_WINDOW_MS   # view.js: a sum is cleared at it.sums[i].t + it.window_ms (answer stays null)
RT_SLACK_MS = 50       # frame-timing tolerance at the end of the sum window
POS_TOL = 0.001        # the browser clamps the cursor to [0, 1] x [0, height] (rounded to 4 dp)
MAX_SAMPLES = 2000     # 46 s at 100 ms = 461 samples
CEILING_MS = G.trial_ceiling(__file__)


def target_pos(path, t_ms):
    t = t_ms / 1000.0
    x = 0.5 + sum(a * math.sin(2 * math.pi * f * t + p) for a, f, p in path["x"])
    y = HEIGHT / 2 + sum(a * math.sin(2 * math.pi * f * t + p) for a, f, p in path["y"])
    return x, y


def _sum(rng, carry):
    while True:
        a, b = rng.randint(13, 48), rng.randint(4, 9)
        if ((a % 10) + b >= 10) == carry:
            return a, b


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        amps_x = [round(rng.uniform(0.16, 0.21), 3), round(rng.uniform(0.06, 0.09), 3)]
        amps_y = [round(rng.uniform(0.10, 0.13), 3), round(rng.uniform(0.04, 0.06), 3)]
        freqs_x = [round(rng.uniform(0.08, 0.11), 3), round(rng.uniform(0.17, 0.22), 3)]
        freqs_y = [round(rng.uniform(0.07, 0.10), 3), round(rng.uniform(0.15, 0.20), 3)]
        carries = [True, True, True, False, False, False]
        rng.shuffle(carries)
        for _ in range(2):
            ph = [round(rng.uniform(0, 2 * math.pi), 3) for _ in range(4)]
            path = {"x": [[amps_x[i], freqs_x[i], ph[i]] for i in range(2)],
                    "y": [[amps_y[i], freqs_y[i], ph[2 + i]] for i in range(2)]}
            sums = []
            for i, c in enumerate(carries):
                a, b = _sum(rng, c)
                s = a + b
                opts = [s, s + rng.choice([-1, 1]), s + rng.choice([-10, 10])]
                rng.shuffle(opts)
                sums.append({"a": a, "b": b, "t": SUM_FIRST_MS + i * SUM_EVERY_MS, "options": opts})
            items.append({"duration_ms": DURATION_MS, "sample_ms": SAMPLE_MS, "height": HEIGHT,
                          "window_ms": SUM_WINDOW_MS, "path": path, "sums": sums})
    return items[:n]


def _samples(item, raw, a):
    """Valid samples as {t: (x, y)}. A sample must be a list [t, x, y] of finite numbers with
    0 <= t <= duration and the position inside the field; malformed samples are flagged and
    dropped. Times must increase: repeated times are flagged (only the first one is used) and
    times that go backwards are flagged."""
    seq = a.stream(raw, "samples", cap=MAX_SAMPLES)
    out, order, dup = {}, [], 0
    for s in seq:
        if not isinstance(s, list) or len(s) != 3:
            a.malformed("invalid_sample")
            order.append(None)
            continue
        st, t = a.time(s[0], field="sample_t", window=item["duration_ms"], floor=0, required=True)
        if st != G.TIMELY:
            order.append(t if st == G.LATE else None)
            if st == G.LATE:
                a.malformed("sample_after_end")
            continue
        order.append(t)
        x, y = s[1], s[2]
        if not (G.is_num(x) and G.is_num(y) and -POS_TOL <= x <= 1 + POS_TOL
                and -POS_TOL <= y <= item["height"] + POS_TOL):
            a.malformed("invalid_sample_position")
            continue
        if t in out:
            dup += 1
            continue
        out[t] = (float(x), float(y))
    if dup:
        a.malformed("duplicate_sample_t")
    a.monotonic(order, "sample_t")
    return out


@G.safe
def score(item, response):
    """response: {"samples": [[t_ms, x, y], ...] cursor positions every ~100 ms,
    "answers": [{"value": chosen number or null, "rt": ms from the sum's onset or null},
    one per sum], "frame_gaps": int, "input": "pointer"/"keys"/...}.
    Tracking error = distance from the cursor to the server-computed target, in field widths.
    A sample counts only if it is well formed (finite t, x, y; 0 <= t <= duration; position
    inside the field) and its time is new (repeated or backwards times are flagged); tracking
    is valid if distinct valid samples cover >= 50 % of the trial.
    Each sum's answer is classified (app/tasks/_guard.py): absent, invalid (value not one of
    the 3 options, value without rt or rt without value, bad rt), anticipatory (< 100 ms),
    late (beyond the 6 s answer window, view.js window_ms) or timely; only a TIMELY answer
    equal to a + b (recomputed here) is correct.
    hit = at least 4 of 6 sums correct AND valid tracking with mean distance <= 0.08."""
    a = G.Audit(CEILING_MS)
    sums = item["sums"]
    if not isinstance(response, dict):
        return a.junk(len(sums))
    good = _samples(item, response.get("samples", G.MISSING), a)
    dists = []
    for t, (x, y) in good.items():
        tx, ty = target_pos(item["path"], t)
        dists.append(math.hypot(x - tx, y - ty))
    coverage = len(dists) / (item["duration_ms"] / item["sample_ms"])
    mean_d = sum(dists) / len(dists) if dists else None
    rmse = math.sqrt(sum(d * d for d in dists) / len(dists)) if dists else None
    tracking_ok = coverage >= 0.5 and mean_d is not None and mean_d <= MAX_MEAN_DIST

    raw = response.get("answers", G.MISSING)
    if raw is G.MISSING:
        a.malformed("missing_answers")
    correct, rts, omissions, events = 0, [], 0, []
    for k, (sm, r) in enumerate(zip(sums, a.entries(raw if raw is not G.MISSING else [], len(sums), "answers"))):
        status, v, rt = a.keyed(r, sm["options"], key="value", window=item.get("window_ms", WINDOW_MS),
                                slack=RT_SLACK_MS)
        omissions += status == G.ABSENT
        ok = status == G.TIMELY and v == sm["a"] + sm["b"]
        if ok:
            correct += 1
            rts.append(rt)
        events.append({"i": k, "status": status, "correct": ok, "rt": rt if status == G.TIMELY else None})
    return a.finish(correct >= 4 and tracking_ok, len(sums) - correct, {
        "arith_correct": correct, "arith_accuracy": round(correct / len(sums), 3),
        "arith_omissions": omissions,
        "arith_rt_mean": G.mean(rts), "arith_rt_median": G.median(rts),
        "track_mean_dist": round(mean_d, 4) if mean_d is not None else None,
        "track_rmse": round(rmse, 4) if rmse is not None else None,
        "track_coverage": round(min(coverage, 1.0), 3), "track_samples": len(dists),
        "frame_gaps": a.opt_int(response, "frame_gaps", hi=10 ** 6),
        "input": a.opt_str(response, "input"), "events": events})


def example_response(item, correct=True):
    samples = []
    for t in range(0, item["duration_ms"] + 1, item["sample_ms"]):
        x, y = target_pos(item["path"], t) if correct else (0.02, 0.02)
        samples.append([t, round(x, 4), round(y, 4)])
    answers = [{"value": (s["a"] + s["b"]) if correct else (s["a"] + s["b"] + 1), "rt": 2500} for s in item["sums"]]
    return {"samples": samples, "answers": answers, "frame_gaps": 0, "input": "pointer"}
