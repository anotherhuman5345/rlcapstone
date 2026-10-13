"""Analyze the exported trials CSV.

1. Language of the clue (primary, core tasks). Does a clue in the less
   comfortable language (L2) slow responses, and does that cost differ between
   groups? Mixed-effects model on log response time (correct trials only):
       log_rt ~ condition * group * task, random intercept per participant.
   Outcomes are labelled per task: for search/scan/dice "accuracy" is the share
   of targets found; for corsi/reading/rule/ospan it is the share of trials
   answered fully correctly. The meaning of rt_ms also differs by task.
   Secondary: mental effort (Paas 1-9) with the same structure.

1b. Library (plugin) tasks. Their block `hit` is a task-specific pass threshold,
   not accuracy, so they are excluded from the models above and summarised per
   task from the export's `metrics` JSON column when present.

2. Surprise gorilla (inattentional blindness). One image per person, compared
   BETWEEN people.

3. Time on task. Reports speed, accuracy and the L2 cost per round, time to
   self-declared exhaustion (Kaplan-Meier with tied times grouped), and an
   EXPLORATORY change-point search whose uncertainty re-runs the breakpoint
   selection inside a participant bootstrap.

Eligibility is outcome-specific (see analysis/eligibility.py) and every
exclusion/missingness reason is printed. A missing final questionnaire does not
remove anyone.

Model fitting warnings are shown, not suppressed; a model that fails or does
not converge has its inferential output withheld.

Usage:
    python analysis/analyze.py trials.csv
    python analysis/analyze.py trials.csv --include-test   # for pilot/simulated data
"""
import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from changepoint import bend_search, describe  # noqa: E402
from eligibility import ANALYSES, eligibility, tri_bool, trial_exclusions, trial_validity  # noqa: E402
from library import CORE_TASKS, OUTCOME_LABEL, library_summary  # noqa: E402
from survival import format_median, km_median  # noqa: E402

# Columns where a missing value simply means "no".
FALSE_IF_MISSING = ("is_test", "practice", "hit", "timed_out", "time_capped", "quit_early")
# Columns where missing must stay missing (unknown), e.g. no final questionnaire.
TRI_STATE = ("attention_ok", "completed", "eligible", "noticed_unusual", "saw_gorilla",
             "knew_gorilla_study")
L2 = "C(condition, Treatment('L1'))"
DEFAULT_SESSION_LIMIT_MIN = 60.0


def load(path):
    """Read the export and normalise types. No participant is excluded here:
    eligibility is decided per analysis."""
    df = pd.read_csv(path)
    # Older exports lack these columns; treat everyone as eligible with no reloads.
    if "eligible" not in df:
        df["eligible"] = True
    for col, default in (("reloads", 0), ("focus_lost", 0)):
        if col not in df:
            df[col] = default
    for col in FALSE_IF_MISSING:
        if col in df:
            df[col] = tri_bool(df[col]).fillna(False).astype(bool)
    for col in TRI_STATE:
        if col in df:
            df[col] = tri_bool(df[col])
    if "is_test" not in df:
        df["is_test"] = False
    if "practice" not in df:
        df["practice"] = False
    return df


def fit(formula, data, reml=True, label=None):
    """Fit a mixed model; print every warning; return None (and say so) if the fit
    fails or does not converge, so no inferential output is shown for it."""
    label = label or formula
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            m = smf.mixedlm(formula, data, groups=data["participant_id"]).fit(reml=reml)
        except Exception as exc:  # noqa: BLE001 - report any fitting failure
            print(f"MODEL FAILED ({label}): {type(exc).__name__}: {exc}. No inferential results reported.")
            return None
    msgs = sorted({f"{w.category.__name__}: {w.message}" for w in caught})
    for msg in msgs:
        print(f"  warning while fitting {label}: {msg}")
    if not getattr(m, "converged", True):
        print(f"MODEL DID NOT CONVERGE ({label}). No inferential results reported.")
        return None
    return m


def report(model):
    if model is not None:
        print(model.summary())


