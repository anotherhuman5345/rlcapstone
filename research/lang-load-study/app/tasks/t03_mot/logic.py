"""Multiple-object tracking (card 03): 8 identical circles; some are highlighted, then all
move for 6 s; afterwards the person selects exactly the k original targets.
One trial is a short block of 3 tracking rounds with 2, 3 and 4 targets (shuffled order).
Motion is simulated here (time-based, 100 Hz physics, stored as 20 Hz key frames the
browser interpolates by elapsed time), so speed does not depend on the screen refresh
rate and the motion shown is exactly the one stored. Objects bounce off the walls and off
each other; their IDs never change. Pairs (k, k+1) share the target-count order and speed;
only the paths and target IDs differ."""
import math

from app.tasks import _guard as G

TIMING = "untimed"   # view.js select() has no time limit; rt is descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)
MAX_SELECTED = 100   # selection entries read per round

W, H, R = 600, 400, 18
N_OBJ = 8
SPEED = 110.0          # px per second (configurable here)
HZ = 20                # stored key frames per second
MOTION_S = 6.0
PHYS_HZ = 100
TARGET_COUNTS = (2, 3, 4)


def _simulate(rng):
    pos = []
    while len(pos) < N_OBJ:
        p = (rng.uniform(R + 5, W - R - 5), rng.uniform(R + 5, H - R - 5))
        if all(math.dist(p, q) > 4 * R for q in pos):
            pos.append(p)
    pos = [list(p) for p in pos]
    vel = []
    for _ in range(N_OBJ):
        a = rng.uniform(0, 2 * math.pi)
        vel.append([SPEED * math.cos(a), SPEED * math.sin(a)])
    dt = 1.0 / PHYS_HZ
    step_every = PHYS_HZ // HZ
    frames = []
    steps = int(MOTION_S * PHYS_HZ)
    for s in range(steps + 1):
        if s % step_every == 0:
            frames.append([round(c) for p in pos for c in p])
        if s == steps:
            break
        for i in range(N_OBJ):
            if rng.random() < 0.02:            # occasional gentle turn: paths stay unpredictable
                a = math.atan2(vel[i][1], vel[i][0]) + rng.uniform(-0.6, 0.6)
                vel[i] = [SPEED * math.cos(a), SPEED * math.sin(a)]
            pos[i][0] += vel[i][0] * dt
            pos[i][1] += vel[i][1] * dt
            if pos[i][0] < R: pos[i][0], vel[i][0] = R, abs(vel[i][0])
            if pos[i][0] > W - R: pos[i][0], vel[i][0] = W - R, -abs(vel[i][0])
            if pos[i][1] < R: pos[i][1], vel[i][1] = R, abs(vel[i][1])
            if pos[i][1] > H - R: pos[i][1], vel[i][1] = H - R, -abs(vel[i][1])
        for i in range(N_OBJ):                 # elastic bounce between equal circles
            for j in range(i + 1, N_OBJ):
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy)
                if 0 < d < 2 * R + 4:
                    nx, ny = dx / d, dy / d
                    vi = vel[i][0] * nx + vel[i][1] * ny
                    vj = vel[j][0] * nx + vel[j][1] * ny
                    if vi - vj > 0:            # approaching
                        vel[i][0] += (vj - vi) * nx; vel[i][1] += (vj - vi) * ny
                        vel[j][0] += (vi - vj) * nx; vel[j][1] += (vi - vj) * ny
                        for v in (vel[i], vel[j]):
                            m = math.hypot(*v) or 1.0
                            v[0], v[1] = v[0] / m * SPEED, v[1] / m * SPEED
    return frames


def generate(rng, n, save_image):
    items, order = [], None
    for k in range(n):
        if k % 2 == 0:
            order = list(TARGET_COUNTS)
            rng.shuffle(order)
        rounds = []
        for kk in order:
            rounds.append({"k": kk, "targets": sorted(rng.sample(range(N_OBJ), kk)),
                           "frames": _simulate(rng)})
        items.append({"w": W, "h": H, "r": R, "n": N_OBJ, "hz": HZ, "speed": SPEED,
                      "cue_ms": 2000, "motion_ms": int(MOTION_S * 1000), "rounds": rounds})
    return items


