"""Dashboard monitoring (card 64), adapted to one 60 s trial.

Four bar gauges (0-100) drift gently around 50. A red line marks 80. Scripted events:
  alarm - the bar rises above the line and STAYS there for 4 s   (respond: click/press that gauge)
  spike - the bar jumps above the line for only 0.6 s           (ignore)
  low   - the bar drops to about 12 for 3 s                     (ignore)
Each trial has 4 alarms, 2 spikes and 1 low event, about 7.5 s apart. The bars never
change colour and nothing flashes, so only the bar position carries the signal.

The browser draws value(g, t) = base + 7 sin(2 pi f1 t + p1) + 3 sin(2 pi f2 t + p2),
blended toward the event level by a ramped envelope. The server scores only against the
scripted event list. Gauge names come from text "gauges" by index. Pairs (k, k+1) have
the same event kinds and gaps (times jittered by up to +-0.5 s), on different gauges.
"""
from statistics import NormalDist

DURATION_MS = 60000
N_GAUGE_NAMES = 8      # length of text "gauges"
N_GAUGES = 4
KINDS = ["alarm"] * 4 + ["spike"] * 2 + ["low"]
LEVEL = {"alarm": 88, "spike": 86, "low": 12}
DUR = {"alarm": 4000, "spike": 600, "low": 3000}
RAMP = {"alarm": 300, "spike": 200, "low": 300}
WINDOW_MS = 5000       # an alarm counts as detected if its gauge is chosen within this time
LURE_WINDOW_MS = 3000  # a press on a lure gauge in this time is a lure false alarm


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        kinds = KINDS[:]
        rng.shuffle(kinds)
        jit = [rng.randint(0, 10) * 100 for _ in kinds]
        for _ in range(2):
            names = rng.sample(range(N_GAUGE_NAMES), N_GAUGES)
            events, prev_g = [], None
            for i, kind in enumerate(kinds):
                g = rng.choice([x for x in range(N_GAUGES) if x != prev_g])
                prev_g = g
                t = 4000 + 7500 * i + jit[i] + rng.randint(-5, 5) * 100
                events.append({"t": t, "g": g, "kind": kind, "dur": DUR[kind], "ramp": RAMP[kind],
                               "level": LEVEL[kind]})
            wobble = [[rng.randint(45, 52), round(rng.uniform(0.08, 0.14), 3), round(rng.uniform(0, 6.28), 2),
                       round(rng.uniform(0.3, 0.5), 3), round(rng.uniform(0, 6.28), 2)] for _ in range(N_GAUGES)]
            items.append({"duration_ms": DURATION_MS, "red_line": 80, "names": names,
                          "wobble": wobble, "events": events})
    return items[:n]


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def score(item, response):
    """response: {"presses": [{"g": gauge index, "t": ms from start}, ...]}.
    Each alarm is detected by the first press on its gauge within 5 s of onset
    (latency = press time - onset); further presses on that gauge inside the same window
    are repeats, not false alarms. Any other press is a false alarm; it is a lure false
    alarm if it is on a spike/low gauge within 3 s of that lure's onset. Lures with no
    press are correct rejections. d' uses (hits+0.5)/(alarms+1) and (lure FAs+0.5)/(lures+1).
    hit = at least 3 of 4 alarms detected AND at most 1 false alarm in total."""
    miss = {"hit": False, "errors": 4, "metrics": {}}
    if not isinstance(response, dict) or not isinstance(response.get("presses"), list):
        return miss
    presses = []
    for p in response["presses"]:
        if isinstance(p, dict) and isinstance(p.get("g"), int) and not isinstance(p.get("g"), bool) \
                and _num(p.get("t")) is not None:
            presses.append((p["g"], _num(p["t"])))
    presses.sort(key=lambda x: x[1])
    used = set()
    alarms = [e for e in item["events"] if e["kind"] == "alarm"]
    lures = [e for e in item["events"] if e["kind"] != "alarm"]
    lat = []
    for e in alarms:
        first = None
        for k, (g, t) in enumerate(presses):
            if g == e["g"] and e["t"] <= t <= e["t"] + WINDOW_MS:
                used.add(k)
                if first is None:
                    first = t - e["t"]
        lat.append(first)
    lure_hit, lure_fa, other_fa = set(), 0, 0
    for k, (g, t) in enumerate(presses):
        if k in used:
            continue
        j = next((j for j, e in enumerate(lures) if g == e["g"] and e["t"] <= t <= e["t"] + LURE_WINDOW_MS), None)
        if j is None:
            other_fa += 1
        else:
            lure_hit.add(j)
            lure_fa += 1
    hits = sum(x is not None for x in lat)
    fas = lure_fa + other_fa
    z = NormalDist().inv_cdf
    hr = (hits + 0.5) / (len(alarms) + 1)
    far = (len(lure_hit) + 0.5) / (len(lures) + 1)
    det = [x for x in lat if x is not None]
    half = item["duration_ms"] / 2
    early = [x for x, e in zip(lat, alarms) if x is not None and e["t"] < half]
    late = [x for x, e in zip(lat, alarms) if x is not None and e["t"] >= half]
    mean = lambda v: round(sum(v) / len(v), 1) if v else None  # noqa: E731
    return {"hit": hits >= 3 and fas <= 1,
            "errors": (len(alarms) - hits) + fas,
            "metrics": {"hits": hits, "misses": len(alarms) - hits,
                        "lure_false_alarms": len(lure_hit), "correct_rejections": len(lures) - len(lure_hit),
                        "other_false_alarms": other_fa, "false_alarm_presses": fas,
                        "d_prime": round(z(hr) - z(far), 3),
                        "latency_mean": mean(det), "latency_first_half": mean(early),
                        "latency_second_half": mean(late), "latencies": lat}}


def example_response(item, correct=True):
    presses = []
    for e in item["events"]:
        if correct and e["kind"] == "alarm":
            presses.append({"g": e["g"], "t": e["t"] + 900})
        if not correct and e["kind"] != "alarm":
            presses.append({"g": e["g"], "t": e["t"] + 400})
    return {"presses": presses}
