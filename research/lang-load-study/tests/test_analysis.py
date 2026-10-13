"""Tests for the statistics pipeline in analysis/ (review findings F07, F12, F13, F19).

Run with:  pytest -q tests/test_analysis.py
"""
import itertools
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ANALYSIS = Path(__file__).resolve().parents[1] / "analysis"
sys.path.insert(0, str(ANALYSIS))

import analyze  # noqa: E402
from changepoint import BendResult, bend_search, describe  # noqa: E402
from eligibility import eligibility  # noqa: E402
from library import library_summary  # noqa: E402
from simulate import simulate  # noqa: E402
from survival import km_curve, km_median  # noqa: E402


# ---------------------------------------------------------------- F13: Kaplan-Meier

def brute_force_km(times, events):
    """Independent textbook product-limit estimate, written without numpy grouping:
    S(t) = prod over distinct event times u <= t of (1 - d_u / n_u)."""
    data = list(zip([float(t) for t in times], [bool(e) for e in events]))
    curve = {}
    s = 1.0
    for u in sorted({t for t, _ in data}):
        n_u = sum(1 for t, _ in data if t >= u)
        d_u = sum(1 for t, e in data if t == u and e)
        s = s * (1 - d_u / n_u)
        curve[u] = s
    return curve


def brute_force_median(times, events):
    for u, s in sorted(brute_force_km(times, events).items()):
        if s <= 0.5 + 1e-12:
            return u
    return None


def test_km_review_fixture_is_order_invariant():
    a = km_curve([1, 1, 2], [False, True, False])
    b = km_curve([1, 1, 2], [True, False, False])
    pd.testing.assert_frame_equal(a, b)
    # Tied at t=1: 3 at risk, 1 event -> S = 2/3; never reaches 0.5.
    assert a.survival.tolist() == pytest.approx([2 / 3, 2 / 3])
    assert km_median([1, 1, 2], [False, True, False]) is None
    assert km_median([1, 1, 2], [True, False, False]) is None


def test_km_all_permutations_of_ties_identical():
    times = [1, 1, 1, 2, 2, 3, 3]
    events = [1, 0, 1, 0, 1, 1, 0]
    ref = km_curve(times, events)
    ref_med = km_median(times, events)
    for arrangement in set(itertools.permutations(zip(times, events))):
        t, e = zip(*arrangement)
        pd.testing.assert_frame_equal(km_curve(t, e), ref)
        assert km_median(t, e) == ref_med


def test_km_hand_computed_reference():
    # t=2: n=8,d=1 -> 7/8; t=3: n=7,d=1 (one censored at 3 stays at risk) -> 6/8;
    # t=5: n=5,d=1 -> 0.6; t=6: n=4,d=2 -> 0.3; t=8: censored only.
    times = [2, 3, 3, 5, 6, 6, 6, 8]
    events = [1, 1, 0, 1, 1, 1, 0, 0]
    c = km_curve(times, events)
    assert c.time.tolist() == [2, 3, 5, 6, 8]
    assert c.n_risk.tolist() == [8, 7, 5, 4, 1]
    assert c.n_events.tolist() == [1, 1, 1, 2, 0]
    assert c.survival.tolist() == pytest.approx([0.875, 0.75, 0.6, 0.3, 0.3])
    assert km_median(times, events) == 6


def test_km_median_exactly_half():
    assert km_median([1, 2], [1, 1]) == 1  # S(1) = 0.5 -> median is 1
    assert km_median([], []) is None


def test_km_matches_brute_force_on_random_tied_data():
    rng = np.random.default_rng(0)
    for _ in range(200):
        n = int(rng.integers(1, 25))
        times = rng.integers(0, 6, n).astype(float)  # many ties
        events = rng.random(n) < 0.6
        c = km_curve(times, events)
        bf = brute_force_km(times, events)
        assert c.time.tolist() == sorted(bf)
        assert c.survival.tolist() == pytest.approx([bf[t] for t in c.time])
        assert km_median(times, events) == brute_force_median(times, events)


def test_km_without_censoring_equals_one_minus_ecdf():
    times = np.array([3, 1, 4, 1, 5, 9, 2, 6, 5, 3])
    c = km_curve(times, np.ones_like(times, dtype=bool))
    ecdf = [(times <= t).mean() for t in c.time]
    assert c.survival.tolist() == pytest.approx([1 - x for x in ecdf])


