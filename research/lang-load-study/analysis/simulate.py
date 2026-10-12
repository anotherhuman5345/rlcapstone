"""Make a FAKE dataset with the same columns as the real export, so the
analysis pipeline can be tested before any real data exist.

Every row is marked is_test=True and the file is named SIMULATED. Never
report these numbers as findings. The assumed effects below exist only to
check that the analysis can find an effect when one is there.
"""
import argparse
import uuid

import numpy as np
import pandas as pd

GROUP_SETUP = {  # group: (n, age, education years, years reading images, P(saw gorilla | L1), P(knew study))
    "high_school": (80, 16, 11, 0, 0.55, 0.05),
    "adult": (40, 45, 14, 0, 0.50, 0.10),
    "phd_student": (30, 29, 20, 0, 0.50, 0.15),
    "radiologist": (30, 42, 22, 12, 0.35, 0.40),
}
ROUNDS, PER_TASK_PER_ROUND = 12, 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="analysis/SIMULATED_trials.csv")
    ap.add_argument("--l2-cost", type=float, default=0.12, help="assumed log-RT cost of an L2 clue")
    ap.add_argument("--decay-start", type=float, default=8.0, help="assumed minute where slowing starts")
    ap.add_argument("--decay-slope", type=float, default=0.04, help="assumed log-RT increase per minute after it")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    rows = []
    for group, (n, age, edu, yrs, p_saw, p_knew) in GROUP_SETUP.items():
        for k in range(n):
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
                "en_reading": 7, "tr_reading": 6, "l1": l1, "l2": l2, "eligible": True,
                "counterbalance": k % 4, "attention_ok": True, "completed": True, "time_capped": False,
                "noticed_unusual": saw or bool(rng.random() < 0.1), "saw_gorilla": saw,
                "knew_gorilla_study": knew,
            }
            clock = 0.0
            rt0 = float(np.exp(8.3 + person + rng.normal(0, 0.3)))
            clock += rt0 / 1000 + 4
            rows.append({**common, "trial_index": 0, "round": None, "elapsed_s": round(clock, 1),
                         "task": "surprise", "image_id": "surprise",
                         "clue_lang": l1 if surprise_cond == "L1" else l2, "condition": surprise_cond,
                         "practice": False, "rt_ms": round(rt0), "hit": True, "timed_out": False,
                         "false_clicks": 0, "effort": 3, "reloads": 0})
            clock += 60  # surprise questions + instructions + 2 practice trials
            i = 3
            for r in range(1, ROUNDS + 1):
                if common["time_capped"]:
                    break
                trials = [(task, j) for task in ("search", "scan") for j in range(PER_TASK_PER_ROUND)]
                rng.shuffle(trials)
                for task, j in trials:
                    cond = "L1" if (j + k) % 2 == 0 else "L2"
                    base = 8.4 if task == "search" else 8.1
                    if group == "radiologist" and task == "scan":
                        base -= 0.15  # assumed expertise benefit on scans
                    cost = args.l2_cost * (0.6 if group == "radiologist" else 1.0) if cond == "L2" else 0
                    minutes = clock / 60
                    learning = -0.03 * min(minutes, 4)  # assumed practice speed-up early on
                    decay = args.decay_slope * max(0.0, minutes - args.decay_start)
                    log_rt = base + person + cost + learning + decay + rng.normal(0, 0.35)
                    rt = float(np.exp(log_rt))
                    if clock > 14 * 60 - 60:  # session time limit (counted from the start page)
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
    df = pd.DataFrame(rows)
    # time_capped is a per-person flag; make every row of a person agree.
    df["time_capped"] = df.groupby("participant_id").time_capped.transform("max")
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(rows)} SIMULATED rows to {args.out}")


if __name__ == "__main__":
    main()