def print_eligibility(table, trials_dropped):
    print("\n" + "=" * 70 + "\n0. ELIGIBILITY AND MISSINGNESS (per analysis)\n" + "=" * 70)
    for name, desc in ANALYSES.items():
        sub = table[table.analysis == name]
        print(f"\n{desc} [{name}]")
        for r in sub.itertuples():
            print(f"  {r.reason:<55} {r.n:>6}")
    if len(trials_dropped):
        print("\nScored trials dropped from performance analyses (per-trial validity):")
        print(trials_dropped.to_string())


def correct_rts(trials):
    rt = trials[trials.hit & trials.rt_ms.notna()].copy()
    rt = rt[rt.rt_ms >= 200]  # under 200 ms is anticipation, not search
    rt["log_rt"] = np.log(rt.rt_ms)
    return rt


def language_effect(trials):
    print("\n" + "=" * 70 + "\n1. LANGUAGE OF THE CLUE (core tasks)\n" + "=" * 70)
    core = trials[trials.task.isin(CORE_TASKS)]
    if core.empty:
        print("No core-task trials.")
        return
    print("\nOutcome definitions by task:")
    for task in sorted(core.task.unique()):
        print(f"  {task}: {OUTCOME_LABEL[task]}; rt_ms = time to the scored response")
    print("\nAccuracy (task-specific definition above) by group, task, condition:")
    print(core.groupby(["group", "task", "condition"]).hit.mean().unstack().round(3).to_string())

    rt = correct_rts(core)
    print("\nMedian response time on correct trials (ms):")
    print(rt.groupby(["group", "task", "condition"]).rt_ms.median().unstack().round(0).to_string())

    print("\n--- Model: log_rt ~ condition * group * task ---")
    report(fit(f"log_rt ~ {L2} * C(group) * C(task)", rt))

    eff = core[core.effort.notna()]
    print("\n--- Model: effort ~ condition * group * task ---")
    report(fit(f"effort ~ {L2} * C(group) * C(task)", eff))

    if rt.education_years.nunique() > 1:
        print("\n--- Exploratory: does education moderate the L2 cost? ---")
        report(fit(f"log_rt ~ {L2} * education_years + C(task)", rt))
    print("A positive L2 coefficient means slower responses with an L2 clue; "
          "exp(coef) - 1 is the approximate percent slow-down.")


def library_tasks(trials):
    print("\n" + "=" * 70 + "\n1b. LIBRARY TASKS (per-task outcomes)\n" + "=" * 70)
    pass_table, metric_table, note = library_summary(trials)
    if note:
        print(note)
    if pass_table is not None:
        print("\nBlock pass flag (task-specific threshold; a quality/descriptive field, NOT accuracy):")
        print(pass_table.round(3).to_string())
    if metric_table is not None:
        print("\nTask metrics from the 'metrics' column (mean of per-person means; booleans are shares):")
        print(metric_table.unstack("condition").round(3).to_string())


def gorilla(df):
    print("\n" + "=" * 70 + "\n2. SURPRISE GORILLA (one image per person)\n" + "=" * 70)
    s = df[df.task == "surprise"].drop_duplicates("participant_id")
    s = s[s.reloads.fillna(0) == 0]  # a reloaded surprise image was seen twice
    s = s[s.saw_gorilla.notna()] if "saw_gorilla" in s else s.iloc[0:0]
    if s.empty:
        print("No usable surprise trials in this file.")
        return
    s = s.assign(saw_gorilla=s.saw_gorilla.astype(bool))
    knew = s.knew_gorilla_study.fillna(False).astype(bool)
    naive_mask = s.knew_gorilla_study.astype("boolean").fillna(True) == False  # noqa: E712
    for label, sub in (("Everyone", s), ("Excluding people who knew (or did not answer)", s[naive_mask])):
        print(f"\n{label}: share who saw the gorilla (n in brackets)")
        tab = sub.groupby(["group", "condition"]).saw_gorilla.agg(["mean", "size"])
        print(tab.apply(lambda r: f"{r['mean']:.2f} [{int(r['size'])}]", axis=1).unstack().to_string())
    print("\nKnew the invisible-gorilla study, by group:")
    print(s.assign(knew=knew).groupby("group").knew.mean().round(2).to_string())
    print("\nSaid they noticed something unusual vs. said they saw a gorilla:")
    print(pd.crosstab(s.noticed_unusual, s.saw_gorilla).to_string())

    naive = s[naive_mask].copy()
    naive["saw"] = naive.saw_gorilla.astype(int)
    if naive.saw.nunique() == 2 and len(naive) >= 20:
        print("\n--- Logistic model (people who did not know the study): saw ~ condition + group ---")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                m = smf.logit(f"saw ~ {L2} + C(group)", naive).fit(disp=False)
            except Exception as exc:  # noqa: BLE001
                print(f"MODEL FAILED: {type(exc).__name__}: {exc}. No inferential results reported.")
                return
        for msg in sorted({f"{w.category.__name__}: {w.message}" for w in caught}):
            print(f"  warning while fitting logistic model: {msg}")
        if not m.mle_retvals.get("converged", True):
            print("MODEL DID NOT CONVERGE. No inferential results reported.")
            return
        print(m.summary())
        print("A negative L2 coefficient means FEWER people saw the gorilla with an L2 clue; "
              "exp(coef) is the odds ratio.")


