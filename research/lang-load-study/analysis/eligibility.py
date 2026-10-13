"""Outcome-specific eligibility (review finding F07).

There is no single complete-case filter any more. Each analysis has its own
predeclared rule, and every participant who is left out of an analysis gets
exactly one reason (the first rule they fail, in the order listed below), so
the exclusion table adds up.

Rules shared by every analysis
  - test/simulated sessions are dropped unless --include-test is given;
  - people who did not pass the language-reading screen (eligible == False)
    were never part of the target sample.

A missing final questionnaire is NOT treated as inattentiveness or as an
invalid session: people who stop because they are exhausted often never reach
it. "completed" and "attention_ok" are used only where they matter:
  - attention_ok == False (an explicit wrong answer to the end-of-session
    question) excludes a person from the trial-level performance analyses when
    attention_policy == "exclude" (default). That question asks about a practice
    target seen long before, so a wrong answer may be a delayed-recall failure
    rather than inattention; the exclusion count is always reported, and
    attention_policy == "keep" runs the analyses without it;
  - a missing attention answer (no final questionnaire) never excludes anyone.

Trial-level validity (performance analyses): a scored round trial is valid when
it was not reloaded (image seen before the clock restarted) and the tab was not
hidden during it. RT analyses additionally use only correct trials with RT >= 200 ms.
"""
import numpy as np
import pandas as pd

TRUE = {"true", "1", "yes", "t"}
FALSE = {"false", "0", "no", "f"}

# Analyses, in report order.
ANALYSES = {
    "performance": "Language of the clue and time on task (trial-level RT/accuracy)",
    "stopping": "Self-declared exhaustion / stopping (time to event)",
    "gorilla": "Surprise gorilla (between people)",
    "retention": "End-of-session word recognition",
    "fatigue_ratings": "Self-rated fatigue (0-100)",
}


def tri_bool(series):
    """Map strings/bools to True / False / NA (pandas nullable boolean)."""
    def conv(v):
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return pd.NA
        s = str(v).strip().lower()
        if s in TRUE:
            return True
        if s in FALSE:
            return False
        return pd.NA
    return series.map(conv).astype("boolean")


def trial_validity(trials):
    """Per-trial validity flags for scored round trials; returns a copy with
    `valid` and `invalid_reason` columns."""
    t = trials.copy()
    reloaded = t.reloads.fillna(0) > 0
    hidden = t.focus_lost.fillna(0) > 0
    t["invalid_reason"] = np.where(reloaded, "reloaded (image seen before clock restart)",
                                   np.where(hidden, "tab hidden during trial", ""))
    t["valid"] = t.invalid_reason == ""
    return t


def _first_reason(checks):
    """checks: list of (reason, bool Series indexed by participant). Returns a Series of
    the first failed reason per participant ('' = included)."""
    idx = checks[0][1].index
    out = pd.Series("", index=idx, dtype=object)
    for reason, failed in checks:
        failed = failed.reindex(idx).fillna(False).astype(bool)
        out[(out == "") & failed] = reason
    return out


def participant_frame(df):
    g = df.groupby("participant_id", sort=False)
    people = g.agg(is_test=("is_test", "first"), eligible=("eligible", "first"),
                   completed=("completed", "first"), attention_ok=("attention_ok", "first"),
                   quit_early=("quit_early", "max"))  # person-level: true on any row
    scored = df[df["round"].notna() & ~df.practice]
    scored = trial_validity(scored) if len(scored) else scored.assign(valid=pd.Series(dtype=bool))
    people["n_scored"] = scored.groupby("participant_id").size().reindex(people.index).fillna(0)
    people["n_valid"] = scored[scored.valid].groupby("participant_id").size().reindex(people.index).fillna(0)
    sur = df[df.task == "surprise"]
    people["has_surprise"] = people.index.isin(sur.participant_id)
    if "saw_gorilla" in df:
        ans = sur.groupby("participant_id").saw_gorilla.first()
        people["has_gorilla_answer"] = ans.reindex(people.index).notna()
    else:
        people["has_gorilla_answer"] = False
    people["surprise_reloaded"] = (sur.groupby("participant_id").reloads.first().fillna(0) > 0) \
        .reindex(people.index).fillna(False)
    ret = ["ret_l1_hits", "ret_l1_false_alarms", "ret_l2_hits", "ret_l2_false_alarms"]
    if set(ret) <= set(df.columns):
        people["has_retention"] = g[ret].first().notna().all(axis=1)
    else:
        people["has_retention"] = False
    return people


def eligibility(df, include_test=False, attention_policy="exclude", fatigue_ids=None):
    """Return (included, table).

    included: {analysis: set of participant ids}
    table: one row per (analysis, reason) with the number of participants; reasons
    starting with 'kept:' describe missingness among included people (not exclusions).
    """
    if attention_policy not in ("exclude", "keep"):
        raise ValueError("attention_policy must be 'exclude' or 'keep'")
    p = participant_frame(df)
    test = p.is_test.fillna(False).astype(bool) if not include_test else pd.Series(False, index=p.index)
    inelig = p.eligible.fillna(True).astype(bool) == False  # noqa: E712  (missing = older export: eligible)
    base = [("test/simulated session", test), ("failed language-reading screen", inelig)]
    attn_fail = p.attention_ok.astype("boolean").fillna(True) == False  # noqa: E712  explicit wrong answer only
    no_final = ~p.completed.fillna(False).astype(bool)

    rules = {
        "performance": base + [("no valid scored trials", p.n_valid == 0)]
        + ([("wrong end-of-session attention answer", attn_fail)] if attention_policy == "exclude" else []),
        "stopping": base + [("no scored trials (never started the timed task)", (p.n_scored == 0)
                             & ~p.quit_early.fillna(False).astype(bool))],
        "gorilla": base + [("no surprise trial", ~p.has_surprise),
                           ("surprise questions not answered", ~p.has_gorilla_answer),
                           ("surprise image reloaded (seen twice)", p.surprise_reloaded.astype(bool))],
        "retention": base + [("no retention data", ~p.has_retention)],
        "fatigue_ratings": base + ([("no fatigue ratings", pd.Series(~p.index.isin(list(fatigue_ids)), index=p.index))]
                                   if fatigue_ids is not None else []),
    }
    included, rows = {}, []
    for name, checks in rules.items():
        reason = _first_reason(checks)
        inc = reason == ""
        included[name] = set(reason.index[inc])
        rows.append({"analysis": name, "reason": "in file", "n": len(reason)})
        for r, _ in checks:
            rows.append({"analysis": name, "reason": f"excluded: {r}", "n": int((reason == r).sum())})
        rows.append({"analysis": name, "reason": "included", "n": int(inc.sum())})
        rows.append({"analysis": name, "reason": "kept: no final questionnaire",
                     "n": int((inc & no_final).sum())})
        rows.append({"analysis": name, "reason": "kept: pressed I'm exhausted",
                     "n": int((inc & p.quit_early.fillna(False).astype(bool)).sum())})
        if name != "performance" or attention_policy == "keep":
            rows.append({"analysis": name, "reason": "kept: wrong end-of-session attention answer",
                         "n": int((inc & attn_fail).sum())})
    return included, pd.DataFrame(rows)


def trial_exclusions(trials):
    """Counts of scored trials dropped from performance analyses, by reason."""
    t = trial_validity(trials)
    return t[~t.valid].invalid_reason.value_counts().rename("n_trials")
