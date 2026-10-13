"""Prospective memory (card 49): an ongoing odd/even task with an intention to remember.
30 two-digit numbers appear one at a time; the person answers Odd (left) or Even (right).
Three of them (10%) appear inside a thick square frame: for those the person must press
the Special response (space bar / Special button) instead.

Pairs (k, k+1) share the structure: 30 displays, 3 cues, never in the first 5 displays
and at least 5 displays apart, non-cue displays half odd / half even. Cue positions and
numbers differ. Answers (parity) are recomputed here from the numbers."""

from app.tasks import _guard as G

TIMING = "window"
WINDOW_MS = 1500        # view.js: out.push(await answer(1500)) - each number waits at most 1500 ms
CEILING_MS = G.trial_ceiling(__file__)
KEYS = ("odd", "even", "special")
N, N_CUES, FIRST, GAP = 30, 3, 5, 5


def _cue_positions(rng):
    while True:
        pos = sorted(rng.sample(range(FIRST, N), N_CUES))
        if all(b - a >= GAP for a, b in zip(pos, pos[1:])):
            return pos


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        cues = set(_cue_positions(rng))
        n_plain = N - N_CUES
        parities = [1] * (n_plain // 2) + [0] * (n_plain - n_plain // 2)
        rng.shuffle(parities)
        displays = []
        for i in range(N):
            if i in cues:
                displays.append({"number": rng.randint(11, 99), "cue": True})
            else:
                par = parities.pop()
                displays.append({"number": rng.choice([x for x in range(11, 100) if x % 2 == par]), "cue": False})
        items.append({"displays": displays})
    return items


@G.safe
def score(item, response):
    """response: [{"key": "odd"|"even"|"special"|null, "rt": ms}] in display order.
    Each display is classified (app/tasks/_guard.py) as absent, invalid, anticipatory
    (< 100 ms), late (> the 1500 ms response window) or timely; a key counts as pressed on
    a display only when its rt is TIMELY in that display's own window.
    A cue counts as caught on time when "special" is pressed (timely) on the cue display,
    or late when it is pressed (timely, in the next display's own window) on the very next
    display instead (that next display is then left out of the primary-task scores).
    Primary accuracy = a timely correct parity on the other non-cue displays (omissions,
    anticipatory, late and malformed answers are wrong). "special" on any other display is
    a false alarm.
    hit = every cue caught (on time or late) AND primary accuracy >= 0.7.
    errors = missed cues + wrong or missing primary answers (a false alarm is one of those)."""
    a = G.Audit(CEILING_MS)
    ds = item["displays"]
    if not isinstance(response, list):
        return a.junk(len(ds))
    rows = []
    for d, r in zip(ds, a.entries(response, len(ds))):
        status, key, rt = a.keyed(r, KEYS, window=WINDOW_MS)
        rows.append({"status": status, "key": key, "made": key if status == G.TIMELY else None, "rt": rt})
    on_time = late = 0
    late_slots, cue_rts, cue_status = set(), [], []
    for i, d in enumerate(ds):
        if not d["cue"]:
            continue
        if rows[i]["made"] == "special":
            on_time += 1
            cue_rts.append(rows[i]["rt"])
            cue_status.append("on_time")
        elif i + 1 < len(ds) and not ds[i + 1]["cue"] and rows[i + 1]["made"] == "special":
            late += 1
            late_slots.add(i + 1)
            cue_status.append("late")
        else:
            cue_status.append("missed")
    n_cues = sum(1 for d in ds if d["cue"])
    prim = [(i, d, rows[i]) for i, d in enumerate(ds) if not d["cue"] and i not in late_slots]
    ok = [r["made"] == ("odd" if d["number"] % 2 else "even") for _, d, r in prim]
    acc = sum(ok) / len(prim) if prim else 0.0
    rts = [r["rt"] for (_, _, r), good in zip(prim, ok) if good]
    fa = sum(1 for _, _, r in prim if r["key"] == "special")
    missed = n_cues - on_time - late
    good_i = {i for (i, _, _), g in zip(prim, ok) if g}
    return a.finish(n_cues > 0 and missed == 0 and acc >= 0.7, missed + (len(prim) - sum(ok)), {
        "cues": n_cues, "cue_hits_on_time": on_time, "cue_hits_late": late,
        "cue_misses": missed, "cue_success_rate": G.rate(on_time + late, n_cues),
        "cue_rt_mean": G.mean(cue_rts),
        "special_false_alarms": fa, "primary_accuracy": round(acc, 3),
        "primary_rt_correct_mean": G.mean(rts),
        "primary_omissions": sum(1 for _, _, r in prim if r["status"] == G.ABSENT),
        "primary_trials": len(prim),
        "anticipations": sum(1 for r in rows if r["status"] == G.ANTICIPATORY),
        "cue_status": cue_status,
        "events": [{"i": i, "cue": d["cue"], "status": rows[i]["status"],
                    "correct": (rows[i]["made"] == "special") if d["cue"] or i in late_slots else i in good_i,
                    "rt": rows[i]["rt"] if rows[i]["made"] is not None else None}
                   for i, d in enumerate(ds)]})


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        par = "odd" if d["number"] % 2 else "even"
        if d["cue"]:
            out.append({"key": "special" if correct else par, "rt": 900})
        else:
            out.append({"key": par, "rt": 650})
    return out