# ---------------------------------------------------------------- F07: eligibility

def _person(pid, *, quit=False, completed=True, attention=True, n=6, reloads=0, focus=0, eligible=True):
    rows = [{"participant_id": pid, "is_test": False, "group": "adult", "eligible": eligible,
             "completed": completed, "attention_ok": attention, "quit_early": quit, "time_capped": False,
             "quit_elapsed_s": 300.0 if quit else None, "task": "surprise", "round": None, "practice": False,
             "elapsed_s": 5.0, "hit": True, "rt_ms": 4000.0, "condition": "L1", "reloads": 0, "focus_lost": 0,
             "saw_gorilla": True, "knew_gorilla_study": False, "noticed_unusual": True,
             "education_years": 14, "effort": 4}]
    for i in range(n):
        rows.append({**rows[0], "task": "search", "round": 1 + i // 3, "elapsed_s": 60.0 + 30 * i,
                     "reloads": reloads, "focus_lost": focus, "condition": "L1" if i % 2 else "L2"})
    return rows


def _frame(rows, tmp_path):
    p = tmp_path / "trials.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return analyze.load(p)


def test_exhausted_without_final_questionnaire_stays_in(tmp_path):
    rows = (_person("complete") + _person("exhausted_no_final", quit=True, completed=None, attention=None)
            + _person("failed_attention", attention=False) + _person("ineligible", eligible=False)
            + _person("all_reloaded", reloads=1))
    df = _frame(rows, tmp_path)
    inc, table = eligibility(df)
    # Missing final questionnaire is not inattentiveness: kept everywhere relevant.
    assert "exhausted_no_final" in inc["stopping"]
    assert "exhausted_no_final" in inc["performance"]
    assert "exhausted_no_final" in inc["gorilla"]
    # An explicit wrong attention answer only affects the performance analyses.
    assert "failed_attention" not in inc["performance"]
    assert "failed_attention" in inc["stopping"]
    # Ineligible people are out everywhere; invalid trials only remove performance.
    assert all("ineligible" not in s for s in inc.values())
    assert "all_reloaded" not in inc["performance"] and "all_reloaded" in inc["stopping"]

    def n(analysis, reason):
        return int(table[(table.analysis == analysis) & (table.reason == reason)].n.iloc[0])
    assert n("performance", "excluded: wrong end-of-session attention answer") == 1
    assert n("performance", "excluded: no valid scored trials") == 1
    assert n("stopping", "kept: no final questionnaire") == 1
    assert n("stopping", "kept: wrong end-of-session attention answer") == 1
    # Reasons partition the file.
    for a in table.analysis.unique():
        excl = table[(table.analysis == a) & table.reason.str.startswith("excluded")].n.sum()
        assert excl + n(a, "included") == n(a, "in file")

    inc_keep, _ = eligibility(df, attention_policy="keep")
    assert "failed_attention" in inc_keep["performance"]


def test_old_complete_case_filter_would_have_dropped_exhausted(tmp_path):
    """The exhausted person's stop event enters the survival analysis."""
    rows = _person("a", quit=True, completed=None, attention=None) + _person("b") + _person("c") \
        + _person("d") + _person("e")
    df = _frame(rows, tmp_path)
    inc, _ = eligibility(df)
    people = analyze.stopping(df, inc["stopping"], 60)
    assert bool(people.loc["a", "quit"]) and people.loc["a", "time"] == pytest.approx(5.0)


def test_per_trial_validity_drops_only_bad_trials(tmp_path):
    rows = _person("p")
    rows[2]["reloads"] = 1
    rows[3]["focus_lost"] = 1
    df = _frame(rows, tmp_path)
    out = analyze.run(df, n_boot=0)
    assert len(out["trials"]) == 4
    assert out["included"]["performance"] == {"p"}


def test_simulated_missing_final_kept(tmp_path, capsys):
    df = simulate(seed=3, n_scale=0.15, p_missing_final=1.0)
    p = tmp_path / "sim.csv"
    df.to_csv(p, index=False)
    d = analyze.load(p)
    # As in the real export: completed is False and attention_ok is blank.
    no_final = set(d[(d.completed == False) & d.attention_ok.isna()].participant_id)  # noqa: E712
    assert no_final  # simulate produced some
    inc, _ = eligibility(d, include_test=True)
    assert no_final <= inc["stopping"] and no_final <= inc["performance"]


