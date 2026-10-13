"""Adversarial scoring fixtures for every library task (review F12/F14/F24).

Runs tools/adversarial_check.py over all tasks (impossible / non-finite / negative / late
times, malformed and oversized payloads, wrong types at every level, missing and extra
fields) and checks a few acceptance fixtures directly. Run with:  pytest -q tests/test_adversarial.py
"""
import copy
import json
import math
import random
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import adversarial_check as harness  # noqa: E402
from app.tasks import LOAD_ERRORS, PLUGINS  # noqa: E402
from app.tasks import _guard as G  # noqa: E402

TASK_IDS = sorted(PLUGINS, key=lambda t: PLUGINS[t].folder.name)


def _items(task_id, n=4, seed=3):
    logic = PLUGINS[task_id].logic

    def save_image(name, img):
        return f"{task_id}_{name}.png"   # pictures are not needed for scoring
    return [{k: v for k, v in it.items() if k != "file"} for it in logic.generate(random.Random(seed), n, save_image)]


def test_all_tasks_load():
    assert not LOAD_ERRORS, LOAD_ERRORS
    assert len(PLUGINS) == 64, sorted(PLUGINS)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_adversarial_harness(task_id):
    """Every rule of tools/adversarial_check.py holds for this task."""
    fails = harness.Checker(task_id, PLUGINS[task_id]).run(2)
    assert not fails, "\n".join(fails)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_examples_hit_and_miss(task_id):
    """example_response(correct=True) is a clean hit and correct=False a miss, on fresh items."""
    logic = PLUGINS[task_id].logic
    for item in _items(task_id):
        good = logic.score(copy.deepcopy(item), logic.example_response(copy.deepcopy(item), True))
        bad = logic.score(copy.deepcopy(item), logic.example_response(copy.deepcopy(item), False))
        assert good["hit"] is True and good["metrics"]["flags"] == [], good["metrics"].get("flags")
        assert good["metrics"]["invalid_events"] == 0
        assert bad["hit"] is False
        json.dumps(good, allow_nan=False)
        json.dumps(bad, allow_nan=False)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_timing_declared(task_id):
    logic = PLUGINS[task_id].logic
    assert logic.TIMING in ("window", "limit", "untimed")
    if logic.TIMING == "window":
        assert G.is_num(logic.WINDOW_MS) and logic.WINDOW_MS > 0
    if logic.TIMING == "limit":
        assert G.is_num(logic.LIMIT_MS) and logic.LIMIT_MS > 0


def test_stop_signal_impossible_rts_fixture():
    """F14: replacing every keypress RT of a correct stop-signal response with 999999 must
    not give a hit, a go accuracy above 0, or a clean result."""
    logic = PLUGINS["stop_signal"].logic
    item = _items("stop_signal", 2)[0]
    resp = logic.example_response(item, True)
    for ev in resp["events"]:
        if ev["rt"] is not None:
            ev["rt"] = 999999
    res = logic.score(item, resp)
    m = res["metrics"]
    assert res["hit"] is False
    assert m["go_accuracy"] == 0.0 and m["go_rt_n"] == 0
    assert "impossible_rt" in m["flags"] and m["invalid_events"] > 0
    # malformed stop events never become successful inhibition
    assert m["stop_successes"] == sum(1 for e in m["events"] if e["type"] == "stop" and e["outcome"] == "stopped")
    assert all(e["outcome"] != "stopped" for e in m["events"] if e["type"] == "stop" and e["status"] == G.INVALID)


def test_stop_signal_reports_go_and_stopping_separately():
    logic = PLUGINS["stop_signal"].logic
    item = _items("stop_signal", 2)[0]
    m = logic.score(item, logic.example_response(item, True))["metrics"]
    for key in ("go_accuracy", "go_omissions", "go_choice_errors", "go_rt_median", "stop_success_rate",
                "stop_successes", "stop_failures", "signal_respond_rt_mean", "ssd_trajectory"):
        assert key in m
    assert m["go_accuracy"] == 1.0 and m["stop_success_rate"] == 0.5
    assert {e["type"] for e in m["events"]} == {"go", "stop"} and len(m["events"]) == len(item["events"])
    # a late go press is not correct, an anticipation neither, and a stop with a key is a failed stop
    resp = logic.example_response(item, True)
    go = [k for k, e in enumerate(item["events"]) if not e["stop"]]
    resp["events"][go[0]]["rt"] = 1500
    resp["events"][go[1]]["rt"] = 40
    m2 = logic.score(item, resp)["metrics"]
    assert m2["go_correct"] == len(go) - 2 and m2["go_late"] == 1 and m2["go_anticipations"] == 1
    assert "late_rt" in m2["flags"]


