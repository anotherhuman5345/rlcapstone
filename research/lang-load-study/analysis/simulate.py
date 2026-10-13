"""Make a FAKE dataset with the same columns as the real export, so the
analysis pipeline can be tested before any real data exist.

Every row is marked is_test=True and the file is named SIMULATED. Never
report these numbers as findings. The assumed effects below exist only to
check that the analysis can find an effect when one is there (and does not
find one when it is absent).

Scenarios
  default        early practice speed-up for 4 minutes, then slowing from
                 --decay-start at --decay-slope log-ms/min (a fatigue effect).
  learning_only  performance improves and then plateaus; there is NO fatigue.
                 The analysis must not report this as fatigue onset.

Options for exercising other parts of the pipeline:
  --p-missing-final  share of people who pressed "I'm exhausted" and never
                     reached the final questionnaire (completed/attention_ok blank).
  --library          add one Stroop library block per round with a `metrics`
                     JSON column, as in the real export.
"""
import argparse
import json
import uuid

import numpy as np
import pandas as pd

GROUP_SETUP = {  # group: (n, age, education years, years reading images, P(saw gorilla | L1), P(knew study))
    "high_school": (80, 16, 11, 0, 0.55, 0.05),
    "adult": (40, 45, 14, 0, 0.50, 0.10),
    "phd_student": (30, 29, 20, 0, 0.50, 0.15),
    "radiologist": (30, 42, 22, 12, 0.35, 0.40),
}
ROUNDS, PER_TASK_PER_ROUND = 24, 4
SESSION_LIMIT_MIN = 60


def learning_curve(minutes, scenario):
    if scenario == "learning_only":
        # Improves quickly at first, then plateaus (about -0.25 log-ms in total).
        return -0.25 * (1 - np.exp(-minutes / 6.0))
    return -0.03 * min(minutes, 4)  # assumed practice speed-up early on


