"""Analyze the exported trials CSV.

1. Language of the clue (primary). Does a clue in the less comfortable
   language (L2) slow visual search, and does that cost differ between groups?
   Mixed-effects model on log response time (correct trials only):
       log_rt ~ condition * group * task, random intercept per participant.
   log is used because response times are right-skewed.
   Secondary: mental effort (Paas 1-9) with the same structure.

2. Surprise gorilla (inattentional blindness). One image per person, so this
   is compared BETWEEN people: share who saw the gorilla, by group and by the
   language of the surprise clue. Reported with and without people who already
   knew the invisible-gorilla study.

3. Time on task. Every round has the same mix, so changes across rounds come
   from time on task. Reports speed, accuracy and the L2 cost per round, and
   searches for the minute where slowing starts (piecewise-linear model).
   Caution: practice makes people faster over time and can hide fatigue.

Usage:
    python analysis/analyze.py trials.csv
    python analysis/analyze.py trials.csv --include-test   # for pilot/simulated data
"""
import argparse
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

BOOL_COLS = ("is_test", "practice", "hit", "timed_out", "attention_ok", "completed", "eligible",
             "noticed_unusual", "saw_gorilla", "knew_gorilla_study", "time_capped", "quit_early")
L2 = "C(condition, Treatment('L1'))"


def load(path, include_test):
    df = pd.read_csv(path)
    # Older exports lack these columns; treat everyone as eligible with no reloads.
    df["eligible"] = df.get("eligible", True)
    df["reloads"] = df.get("reloads", 0)
    df["focus_lost"] = df.get("focus_lost", 0)
    for col in BOOL_COLS:
        if col in df:
            df[col] = df[col].astype(str).str.lower() == "true"
    n0 = df.participant_id.nunique()
    if not include_test:
        df = df[~df.is_test]
    df = df[df.completed & df.attention_ok & df.eligible]
    print(f"Participants: {n0} in file, {df.participant_id.nunique()} after exclusions")
    return df


def language_effect(trials):
    print("\n" + "=" * 70 + "\n1. LANGUAGE OF THE CLUE\n" + "=" * 70)
    print("\nAccuracy (share of targets found) by group, task, condition:")
    print(trials.groupby(["group", "task", "condition"]).hit.mean().unstack().round(3).to_string())

    rt = correct_rts(trials)
    print("\nMedian time to find (ms):")
    print(rt.groupby(["group", "task", "condition"]).rt_ms.median().unstack().round(0).to_string())

    print(f"\n--- Model: log_rt ~ condition * group * task ---")
    print(fit(f"log_rt ~ {L2} * C(group) * C(task)", rt).summary())

    eff = trials[trials.effort.notna()]
    print(f"\n--- Model: effort ~ condition * group * task ---")
    print(fit(f"effort ~ {L2} * C(group) * C(task)", eff).summary())

    if rt.education_years.nunique() > 1:
        print("\n--- Exploratory: does education moderate the L2 cost? ---")
        print(fit(f"log_rt ~ {L2} * education_years + C(task)", rt).summary())
    print("A positive L2 coefficient means slower search with an L2 clue; "
          "exp(coef) - 1 is the approximate percent slow-down.")


def gorilla(df):
    print("\n" + "=" * 70 + "\n2. SURPRISE GORILLA (one image per person)\n" + "=" * 70)
    s = df[df.task == "surprise"].drop_duplicates("participant_id")
    if s.empty:
        print("No surprise trials in this file.")
        return
    s = s[s.reloads.fillna(0) == 0]  # a reloaded surprise image was seen twice
    for label, sub in (("Everyone", s), ("Excluding people who knew the study", s[~s.knew_gorilla_study])):
        print(f"\n{label}: share who saw the gorilla (n in brackets)")
        tab = sub.groupby(["group", "condition"]).saw_gorilla.agg(["mean", "size"])
        print(tab.apply(lambda r: f"{r['mean']:.2f} [{int(r['size'])}]", axis=1).unstack().to_string())
    print(f"\nKnew the invisible-gorilla study, by group:")
    print(s.groupby("group").knew_gorilla_study.mean().round(2).to_string())
    print(f"\nSaid they noticed something unusual vs. said they saw a gorilla:")
    print(pd.crosstab(s.noticed_unusual, s.saw_gorilla).to_string())

    naive = s[~s.knew_gorilla_study].copy()
    naive["saw"] = naive.saw_gorilla.astype(int)
    if naive.saw.nunique() == 2 and len(naive) >= 20:
        print(f"\n--- Logistic model (people who did not know the study): saw ~ condition + group ---")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.logit(f"saw ~ {L2} + C(group)", naive).fit(disp=False)
        print(m.summary())
        print("A negative L2 coefficient means FEWER people saw the gorilla with an L2 clue; "
              "exp(coef) is the odds ratio.")


