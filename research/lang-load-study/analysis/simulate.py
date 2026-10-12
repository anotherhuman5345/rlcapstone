"""Make a FAKE dataset with the same columns as the real export, so the
analysis pipeline can be tested before any real data exist.

Every row is marked is_test=True and the file is named SIMULATED. Never
report these numbers as findings.
"""
import argparse
import uuid

import numpy as np
import pandas as pd

GROUP_SETUP = {  # group: (n, age, education years, years reading images)
    "high_school": (40, 16, 11, 0),
    "radiologist": (20, 42, 22, 12),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="analysis/SIMULATED_trials.csv")
    ap.add_argument("--l2-cost", type=float, default=0.12, help="assumed log-RT cost of an L2 clue")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    rows = []
    for group, (n, age, edu, yrs) in GROUP_SETUP.items():
        for k in range(n):
            pid = str(uuid.uuid4())
            person = rng.normal(0, 0.15)
            l1 = rng.choice(["en", "tr"])
            l2 = "tr" if l1 == "en" else "en"
            for task in ("search", "scan"):
                for i in range(12):
                    cond = "L1" if (i + k) % 2 == 0 else "L2"
                    base = 8.4 if task == "search" else 8.1
                    if group == "radiologist" and task == "scan":
                        base -= 0.15  # assumed expertise benefit on scans
                    cost = args.l2_cost * (0.6 if group == "radiologist" else 1.0) if cond == "L2" else 0
                    log_rt = base + person + cost + rng.normal(0, 0.35)
                    rt = float(np.exp(log_rt))
                    timed_out = rt > 60000
                    rows.append({
                        "participant_id": pid, "is_test": True, "group": group,
                        "age": age + int(rng.integers(0, 4)), "education_years": edu,
                        "years_reading_images": yrs, "native_lang": l1, "l2_age_acquired": 6,
                        "en_reading": 7, "tr_reading": 6, "l1": l1, "l2": l2, "counterbalance": k % 4,
                        "attention_ok": True, "completed": True, "trial_index": i, "task": task,
                        "image_id": f"{task}_{i:02d}", "clue_lang": l1 if cond == "L1" else l2,
                        "condition": cond, "practice": False,
                        "rt_ms": None if timed_out else round(rt), "hit": not timed_out,
                        "timed_out": timed_out, "false_clicks": int(rng.poisson(0.5)),
                        "effort": int(np.clip(round(4 + (1 if cond == "L2" else 0) + rng.normal(0, 1.3)), 1, 9)),
                    })
    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"Wrote {len(rows)} SIMULATED rows to {args.out}")


if __name__ == "__main__":
    main()
