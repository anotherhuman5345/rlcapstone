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

DURATION_MS = 46000
SAMPLE_MS = 100
N_SUMS = 6
SUM_FIRST_MS, SUM_EVERY_MS, SUM_WINDOW_MS = 4000, 7000, 6000
HEIGHT = 0.6
MAX_MEAN_DIST = 0.08   # mean distance (field widths) still counted as tracking


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


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def score(item, response):
    """response: {"samples": [[t_ms, x, y], ...] cursor positions every ~100 ms,
    "answers": [{"value": chosen number or null, "rt": ms or null}, one per sum],
    "frame_gaps": int, "input": "pointer"/"keys"/...}.
    Tracking error = distance from the cursor to the server-computed target, in field widths.
    Samples count only if 0 <= t <= duration; tracking is valid if they cover >= 50 % of
    the trial.
    hit = at least 4 of 6 sums correct AND valid tracking with mean distance <= 0.08."""
    miss = {"hit": False, "errors": N_SUMS, "metrics": {}}
    if not isinstance(response, dict):
        return miss
    raw = response.get("samples") if isinstance(response.get("samples"), list) else []
    dists = []
    for s in raw:
        if not isinstance(s, list) or len(s) != 3:
            continue
        t, x, y = (_num(v) for v in s)
        if t is None or x is None or y is None or not 0 <= t <= item["duration_ms"]:
            continue
        tx, ty = target_pos(item["path"], t)
        dists.append(math.hypot(x - tx, y - ty))
    coverage = len(dists) / (item["duration_ms"] / item["sample_ms"])
    mean_d = sum(dists) / len(dists) if dists else None
    rmse = math.sqrt(sum(d * d for d in dists) / len(dists)) if dists else None
    tracking_ok = coverage >= 0.5 and mean_d is not None and mean_d <= MAX_MEAN_DIST

    answers = response.get("answers") if isinstance(response.get("answers"), list) else []
    correct, rts, omissions = 0, [], 0
    for k, sm in enumerate(item["sums"]):
        a = answers[k] if k < len(answers) and isinstance(answers[k], dict) else {}
        v = _num(a.get("value"))
        if v is None:
            omissions += 1
        elif v == sm["a"] + sm["b"]:
            correct += 1
            rt = _num(a.get("rt"))
            if rt is not None:
                rts.append(rt)
    return {"hit": correct >= 4 and tracking_ok,
            "errors": len(item["sums"]) - correct,
            "metrics": {"arith_correct": correct, "arith_accuracy": round(correct / len(item["sums"]), 3),
                        "arith_omissions": omissions,
                        "arith_rt_mean": round(sum(rts) / len(rts), 1) if rts else None,
                        "track_mean_dist": round(mean_d, 4) if mean_d is not None else None,
                        "track_rmse": round(rmse, 4) if rmse is not None else None,
                        "track_coverage": round(min(coverage, 1.0), 3),
                        "frame_gaps": int(_num(response.get("frame_gaps")) or 0),
                        "input": response.get("input") if isinstance(response.get("input"), str) else None}}


def example_response(item, correct=True):
    samples = []
    for t in range(0, item["duration_ms"] + 1, item["sample_ms"]):
        x, y = target_pos(item["path"], t) if correct else (0.02, 0.02)
        samples.append([t, round(x, 4), round(y, 4)])
    answers = [{"value": (s["a"] + s["b"]) if correct else (s["a"] + s["b"] + 1), "rt": 2500} for s in item["sums"]]
    return {"samples": samples, "answers": answers, "frame_gaps": 0, "input": "pointer"}