def stopping(df, people_ids, session_limit_min):
    """Time to self-declared exhaustion. Uses everyone eligible for the stopping
    analysis, including people who never reached the final questionnaire."""
    d = df[df.participant_id.isin(people_ids)]
    print(f"\nTime to self-declared exhaustion ({len(people_ids)} people, incl. those without a final "
          "questionnaire):")
    if d.empty:
        print("  no data")
        return None
    scored = d[d["round"].notna() & ~d.practice]
    # Person-level flags: true if set on any row; first non-missing stop time.
    people = d.groupby("participant_id").agg(group=("group", "first"), quit=("quit_early", "max"),
                                             quit_s=("quit_elapsed_s", "first"),
                                             capped=("time_capped", "max"))
    people["last_min"] = scored.groupby("participant_id").elapsed_s.max().reindex(people.index) / 60
    people["quit_min"] = people.quit_s / 60
    print(f"Share of people stopped by the {session_limit_min:g}-minute limit: {people.capped.mean():.2f}")
    summary = people.groupby("group").agg(share=("quit", "mean"), n=("quit", "size"),
                                          median_minute=("quit_min", "median"))
    print("Pressed \"I'm exhausted\": share of people and median minute among those who pressed, by group:")
    print(summary.round(2).to_string())
    # Event = pressed the button. Everyone else is censored at their last recorded time
    # (or the session limit if capped and no later timestamp exists).
    people["time"] = np.where(people.quit, people.quit_min.fillna(people.last_min),
                              np.where(people.capped, people.last_min.fillna(session_limit_min),
                                       people.last_min))
    people = people[people.time.notna()]
    print("\nMedian minutes to self-declared exhaustion (Kaplan-Meier; tied times grouped; "
          "non-pressers censored at their last recorded time):")
    for group, g in people.groupby("group"):
        print(f"  {group}: {format_median(km_median(g.time.values, g.quit.values))} (n = {len(g)})")
    return people


def time_on_task(trials, df, stopping_ids, session_limit_min, n_boot, seed):
    print("\n" + "=" * 70 + "\n3. TIME ON TASK\n" + "=" * 70)
    core = trials[trials.task.isin(CORE_TASKS)]
    rt = correct_rts(core)
    rt["elapsed_min"] = rt.elapsed_s / 60
    print("\nMedian response time on correct core-task trials (ms) per round, by group:")
    print(rt.groupby(["group", "round"]).rt_ms.median().unstack().round(0).to_string())
    print("\nAccuracy per round, by task (task-specific definitions, see section 1):")
    print(core.groupby(["task", "round"]).hit.mean().unstack().round(3).to_string())
    print("\nL2 cost per round (median L2 time / median L1 time):")
    med = rt.groupby(["round", "condition"]).rt_ms.median().unstack()
    if {"L1", "L2"} <= set(med.columns):
        print((med.L2 / med.L1).round(3).to_string())

    people = stopping(df, stopping_ids, session_limit_min)

    print("\n--- Model: does the L2 cost change with time on task? ---")
    report(fit(f"log_rt ~ {L2} * elapsed_min + C(group) + C(task)", rt))

    print("\n--- Change-point search ---")
    res = bend_search(rt, n_boot=n_boot, seed=seed)
    for line in describe(res, session_limit_min):
        print(line)
    return res, people