# ---------------------------------------------------------------- F12: library tasks

def test_library_summary_without_metrics_column():
    trials = pd.DataFrame({"participant_id": ["a", "a"], "task": ["stop_signal", "search"],
                           "condition": ["L1", "L1"], "hit": [True, True]})
    pass_table, metric_table, note = library_summary(trials)
    assert metric_table is None and "metrics" in note and "NOT accuracy" in note
    assert list(pass_table.index.get_level_values("task")) == ["stop_signal"]


def test_library_summary_uses_metrics_json():
    m1 = {"response": [1, 2], "go_accuracy": 0.9, "stop_success_rate": 0.5, "go_rt_median": 450,
          "race_check_ok": True, "ssd_trajectory": [200, 250], "ssrt": None}
    m2 = {**m1, "go_accuracy": 0.7, "race_check_ok": False}
    trials = pd.DataFrame({"participant_id": ["a", "b"], "task": ["stop_signal"] * 2,
                           "condition": ["L1", "L1"], "hit": [True, False],
                           "metrics": [json.dumps(m1), json.dumps(m2)]})
    _, table, note = library_summary(trials)
    assert note == ""
    metrics = set(table.index.get_level_values("metric"))
    assert {"go_accuracy", "stop_success_rate", "go_rt_median", "race_check_ok"} <= metrics
    assert not metrics & {"response", "ssd_trajectory", "ssrt"}
    assert table.loc[("stop_signal", "go_accuracy", "L1"), "mean_of_person_means"] == pytest.approx(0.8)
    assert table.loc[("stop_signal", "race_check_ok", "L1"), "mean_of_person_means"] == pytest.approx(0.5)


def test_library_blocks_not_in_core_accuracy(tmp_path, capsys):
    df = simulate(seed=2, n_scale=0.1, library=True, rounds=4)
    p = tmp_path / "sim.csv"
    df.to_csv(p, index=False)
    analyze.run(analyze.load(p), include_test=True, n_boot=0)
    out = capsys.readouterr().out
    section1 = out.split("1. LANGUAGE OF THE CLUE")[1].split("1b. LIBRARY TASKS")[0]
    section1b = out.split("1b. LIBRARY TASKS")[1].split("2. SURPRISE GORILLA")[0]
    assert "stroop" not in section1
    assert "stroop" in section1b and "stroop_cost_ms" in section1b and "NOT accuracy" in section1b


# ---------------------------------------------------------------- F19: change point

def _rt_frame(df):
    trials = df[df["round"].notna() & ~df.practice.astype(bool)]
    rt = analyze.correct_rts(trials.assign(hit=trials.hit.astype(bool)))
    rt["elapsed_min"] = rt.elapsed_s / 60
    return rt


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_learning_only_is_not_reported_as_fatigue_onset(seed):
    rt = _rt_frame(simulate(seed=seed, scenario="learning_only", n_scale=0.35))
    res = bend_search(rt, n_boot=100, seed=seed)
    assert res.ok
    assert res.verdict != "post_break_slowing"
    text = "\n".join(describe(res, 60))
    assert "Exploratory finding" not in text and "response times rise" not in text
    assert "No demonstrated slowing within the 60-minute session" in text or res.verdict == "post_break_speedup"


def test_true_decay_is_detected_as_exploratory_slowing():
    rt = _rt_frame(simulate(seed=1, decay_slope=0.04, decay_start=8, n_scale=0.35))
    res = bend_search(rt, n_boot=100, seed=1)
    assert res.ok and res.verdict == "post_break_slowing"
    assert res.ci["post_slope_avg"][0] > 0
    assert 4 <= res.k <= 14
    text = "\n".join(describe(res, 60))
    assert text.startswith("EXPLORATORY")


def test_positive_change_with_negative_post_slope_is_a_plateau():
    res = BendResult(ok=True, k=10, pre_slope_at_k=-0.05, change=0.03, post_slope_avg=-0.02, t_end=40,
                     ci={"k": (8, 12), "pre_slope_at_k": (-0.06, -0.04), "change": (0.01, 0.05),
                         "post_slope_avg": (-0.03, -0.01)}, n_boot=100, verdict="post_break_speedup")
    text = "\n".join(describe(res, 45))
    assert "not evidence of fatigue" in text and "rise" not in text


