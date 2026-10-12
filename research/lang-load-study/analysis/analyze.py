"""Analyze the exported trials CSV.

Primary question: does a clue in the less comfortable language (L2) slow
visual search, and does that cost differ between groups (e.g. high school
students vs. radiologists)?

Model: linear mixed-effects model on log response time (correct trials only),
    log_rt ~ condition * group * task, random intercept per participant.
log is used because response times are right-skewed.

Secondary:
  - Mental effort (Paas 1-9) ~ condition * group * task (same structure).
  - Does years of education moderate the L2 cost? log_rt ~ condition * education_years.
  - Accuracy (found vs. timed out) by condition, descriptive.

Usage:
    python analysis/analyze.py trials.csv
    python analysis/analyze.py trials.csv --include-test   # for pilot/simulated data
"""
import argparse
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def load(path, include_test):
    df = pd.read_csv(path)
    for col in ("is_test", "practice", "hit", "timed_out", "attention_ok", "completed"):
        if col in df:
            df[col] = df[col].astype(str).str.lower() == "true"
    n0 = df.participant_id.nunique()
    if not include_test:
        df = df[~df.is_test]
    df = df[~df.practice & df.completed & df.attention_ok]
    print(f"Participants: {n0} in file, {df.participant_id.nunique()} after exclusions")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--include-test", action="store_true")
    args = ap.parse_args()

    df = load(args.csv, args.include_test)
    if df.empty:
        sys.exit("No usable rows. Did you mean --include-test?")
    if df.is_test.any():
        print("\n*** WARNING: includes TEST/SIMULATED data. Not reportable as findings. ***")

    print("\nParticipants per group:")
    print(df.groupby("group").participant_id.nunique().to_string())

    print("\nAccuracy (share of targets found) by group, task, condition:")
    print(df.groupby(["group", "task", "condition"]).hit.mean().unstack().round(3).to_string())

    rt = df[df.hit & df.rt_ms.notna()].copy()
    # Trim implausible RTs: under 200 ms is anticipation, not search.
    rt = rt[rt.rt_ms >= 200]
    rt["log_rt"] = np.log(rt.rt_ms)

    print("\nMedian time to find (ms):")
    print(rt.groupby(["group", "task", "condition"]).rt_ms.median().unstack().round(0).to_string())

    print("\n=== Primary model: log_rt ~ condition * group * task ===")
    m1 = smf.mixedlm("log_rt ~ C(condition, Treatment('L1')) * C(group) * C(task)",
                     rt, groups=rt["participant_id"]).fit(reml=True)
    print(m1.summary())

    eff = df[df.effort.notna()]
    print("\n=== Mental effort: effort ~ condition * group * task ===")
    m2 = smf.mixedlm("effort ~ C(condition, Treatment('L1')) * C(group) * C(task)",
                     eff, groups=eff["participant_id"]).fit(reml=True)
    print(m2.summary())

    if rt.education_years.nunique() > 1:
        print("\n=== Exploratory: does education moderate the L2 cost? ===")
        m3 = smf.mixedlm("log_rt ~ C(condition, Treatment('L1')) * education_years + C(task)",
                         rt, groups=rt["participant_id"]).fit(reml=True)
        print(m3.summary())

    print("\nReading the output: a positive coefficient on the L2 condition means slower search")
    print("with an L2 clue. exp(coef) - 1 is the approximate percent slow-down.")


if __name__ == "__main__":
    main()