def time_on_task(trials):
    print("\n" + "=" * 70 + "\n3. TIME ON TASK\n" + "=" * 70)
    rt = correct_rts(trials)
    rt["elapsed_min"] = rt.elapsed_s / 60
    print("\nMedian time to find (ms) per round, by group:")
    print(rt.groupby(["group", "round"]).rt_ms.median().unstack().round(0).to_string())
    print("\nAccuracy per round, by group:")
    print(trials.groupby(["group", "round"]).hit.mean().unstack().round(3).to_string())
    print("\nL2 cost per round (median L2 time / median L1 time):")
    med = rt.groupby(["round", "condition"]).rt_ms.median().unstack()
    print((med.L2 / med.L1).round(3).to_string())
    capped = trials.groupby("participant_id").time_capped.first().mean()
    print(f"\nShare of people stopped by the 15-minute limit: {capped:.2f}")
    if "quit_early" in trials:
        # The "I'm exhausted" button: a direct, self-reported measure of fatigue.
        people = trials.groupby("participant_id").agg(group=("group", "first"), quit=("quit_early", "first"),
                                                     quit_min=("quit_elapsed_s", "first"))
        people["quit_min"] = people.quit_min / 60
        print("\nPressed \"I'm exhausted\": share of people and median minute, by group:")
        summary = people.groupby("group").agg(share=("quit", "mean"), n=("quit", "size"),
                                             median_minute=("quit_min", "median"))
        print(summary.round(2).to_string())
        # Time to exhaustion as survival data: pressing the button is the event; people who
        # reached the safety maximum (or ran out of items) are censored at their last answer.
        last = trials.groupby("participant_id").elapsed_s.max() / 60
        people["time"] = people.quit_min.fillna(last)
        print("\nMedian minutes to self-declared exhaustion (Kaplan-Meier, censored at the end):")
        for group, g in people.groupby("group"):
            print(f"  {group}: {km_median(g.time.values, g.quit.values)}")

    print("\n--- Model: does the L2 cost change with time on task? ---")
    print(fit(f"log_rt ~ {L2} * elapsed_min + C(group) + C(task)", rt).summary())

    # Where does slowing start? Try each candidate minute as a bend point and keep the
    # best-fitting one. Compare against no bend (straight line) before believing it.
    # log(elapsed) soaks up the early practice speed-up, so the end of learning
    # is not mistaken for the start of fatigue.
    lo, hi = rt.elapsed_min.quantile([.1, .9])
    base = fit(f"log_rt ~ elapsed_min + np.log(elapsed_min) + {L2} + C(group) + C(task)", rt, reml=False)
    best = None
    for k in np.arange(np.ceil(lo), np.floor(hi) + .01, 0.5):
        rt["after"] = np.clip(rt.elapsed_min - k, 0, None)
        m = fit(f"log_rt ~ elapsed_min + np.log(elapsed_min) + after + {L2} + C(group) + C(task)",
                rt, reml=False)
        if best is None or m.llf > best[1].llf:
            best = (k, m)
    if best:
        k, m = best
        lr = 2 * (m.llf - base.llf)
        print(f"\nBest bend point: {k:.1f} min. Slope before: {m.params['elapsed_min']:+.4f} log-ms/min, "
              f"change after: {m.params['after']:+.4f} (likelihood-ratio vs. straight line: {lr:.1f}).")
        print("A positive change after the bend means people slow down from that minute on. "
              "A likelihood ratio below ~6 is not convincing evidence of a bend; "
              "report it as 'no clear decay within 15 minutes'.")