def test_failed_bend_search_stops_inference():
    rt = pd.DataFrame({"participant_id": ["a"] * 5, "log_rt": np.log(np.full(5, 1000.0)),
                       "elapsed_min": np.arange(1, 6, dtype=float), "condition": "L1", "task": "search"})
    res = bend_search(rt, n_boot=10)
    assert not res.ok
    text = describe(res)
    assert any("FAILED" in line for line in text)
    assert not any("slope" in line.lower() for line in text)


def test_fit_failure_and_nonconvergence_withhold_output(monkeypatch, capsys):
    data = pd.DataFrame({"participant_id": list("aabb"), "y": [1.0, 2, 3, 4], "x": [0.0, 1, 0, 1]})

    def boom(*a, **k):
        raise np.linalg.LinAlgError("Singular matrix")
    monkeypatch.setattr(analyze.smf, "mixedlm", boom)
    assert analyze.fit("y ~ x", data) is None
    assert "MODEL FAILED" in capsys.readouterr().out

    class NotConverged:
        converged = False

        def fit(self, **k):
            import warnings
            warnings.warn("fake convergence problem", RuntimeWarning)
            return self
    monkeypatch.setattr(analyze.smf, "mixedlm", lambda *a, **k: NotConverged())
    assert analyze.fit("y ~ x", data) is None
    out = capsys.readouterr().out
    assert "fake convergence problem" in out and "DID NOT CONVERGE" in out


def test_no_hardcoded_15_minute_wording(tmp_path, capsys):
    for f in ANALYSIS.glob("*.py"):
        src = f.read_text()
        assert not re.search(r"15[- ]minute", src), f
    df = simulate(seed=4, n_scale=0.1, rounds=4)
    p = tmp_path / "sim.csv"
    df.to_csv(p, index=False)
    analyze.run(analyze.load(p), include_test=True, session_limit_min=45, n_boot=20)
    out = capsys.readouterr().out
    assert "45-minute" in out and "15-minute" not in out and "60-minute" not in out


def test_fatigue_ratings_do_not_require_final_questionnaire(tmp_path, capsys):
    rows = _person("a", quit=True, completed=None, attention=None) + _person("b") + _person("c")
    df = _frame(rows, tmp_path)
    f = pd.DataFrame([{"participant_id": p, "group": "adult", "point": pt, "value": v, "elapsed_s": s}
                      for p in ("a", "b") for pt, v, s in (("baseline", 10, None), ("after_round_1", 30, 600))])
    out = analyze.run(df, fatigue_df=f, n_boot=0)
    assert out["included"]["fatigue_ratings"] == {"a", "b"}
    table = out["eligibility"]
    row = table[(table.analysis == "fatigue_ratings") & (table.reason == "excluded: no fatigue ratings")]
    assert int(row.n.iloc[0]) == 1
    assert "4. SELF-RATED FATIGUE" in capsys.readouterr().out


def test_simulated_default_dataset_runs_end_to_end(tmp_path, capsys):
    df = simulate(seed=5, n_scale=0.15, library=True, p_missing_final=0.3)
    p = tmp_path / "sim.csv"
    df.to_csv(p, index=False)
    out = analyze.run(analyze.load(p), include_test=True, n_boot=30)
    printed = capsys.readouterr().out
    assert "0. ELIGIBILITY AND MISSINGNESS" in printed and "EXPLORATORY change-point" in printed
    assert out["bend"].ok


def test_cli_on_shipped_simulated_csv():
    import subprocess
    r = subprocess.run([sys.executable, str(ANALYSIS / "analyze.py"), str(ANALYSIS / "SIMULATED_trials.csv"),
                        "--include-test", "--bootstrap", "10"], capture_output=True, text=True, timeout=600,
                       cwd=str(ANALYSIS.parent), env={**os.environ, "PYTHONWARNINGS": "ignore"})
    assert r.returncode == 0, r.stderr[-2000:]
    assert "EXPLORATORY change-point" in r.stdout and "15-minute" not in r.stdout
