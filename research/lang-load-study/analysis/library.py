"""Task labels and per-task summaries for library (plugin) tasks (review finding F12).

Core tasks keep their own trial-level outcome:
  - search, scan, dice: click on the target; `hit` = target found (accuracy).
  - corsi, reading, rule, ospan: one answer per trial; `hit` = answer fully correct.
Library tasks (app/tasks plugins) run a whole block per trial. Their `hit` is a
task-specific PASS THRESHOLD (e.g. go accuracy >= .80 and stop success >= .25)
and is NOT accuracy; their `rt_ms` is block duration, not an event RT. Their real
outcomes live in the export's `metrics` JSON column (accuracy, event RT fields,
costs ...). These are summarised per task; block pass is shown only as a
descriptive quality field.
"""
import json

import numpy as np
import pandas as pd

SEARCH_TASKS = ("search", "scan", "dice")
ANSWER_TASKS = ("corsi", "reading", "rule", "ospan")
CORE_TASKS = SEARCH_TASKS + ANSWER_TASKS
NON_OUTCOME_KEYS = {"response"}

OUTCOME_LABEL = {
    **{t: "accuracy = share of targets found (click on target)" for t in SEARCH_TASKS},
    **{t: "accuracy = share of trials answered fully correctly" for t in ANSWER_TASKS},
}


def is_library(task):
    return task not in CORE_TASKS and task != "surprise"


def parse_metrics(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return {}
    if isinstance(value, dict):
        return value
    try:
        out = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return out if isinstance(out, dict) else {}


def metrics_long(trials):
    """One row per (trial, scalar metric). Booleans become 0/1 (shares); lists, dicts,
    strings and the raw response are skipped."""
    if "metrics" not in trials:
        return pd.DataFrame(columns=["participant_id", "task", "condition", "metric", "value"])
    rows = []
    for rec in trials[["participant_id", "task", "condition", "metrics"]].itertuples(index=False):
        for key, val in parse_metrics(rec.metrics).items():
            if key in NON_OUTCOME_KEYS or val is None:
                continue
            if isinstance(val, bool):
                val = float(val)
            elif isinstance(val, (int, float)) and np.isfinite(val):
                val = float(val)
            else:
                continue
            rows.append((rec.participant_id, rec.task, rec.condition, key, val))
    return pd.DataFrame(rows, columns=["participant_id", "task", "condition", "metric", "value"])


def library_summary(trials):
    """Returns (pass_table, metric_table, note).

    pass_table: per task x condition, n blocks and share passing the task's threshold
                (descriptive quality field only).
    metric_table: per task x metric x condition: mean of per-person means and n people.
    """
    lib = trials[trials.task.map(is_library)]
    if lib.empty:
        return None, None, "No library-task trials in this file."
    pass_table = lib.groupby(["task", "condition"]).agg(n_blocks=("hit", "size"),
                                                        block_pass_share=("hit", "mean"))
    if "metrics" not in lib:
        return pass_table, None, ("Export has no 'metrics' column: library-task outcomes (event accuracy, "
                                  "RTs, costs) cannot be summarised. Block pass flags are shown as a "
                                  "descriptive quality field only, NOT accuracy.")
    long = metrics_long(lib)
    if long.empty:
        return pass_table, None, "Library trials present but no numeric metrics were recorded."
    per_person = long.groupby(["task", "metric", "condition", "participant_id"]).value.mean()
    metric_table = per_person.groupby(["task", "metric", "condition"]).agg(["mean", "size"]) \
        .rename(columns={"mean": "mean_of_person_means", "size": "n_people"})
    return pass_table, metric_table, ""