def retention(df):
    """End-of-session word recognition (operation-span words seen ~10 minutes earlier).
    Hits = seen words ticked; false alarms = never-shown words ticked. Compared within
    person: words from L1 trials vs. words from L2 trials."""
    cols = ["ret_l1_hits", "ret_l1_false_alarms", "ret_l2_hits", "ret_l2_false_alarms"]
    if not set(cols) <= set(df.columns):
        return
    people = df.groupby("participant_id").agg(group=("group", "first"),
                                              **{c: (c, "first") for c in cols}).dropna()
    print("\n" + "=" * 70 + "\n5. WORD RETENTION (operation-span words, end of session)\n" + "=" * 70)
    if people.empty:
        print("No retention data.")
        return
    print("\nMean hit and false-alarm rates by group:")
    print(people.groupby("group")[cols].mean().round(2).to_string())
    diff = people.ret_l1_hits - people.ret_l2_hits
    print(f"\nL1 minus L2 hit rate: mean {diff.mean():+.3f} (n = {len(diff)}); "
          "positive means words seen in the comfortable language were remembered better.")


def fatigue(path, people):
    """Self-rated mental fatigue (0-100). Kept separate from performance: the two need not
    move together. Reports raw ratings and change from each person's own baseline."""
    print("\n" + "=" * 70 + "\n4. SELF-RATED FATIGUE (0-100)\n" + "=" * 70)
    f = pd.read_csv(path)
    f = f[f.participant_id.isin(people)]
    if f.empty:
        print("No fatigue ratings for the included participants.")
        return
    base = f[f.point == "baseline"].set_index("participant_id").value
    f = f.assign(change=f.value - f.participant_id.map(base))
    order = {"baseline": 0, "final": 999}
    f["step"] = f.point.map(lambda pt: order.get(pt, int(pt.rsplit("_", 1)[1]) if pt.startswith("after_round_") else -1))
    print("\nMedian rating by group at baseline, after rounds 1-3, and at the end:")
    keep = f[f.step.isin([0, 1, 2, 3, 999])]
    print(keep.pivot_table(index="group", columns="point", values="value", aggfunc="median")
          .reindex(columns=["baseline", "after_round_1", "after_round_2", "after_round_3", "final"]).round(0).to_string())
    rounds = f[f.point.str.startswith("after_round_") & f.elapsed_s.notna()].copy()
    if rounds.participant_id.nunique() > 3:
        rounds["elapsed_min"] = rounds.elapsed_s / 60
        print("\n--- Model: change from baseline ~ elapsed minutes + group ---")
        print(fit("change ~ elapsed_min + C(group)", rounds).summary())


def km_median(times, events):
    """Kaplan-Meier median survival time; 'not reached' if fewer than half pressed the button."""
    order = np.argsort(times)
    times, events = np.asarray(times)[order], np.asarray(events)[order]
    at_risk, surv = len(times), 1.0
    for t, e in zip(times, events):
        if e:
            surv *= 1 - 1 / at_risk
            if surv <= .5:
                return f"{t:.1f} min"
        at_risk -= 1
    return "not reached"


def correct_rts(trials):
    rt = trials[trials.hit & trials.rt_ms.notna()].copy()
    rt = rt[rt.rt_ms >= 200]  # under 200 ms is anticipation, not search
    rt["log_rt"] = np.log(rt.rt_ms)
    return rt


def fit(formula, data, reml=True):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return smf.mixedlm(formula, data, groups=data["participant_id"]).fit(reml=reml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--include-test", action="store_true")
    ap.add_argument("--fatigue", help="fatigue.csv export (0-100 ratings at start, after rounds, end)")
    args = ap.parse_args()

    df = load(args.csv, args.include_test)
    if df.empty:
        sys.exit("No usable rows. Did you mean --include-test?")
    if df.is_test.any():
        print("\n*** WARNING: includes TEST/SIMULATED data. Not reportable as findings. ***")
    print("\nParticipants per group:")
    print(df.groupby("group").participant_id.nunique().to_string())

    # Scored round trials only. A reloaded trial means the image was seen before the clock
    # restarted; a trial where the tab was hidden was interrupted. Both are dropped (and counted).
    trials = df[df["round"].notna() & ~df.practice]
    reloaded = trials.reloads.fillna(0) > 0
    hidden = trials.focus_lost.fillna(0) > 0
    if reloaded.any() or hidden.any():
        print(f"Dropped {int(reloaded.sum())} reloaded and {int((hidden & ~reloaded).sum())} "
              "interrupted (tab hidden) round trials")
    trials = trials[~reloaded & ~hidden]

    language_effect(trials)
    gorilla(df)
    time_on_task(trials)
    retention(df)
    if args.fatigue:
        fatigue(args.fatigue, set(df.participant_id))


if __name__ == "__main__":
    main()