def simulate(seed=1, l2_cost=0.12, decay_start=8.0, decay_slope=0.04, scenario="default",
             n_scale=1.0, p_missing_final=0.0, library=False, rounds=ROUNDS):
    """Return a DataFrame shaped like the real trials export."""
    if scenario not in ("default", "learning_only"):
        raise ValueError(f"unknown scenario {scenario!r}")
    if scenario == "learning_only":
        decay_slope = 0.0
    rng = np.random.default_rng(seed)
    extra_rng = np.random.default_rng(seed + 10_000)  # separate stream: default output is unchanged

    rows = []
    for group, (n, age, edu, yrs, p_saw, p_knew) in GROUP_SETUP.items():
        for k in range(max(1, int(round(n * n_scale)))):
            pid = str(uuid.uuid4())
            person = rng.normal(0, 0.15)
            person_effort = rng.normal(0, 0.8)
            l1 = rng.choice(["en", "tr"])
            l2 = "tr" if l1 == "en" else "en"
            knew = bool(rng.random() < p_knew)
            surprise_cond = "L1" if (k // 2) % 2 == 0 else "L2"
            saw = bool(rng.random() < (0.9 if knew else p_saw * (0.75 if surprise_cond == "L2" else 1)))
            common = {
                "participant_id": pid, "is_test": True, "group": group,
                "age": age + int(rng.integers(0, 4)), "education_years": edu,
                "years_reading_images": yrs, "native_lang": l1, "l2_age_acquired": 6,
                "l1": l1, "l2": l2, "l1_reading": 7, "l2_reading": 6, "eligible": True,
                "counterbalance": k % 4, "attention_ok": True, "completed": True, "time_capped": False,
                "quit_early": False, "quit_elapsed_s": None, "quit_trial": None,
                "noticed_unusual": saw or bool(rng.random() < 0.1), "saw_gorilla": saw,
                "knew_gorilla_study": knew,
            }
            clock = 0.0
            rt0 = float(np.exp(8.3 + person + rng.normal(0, 0.3)))
            clock += rt0 / 1000 + 4
            first_row = len(rows)
            rows.append({**common, "trial_index": 0, "round": None, "elapsed_s": round(clock, 1),
                         "task": "surprise", "image_id": "surprise",
                         "clue_lang": l1 if surprise_cond == "L1" else l2, "condition": surprise_cond,
                         "practice": False, "rt_ms": round(rt0), "hit": True, "timed_out": False,
                         "false_clicks": 0, "effort": 3, "reloads": 0})
            clock += 60  # surprise questions + instructions + 2 practice trials
            i = 3
            # Assumed: most people press "I'm exhausted" somewhere between minute 12 and 55;
            # the rest reach the 60-minute safety maximum.
            quit_at = rng.uniform(12, 55) if rng.random() < 0.85 else None
            for r in range(1, rounds + 1):
                if common["time_capped"] or common["quit_early"]:
                    break
                trials = [(task, j) for task in ("search", "scan", "dice") for j in range(PER_TASK_PER_ROUND)]
                rng.shuffle(trials)
                for task, j in trials:
                    cond = "L1" if (j + k) % 2 == 0 else "L2"
                    base = {"search": 8.4, "scan": 8.1, "dice": 8.7}[task]
                    if group == "radiologist" and task == "scan":
                        base -= 0.15  # assumed expertise benefit on scans
                    cost = l2_cost * (0.6 if group == "radiologist" else 1.0) if cond == "L2" else 0
                    minutes = clock / 60
                    learning = learning_curve(minutes, scenario)
                    decay = decay_slope * max(0.0, minutes - decay_start)
                    log_rt = base + person + cost + learning + decay + rng.normal(0, 0.35)
                    rt = float(np.exp(log_rt))
                    if quit_at and clock / 60 > quit_at:
                        common.update(quit_early=True, quit_elapsed_s=round(clock, 1), quit_trial=i)
                        break
                    if clock > SESSION_LIMIT_MIN * 60 - 60:  # safety maximum (counted from the start page)
                        common["time_capped"] = True
                        break
                    timed_out = rt > 30000
                    clock += min(rt, 30000) / 1000 + 3.5  # plus effort rating and page change
                    rows.append({
                        **common, "trial_index": i, "round": r, "elapsed_s": round(clock, 1),
                        "task": task, "image_id": f"{task}_{(r - 1) * 4 + j:02d}",
                        "clue_lang": l1 if cond == "L1" else l2, "condition": cond, "practice": False,
                        "rt_ms": None if timed_out else round(rt), "hit": not timed_out,
                        "timed_out": timed_out, "false_clicks": int(rng.poisson(0.5)),
                        "effort": int(np.clip(round(4 + person_effort + (1 if cond == "L2" else 0)
                                                    + rng.normal(0, 1.3)), 1, 9)),
                        "reloads": 0,
                    })
                    i += 1
                if library and not (common["time_capped"] or common["quit_early"]):
                    clock += 40
                    rows.append(_stroop_block(extra_rng, common, i, r, k, clock, l1, l2, person))
                    i += 1
            if p_missing_final > 0 and common["quit_early"] and extra_rng.random() < p_missing_final:
                common.update(completed=False, attention_ok=None)
            for row in rows[first_row:]:  # person-level flags apply to all of this person's rows
                row.update(time_capped=common["time_capped"], quit_early=common["quit_early"],
                           quit_elapsed_s=common["quit_elapsed_s"], quit_trial=common["quit_trial"],
                           completed=common["completed"], attention_ok=common["attention_ok"])
    return pd.DataFrame(rows)


def _stroop_block(rng, common, i, r, k, clock, l1, l2, person):
    """One library Stroop block. `hit` is the task's pass threshold (accuracy >= .75), not
    accuracy, and rt_ms is the block duration, not an event RT."""
    cond = "L1" if (r + k) % 2 == 0 else "L2"
    acc = float(np.clip(rng.normal(0.93, 0.05), 0, 1))
    rt_c = float(np.exp(6.4 + person + rng.normal(0, 0.1)))
    rt_i = rt_c + float(rng.normal(80 if cond == "L1" else 110, 20))
    metrics = {"response": [], "accuracy": round(acc, 3), "median_rt_congruent": round(rt_c, 1),
               "median_rt_incongruent": round(rt_i, 1), "stroop_cost_ms": round(rt_i - rt_c, 1),
               "omissions": int(rng.poisson(0.3))}
    return {**common, "trial_index": i, "round": r, "elapsed_s": round(clock, 1), "task": "stroop",
            "image_id": f"stroop_{r:02d}", "clue_lang": l1 if cond == "L1" else l2, "condition": cond,
            "practice": False, "rt_ms": 40000.0 if acc >= 0.75 else None, "hit": acc >= 0.75,
            "timed_out": False, "false_clicks": 0, "effort": 4, "reloads": 0, "metrics": json.dumps(metrics)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="analysis/SIMULATED_trials.csv")
    ap.add_argument("--l2-cost", type=float, default=0.12, help="assumed log-RT cost of an L2 clue")
    ap.add_argument("--decay-start", type=float, default=8.0, help="assumed minute where slowing starts")
    ap.add_argument("--decay-slope", type=float, default=0.04, help="assumed log-RT increase per minute after it")
    ap.add_argument("--scenario", choices=("default", "learning_only"), default="default")
    ap.add_argument("--p-missing-final", type=float, default=0.0,
                    help="share of exhausted quitters who never reach the final questionnaire")
    ap.add_argument("--library", action="store_true", help="add Stroop library blocks with a metrics column")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    df = simulate(args.seed, args.l2_cost, args.decay_start, args.decay_slope, args.scenario,
                  p_missing_final=args.p_missing_final, library=args.library)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} SIMULATED rows ({args.scenario}) to {args.out}")


if __name__ == "__main__":
    main()
