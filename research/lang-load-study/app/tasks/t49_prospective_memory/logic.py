"""Prospective memory (card 49): an ongoing odd/even task with an intention to remember.
30 two-digit numbers appear one at a time; the person answers Odd (left) or Even (right).
Three of them (10%) appear inside a thick square frame: for those the person must press
the Special response (space bar / Special button) instead.

Pairs (k, k+1) share the structure: 30 displays, 3 cues, never in the first 5 displays
and at least 5 displays apart, non-cue displays half odd / half even. Cue positions and
numbers differ. Answers (parity) are recomputed here from the numbers."""

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


def _keys(response, n):
    resp = response if isinstance(response, list) else []
    out = []
    for i in range(n):
        r = resp[i] if i < len(resp) and isinstance(resp[i], dict) else {}
        key = r.get("key") if r.get("key") in ("odd", "even", "special") else None
        rt = r.get("rt") if isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) else None
        out.append((key, rt))
    return out


def score(item, response):
    """response: [{"key": "odd"|"even"|"special"|null, "rt": ms}] in display order.
    A cue counts as caught on time when "special" is pressed on the cue display, or late
    when it is pressed on the very next display instead (that next display is then left out
    of the primary-task scores). Primary accuracy = correct parity on the other non-cue
    displays (omissions are wrong). "special" on any other display is a false alarm.
    hit = every cue caught (on time or late) AND primary accuracy >= 0.7.
    errors = missed cues + wrong or missing primary answers (a false alarm is one of those)."""
    ds = item["displays"]
    rows = _keys(response, len(ds))
    on_time = late = 0
    late_slots, cue_rts = set(), []
    for i, d in enumerate(ds):
        if not d["cue"]:
            continue
        if rows[i][0] == "special":
            on_time += 1
            if rows[i][1]:
                cue_rts.append(rows[i][1])
        elif i + 1 < len(ds) and not ds[i + 1]["cue"] and rows[i + 1][0] == "special":
            late += 1
            late_slots.add(i + 1)
    n_cues = sum(1 for d in ds if d["cue"])
    prim = [(d, rows[i]) for i, d in enumerate(ds) if not d["cue"] and i not in late_slots]
    ok = [(key == ("odd" if d["number"] % 2 else "even")) for d, (key, _) in prim]
    acc = sum(ok) / len(prim) if prim else 0.0
    rts = [rt for (d, (key, rt)), good in zip(prim, ok) if good and rt]
    fa = sum(1 for _, (key, _) in prim if key == "special")
    missed = n_cues - on_time - late
    return {"hit": missed == 0 and acc >= 0.7, "errors": missed + (len(prim) - sum(ok)),
            "metrics": {"cues": n_cues, "cue_hits_on_time": on_time, "cue_hits_late": late,
                        "cue_misses": missed, "cue_success_rate": round((on_time + late) / n_cues, 3),
                        "cue_rt_mean": round(sum(cue_rts) / len(cue_rts), 1) if cue_rts else None,
                        "special_false_alarms": fa, "primary_accuracy": round(acc, 3),
                        "primary_rt_correct_mean": round(sum(rts) / len(rts), 1) if rts else None,
                        "primary_omissions": sum(1 for _, (key, _) in prim if key is None),
                        "primary_trials": len(prim)}}


def example_response(item, correct=True):
    out = []
    for d in item["displays"]:
        par = "odd" if d["number"] % 2 else "even"
        if d["cue"]:
            out.append({"key": "special" if correct else par, "rt": 900})
        else:
            out.append({"key": par, "rt": 650})
    return out
