"""Multiple-object tracking (card 03): 8 identical circles; some are highlighted, then all
move for 6 s; afterwards the person selects exactly the k original targets.
One trial is a short block of 3 tracking rounds with 2, 3 and 4 targets (shuffled order).
Motion is simulated here (time-based, 100 Hz physics, stored as 20 Hz key frames the
browser interpolates by elapsed time), so speed does not depend on the screen refresh
rate and the motion shown is exactly the one stored. Objects bounce off the walls and off
each other; their IDs never change. Pairs (k, k+1) share the target-count order and speed;
only the paths and target IDs differ."""
import math
import statistics

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


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and x == x else None


def score(item, response):
    """response: [{"selected": [object ids], "rt": ms}] in round order (rt from motion end
    to "Done"). Per round: target proportion = correctly selected targets / k; exact = the
    selected set equals the target set; false selections = selected non-targets.
    hit = mean target proportion over the rounds >= 0.75 (guessing gives about 0.375)."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, rd in enumerate(item["rounds"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        raw = r.get("selected") if isinstance(r.get("selected"), list) else []
        sel = {s for s in raw if isinstance(s, int) and not isinstance(s, bool) and 0 <= s < item["n"]}
        tg = set(rd["targets"])
        rows.append({"k": rd["k"], "prop": len(sel & tg) / len(tg), "exact": sel == tg,
                     "false": len(sel - tg), "rt": _num(r.get("rt"))})
    mean_prop = sum(r["prop"] for r in rows) / len(rows) if rows else 0.0
    rts = [r["rt"] for r in rows if r["rt"] is not None and r["rt"] > 0]
    return {"hit": mean_prop >= 0.75, "errors": sum(not r["exact"] for r in rows),
            "metrics": {"target_proportion": round(mean_prop, 3),
                        "exact_rounds": sum(r["exact"] for r in rows), "rounds": len(rows),
                        "false_selections": sum(r["false"] for r in rows),
                        "proportion_by_k": {str(r["k"]): round(r["prop"], 3) for r in rows},
                        "exact_by_k": {str(r["k"]): r["exact"] for r in rows},
                        "median_selection_rt": round(statistics.median(rts), 1) if rts else None}}


def example_response(item, correct=True):
    out = []
    for rd in item["rounds"]:
        if correct:
            sel = list(rd["targets"])
        else:
            sel = [i for i in range(item["n"]) if i not in rd["targets"]][:rd["k"]]
        out.append({"selected": sel, "rt": 3000})
    return out