@pytest.mark.parametrize("task_id,conds", [("stroop", ("congruent", "incongruent")),
                                           ("flanker", ("congruent", "incongruent")),
                                           ("simon", ("compatible", "incompatible"))])
def test_interference_tasks_report_condition_events(task_id, conds):
    """F12: a Stroop-type export carries congruent/incongruent event-level measures."""
    logic = PLUGINS[task_id].logic
    item = _items(task_id, 2)[0]
    m = logic.score(item, logic.example_response(item, True))["metrics"]
    text = json.dumps(m)
    for c in conds:
        assert c in text
    assert isinstance(m.get("events"), list) and len(m["events"]) == len(item["displays"])
    assert all("status" in e and "correct" in e and "rt" in e for e in m["events"])


def test_guard_time_classification():
    a = G.Audit(ceiling_ms=10000)
    assert a.time(None)[0] == G.ABSENT
    assert a.time(450, window=1000) == (G.TIMELY, 450.0)
    assert a.time(40, window=1000)[0] == G.ANTICIPATORY
    assert a.time(1200, window=1000)[0] == G.LATE
    assert a.time(1020, window=1000, slack=50)[0] == G.TIMELY
    for bad in (-5, math.nan, math.inf, -math.inf, "450", True, [], {}, 999999):
        assert a.time(bad, window=1000)[0] == G.INVALID, bad
    assert a.invalid_events == 9
    assert {"invalid_rt", "impossible_rt", "late_rt", "anticipatory_rt"} <= set(a.flags)


def test_guard_keyed_events():
    a = G.Audit()
    keys = ("left", "right")
    assert a.keyed({"key": None, "rt": None}, keys, window=1000)[0] == G.ABSENT
    assert a.keyed({"key": "left", "rt": 500}, keys, window=1000) == (G.TIMELY, "left", 500.0)
    assert a.keyed({"key": "left", "rt": None}, keys, window=1000)[0] == G.INVALID      # key without rt
    assert a.keyed({"key": None, "rt": 500}, keys, window=1000)[0] == G.INVALID         # rt without key
    assert a.keyed({"key": "up", "rt": 500}, keys, window=1000)[0] == G.INVALID         # unknown key
    assert a.keyed({"key": "left"}, keys, window=1000)[0] == G.INVALID                  # missing field
    assert a.keyed(None, keys, window=1000)[0] == G.INVALID
    assert a.keyed(G.MISSING, keys, window=1000)[0] == G.INVALID
    res = a.finish(False, 0, {})
    assert res["metrics"]["event_status"]["invalid"] == 6
    assert res["metrics"]["invalid_events"] == 6


def test_harness_catches_a_naive_scorer():
    """The harness must fail the pre-fix style of scorer (key equality, RT ignored)."""
    real = PLUGINS["stop_signal"].logic

    def naive_score(item, response):
        evs = response.get("events") if isinstance(response, dict) else None
        if not isinstance(evs, list):
            return {"hit": False, "errors": 0, "metrics": {"flags": [], "invalid_events": 0}}
        go_ok = sum(1 for e, r in zip(item["events"], evs)
                    if not e["stop"] and isinstance(r, dict) and r.get("key") == e["dir"])
        stops = sum(1 for e, r in zip(item["events"], evs)
                    if e["stop"] and isinstance(r, dict) and r.get("key") is None)
        hit = go_ok / 24 >= 0.8 and stops / 8 >= 0.25
        return {"hit": hit, "errors": 0, "metrics": {"flags": [], "invalid_events": 0}}

    fake_logic = types.SimpleNamespace(generate=real.generate, example_response=real.example_response,
                                       score=naive_score, TIMING="window", WINDOW_MS=real.WINDOW_MS)
    fake = types.SimpleNamespace(logic=fake_logic, timeout_ms=PLUGINS["stop_signal"].timeout_ms)
    fails = harness.Checker("stop_signal", fake).run(1)
    assert any(f.startswith("R3") and "999999" in f for f in fails), fails