def _selection(raw, n, k, a):
    """The selected object ids as a set, or None when the round's selection is invalid.
    The view only allows Done with exactly k distinct ids 0..n-1. Ids that are not
    integers in range are flagged and dropped; repeated ids are flagged and counted once;
    fewer than k ids are flagged (scored as given); MORE than k ids are flagged and the
    round is invalid (selecting extra objects must never earn target credit)."""
    if raw is G.MISSING:
        a.malformed("missing_selected")
        return None
    if not isinstance(raw, list):
        a.malformed("invalid_selected")
        return None
    sel = set()
    for s in raw[:MAX_SELECTED]:
        if not G.member(s, range(n)):
            a.malformed("invalid_selected_id")
        elif s in sel:
            a.malformed("duplicate_selected")
        else:
            sel.add(s)
    if len(raw) > MAX_SELECTED:
        a.flag("too_many_selected_entries")
    if len(sel) > k:
        a.malformed("too_many_selected")
        return None
    if len(sel) < k:
        a.flag("too_few_selected")
    return sel


@G.safe
def score(item, response):
    """response: [{"selected": [object ids], "rt": ms}] in round order, one entry per round
    (missing entries are invalid rounds, extra ones ignored; both flagged); rt from motion
    end to "Done". Per round: target proportion = correctly selected targets / k; exact =
    the selected set equals the target set; false selections = selected non-targets.
    The selection must be at most k distinct ids 0..n-1 (the view requires exactly k):
    a round with more than k ids is invalid and scores 0 (flagged); bad / repeated ids
    are flagged and dropped / counted once.
    hit = mean target proportion over the rounds >= 0.75 (guessing gives about 0.375).
    Selection is unspeeded: rt is descriptive, checked (finite, >= 100 ms, below the
    trial timeout) and null when bad (flagged); correctness stands."""
    a = G.Audit(CEILING_MS)
    rounds = item["rounds"]
    if not isinstance(response, list):
        return a.junk(len(rounds))
    rows = []
    for rd, r in zip(rounds, a.entries(response, len(rounds))):
        ev = a.obj(r)
        tg = set(rd["targets"])
        sel, rt = None, None
        if ev is not None:
            sel = _selection(ev.get("selected", G.MISSING), item["n"], rd["k"], a)
            rt = a.duration(ev, "rt")
        if sel is None:
            rows.append({"k": rd["k"], "prop": 0.0, "exact": False, "false": 0, "rt": rt, "valid": False})
        else:
            rows.append({"k": rd["k"], "prop": len(sel & tg) / len(tg), "exact": sel == tg,
                         "false": len(sel - tg), "rt": rt, "valid": True})
    mean_prop = sum(r["prop"] for r in rows) / len(rows) if rows else 0.0
    rts = [r["rt"] for r in rows if r["rt"] is not None]
    return a.finish(mean_prop >= 0.75, sum(not r["exact"] for r in rows), {
        "target_proportion": round(mean_prop, 3),
        "exact_rounds": sum(r["exact"] for r in rows), "rounds": len(rows),
        "invalid_rounds": sum(not r["valid"] for r in rows),
        "false_selections": sum(r["false"] for r in rows),
        "proportion_by_k": {str(r["k"]): round(r["prop"], 3) for r in rows},
        "exact_by_k": {str(r["k"]): r["exact"] for r in rows},
        "median_selection_rt": G.median(rts)})


def example_response(item, correct=True):
    out = []
    for rd in item["rounds"]:
        if correct:
            sel = list(rd["targets"])
        else:
            sel = [i for i in range(item["n"]) if i not in rd["targets"]][:rd["k"]]
        out.append({"selected": sel, "rt": 3000})
    return out