def retention(df):
    """End-of-session word recognition (operation-span words seen earlier).
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


def fatigue(f, people):
    """Self-rated mental fatigue (0-100). Kept separate from performance: the two need not
    move together. Reports raw ratings and change from each person's own baseline."""
    print("\n" + "=" * 70 + "\n4. SELF-RATED FATIGUE (0-100)\n" + "=" * 70)
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
    rounds = f[f.point.str.startswith("after_round_") & f.elapsed_s.notna() & f.change.notna()].copy()
    if rounds.participant_id.nunique() > 3:
        rounds["elapsed_min"] = rounds.elapsed_s / 60
        print("\n--- Model: change from baseline ~ elapsed minutes + group ---")
        report(fit("change ~ elapsed_min + C(group)", rounds))


def run(df, include_test=False, attention_policy="exclude", fatigue_df=None,
        session_limit_min=DEFAULT_SESSION_LIMIT_MIN, n_boot=200, seed=0):
    """Run every analysis on a loaded frame. Returns a dict of intermediate results (for tests)."""
    fatigue_ids = set(fatigue_df.participant_id) if fatigue_df is not None else None
    included, table = eligibility(df, include_test, attention_policy, fatigue_ids)
    print(f"Participants in file: {df.participant_id.nunique()}")
    if include_test and df.is_test.any():
        print("\n*** WARNING: includes TEST/SIMULATED data. Not reportable as findings. ***")
    perf = df[df.participant_id.isin(included["performance"])]
    scored = perf[perf["round"].notna() & ~perf.practice]
    dropped = trial_exclusions(scored) if len(scored) else pd.Series(dtype=int)
    print_eligibility(table, dropped)
    trials = trial_validity(scored) if len(scored) else scored
    trials = trials[trials.valid] if len(trials) else trials
    out = {"included": included, "eligibility": table, "trials": trials}
    if trials.empty:
        print("\nNo valid scored trials for the performance analyses.")
    else:
        print("\nParticipants per group (performance analyses):")
        print(trials.groupby("group").participant_id.nunique().to_string())
        language_effect(trials)
        library_tasks(trials)
    gorilla(df[df.participant_id.isin(included["gorilla"])])
    if not trials.empty:
        out["bend"], out["stopping"] = time_on_task(trials, df, included["stopping"], session_limit_min,
                                                    n_boot, seed)
    else:
        print("\n" + "=" * 70 + "\n3. TIME ON TASK\n" + "=" * 70)
        out["stopping"] = stopping(df, included["stopping"], session_limit_min)
    retention(df[df.participant_id.isin(included["retention"])])
    if fatigue_df is not None:
        fatigue(fatigue_df, included["fatigue_ratings"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--include-test", action="store_true")
    ap.add_argument("--fatigue", help="fatigue.csv export (0-100 ratings at start, after rounds, end)")
    ap.add_argument("--attention-policy", choices=("exclude", "keep"), default="exclude",
                    help="what to do with an explicit wrong end-of-session attention answer in the "
                         "performance analyses (a missing answer never excludes anyone)")
    ap.add_argument("--session-limit-min", type=float, default=DEFAULT_SESSION_LIMIT_MIN,
                    help="session length from the frozen protocol (minutes), used in report wording")
    ap.add_argument("--bootstrap", type=int, default=200, help="bootstrap resamples for the change-point CI")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    df = load(args.csv)
    if df.empty:
        sys.exit("No rows in file.")
    if not args.include_test and df.is_test.all():
        sys.exit("Only test/simulated rows in this file. Did you mean --include-test?")
    fatigue_df = pd.read_csv(args.fatigue) if args.fatigue else None
    run(df, args.include_test, args.attention_policy, fatigue_df, args.session_limit_min,
        args.bootstrap, args.seed)


if __name__ == "__main__":
    main()
