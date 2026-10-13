"""Session lifecycle and raw-data integrity: hard deadline (F01), task-id length (F02),
stored version stamps (F03), complete raw data (F04), stop reasons and partial trials
(F05), atomic state changes (F08), phase and payload checks (F20), admin access (F21)."""
import csv
import io
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import config
from app import main as appmain
from app.db import FatigueRating, Participant, SessionLocal, TrialResult, now
from app.main import app
from app.plan import build_plan, load_manifest
from app.tasks import PLUGINS

MANIFEST = load_manifest()
M = {i["id"]: i for i in MANIFEST["images"]}
BG = {"group": "radiologist", "age": 45, "education_years": 22, "years_reading_images": 12,
      "native_lang": "tr", "l2_age_acquired": 20, "l1": "tr", "l1_reading": 7, "l2": "en", "l2_reading": 6}
SMALL = {"search": 2, "corsi": 2, "reading": 2, "rule": 2, "ospan": 2}


# ---------- helpers ----------

def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def pid(c):
    return c.cookies.get("pid")


def participant(c):
    with SessionLocal() as db:
        return db.get(Participant, pid(c))


def setp(c, **fields):
    with SessionLocal() as db:
        p = db.get(Participant, pid(c))
        for k, v in fields.items():
            setattr(p, k, v)
        db.commit()


def trial_rows(c):
    with SessionLocal() as db:
        return (db.query(TrialResult).filter(TrialResult.participant_id == pid(c))
                .order_by(TrialResult.trial_index, TrialResult.id).all())


def session_ctx(page):
    return json.loads(page.split("window.SESSION = ")[1].split(";</script>")[0])


def show(c):
    """Open the current trial, answering a due fatigue check-in first."""
    r = c.get("/trial")
    if r.url.path == "/fatigue":
        c.post("/fatigue", data={"point": r.url.params["point"], "value": 40})
        r = c.get("/trial")
    return r


def body_for(c, i, correct=True):
    tr = participant(c).plan[i]
    tg, task = M[tr["image_id"]]["target"], tr["task"]
    body = {"trial_index": i, "rt_ms": 1500.0, "effort": 4}
    if task in PLUGINS:
        body["response"] = PLUGINS[task].logic.example_response(tg, correct)
    elif task == "corsi":
        seq = tg["sequence"] if tg["direction"] == "forward" else tg["sequence"][::-1]
        body["response"] = seq if correct else seq[::-1]
    elif task == "reading":
        body["response"] = tg["answer"] if correct else (tg["answer"] + 1) % 3
    elif task == "rule":
        body["response"] = tg["answer"] if correct else {"A": "B", "B": "A"}[tg["answer"]]
    elif task == "ospan":
        words = tg["words"] if correct else tg["words"][::-1]
        body["response"] = {"recall": words, "sums": [sm["true"] for sm in tg["sums"]]}
    else:
        x = tg["x"] + (0 if correct else 400)
        body.update(click_x=x, click_y=tg["y"], clicks=[{"x": x, "y": tg["y"], "t_ms": 1500}])
    return body


def submit(c, i, correct=True, **extra):
    show(c)
    return c.post("/api/trial", json={**body_for(c, i, correct), **extra})


def new_session(c, mix=SMALL, rounds=2, through_surprise=True):
    c.post("/start", data={"ui_lang": "en"})
    c.post("/consent", data={"agree": "yes"})
    c.post("/background", data=BG)
    if mix is not None:
        p = participant(c)
        setp(c, plan=build_plan(p.id, p.counterbalance, "tr", "en", MANIFEST, mix=mix, rounds=rounds))
    c.post("/fatigue", data={"point": "baseline", "value": 30})
    if through_surprise:
        submit(c, 0)
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "no"})


def to_first_scored(c):
    """Answer practice trials; return the index of the first scored trial (now shown)."""
    plan = participant(c).plan
    i = participant(c).current_trial
    while not plan[i].get("round"):
        assert submit(c, i).json()["ok"]
        i += 1
    show(c)
    return i


def login(c):
    assert c.get("/admin?key=test-key").status_code == 200


# ---------- F01: hard session deadline ----------

def test_deadline_starts_at_first_scored_stimulus_and_refresh_keeps_it():
    c = TestClient(app)
    with c:
        new_session(c)
        practice_page = c.get("/trial").text
        assert session_ctx(practice_page)["remainingMs"] is None  # practice is outside the cap
        assert participant(c).deadline_at is None
        i = to_first_scored(c)
        p = participant(c)
        assert p.deadline_at is not None and p.cap_started_at is not None
        assert abs((appmain._utc(p.deadline_at) - appmain._utc(p.cap_started_at)).total_seconds()
                   - config.SESSION_LIMIT_MIN * 60) < 1
        first = session_ctx(show(c).text)["remainingMs"]
        time.sleep(0.3)
        again = session_ctx(show(c).text)["remainingMs"]  # refresh
        assert participant(c).deadline_at == p.deadline_at  # never renewed
        assert again <= first - 250
        assert participant(c).current_trial == i


def test_every_timed_screen_runs_on_the_same_deadline():
    """Start/encoding/recall (Corsi, operation span), search, reading, rule, plugin and
    the effort rating (same page) and fatigue check-ins all get the stored deadline."""
    c = TestClient(app)
    with c:
        new_session(c, mix={**SMALL, "feature_search": 2})
        i = to_first_scored(c)
        deadline = appmain._utc(participant(c).deadline_at)
        plan = participant(c).plan
        seen = set()
        while i < len(plan):
            r = c.get("/trial")
            kind = "fatigue" if r.url.path == "/fatigue" else plan[i]["task"]
            ctx = session_ctx(r.text)
            assert ctx["remainingMs"] is not None, kind
            implied = now() + timedelta(milliseconds=ctx["remainingMs"])
            assert abs((implied - deadline).total_seconds()) < 2, kind
            assert "/static/session.js" in r.text and 'id="withdraw"' in r.text, kind
            seen.add(kind)
            if kind == "fatigue":
                c.post("/fatigue", data={"point": r.url.params["point"], "value": 40})
                continue
            c.post("/api/trial", json=body_for(c, i))
            i += 1
        assert seen >= {"search", "corsi", "reading", "rule", "ospan", "feature_search", "fatigue"}


def test_late_trial_is_kept_flagged_and_ends_the_session(monkeypatch):
    monkeypatch.setattr(config, "SESSION_LIMIT_MIN", 0.005)  # 0.3 s
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        time.sleep(0.5)
        res = c.post("/api/trial", json=body_for(c, i)).json()
        assert res["ok"] and res["late"] and res["next"] == "/final"
        row = trial_rows(c)[-1]
        assert row.trial_index == i and row.late is True and row.partial is False
        p = participant(c)
        assert p.stop_reason == "time_cap" and p.time_capped and p.quit_trial == i + 1
        assert c.get("/trial").url.path in ("/final", "/retention")
        login(c)
        mine = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == p.id]
        assert mine[-1]["late"] == "True" and mine[0]["late"] == "False"
        assert {r["session_end"] for r in mine} == {"time_cap"}


def test_late_fatigue_rating_is_kept_flagged(monkeypatch):
    c = TestClient(app)
    with c:
        new_session(c, mix={"search": 2}, rounds=2)
        i = to_first_scored(c)
        submit(c, i)
        submit(c, i + 1)
        r = c.get("/trial")
        assert r.url.path == "/fatigue"  # round 1 done
        setp(c, deadline_at=now() - timedelta(seconds=1))
        c.post("/fatigue", data={"point": r.url.params["point"], "value": 70})
        with SessionLocal() as db:
            f = db.query(FatigueRating).filter_by(participant_id=pid(c), point="after_round_1").one()
            assert f.late is True and f.value == 70
        assert participant(c).stop_reason == "time_cap"


def test_time_cap_stop_keeps_the_partial_trial():
    c = TestClient(app)
    with c:
        new_session(c, mix={"search": 2})
        i = to_first_scored(c)
        part = {"clicks": [{"x": 5, "y": 5, "t_ms": 400}], "rt_ms": 900, "false_clicks": 1}
        early = c.post("/api/stop", json={"trial_index": i, "reason": "time_cap", "partial": part})
        assert early.status_code == 409 and participant(c).stop_reason is None  # clock not up yet
        setp(c, deadline_at=now() - timedelta(milliseconds=10))
        res = c.post("/api/stop", json={"trial_index": i, "reason": "time_cap", "partial": part}).json()
        assert res["reason"] == "time_cap" and res["next"] == "/final"
        row = trial_rows(c)[-1]
        assert row.trial_index == i and row.partial and not row.hit and row.rt_ms == 900
        assert row.wrong_clicks == 1 and row.first_click_correct is False
        p = participant(c)
        assert p.stopped_at is not None and p.stop_elapsed_s is not None
        assert "first scored stimulus" in p.stop_clock_basis


# ---------- F05: stop reasons, partial trials, idempotency ----------

@pytest.mark.parametrize("reason", ["exhausted", "withdrawn", "technical_failure"])
def test_each_stop_reason_is_recorded_once_with_its_partial_trial(reason):
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        partial = {"response": [3, 1], "rt_ms": 700}
        res = c.post("/api/stop", json={"trial_index": i, "reason": reason, "partial": partial}).json()
        assert res["ok"] and res["reason"] == reason and not res["already"]
        first = participant(c)
        assert first.stop_reason == reason and first.quit_trial == i
        assert first.quit_early is (reason == "exhausted")
        again = c.post("/api/stop", json={"trial_index": i, "reason": "withdrawn"}).json()
        assert again["already"] is True
        p = participant(c)
        assert (p.stop_reason, p.stopped_at) == (first.stop_reason, first.stopped_at)
        kept = [r for r in trial_rows(c) if r.trial_index == i]
        assert len(kept) == 1 and kept[0].partial and json.loads(kept[0].response) == [3, 1]


def test_stale_tab_stop_is_recorded_as_stale():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        res = c.post("/api/stop", json={"trial_index": i - 1, "reason": "withdrawn",
                                        "partial": {"response": "x"}}).json()
        p = participant(c)
        assert res["reason"] == "stale_request" and p.stop_requested == "withdrawn"
        assert all(r.trial_index != i for r in trial_rows(c))  # no partial attached to the wrong trial


def test_old_quit_endpoint_still_means_exhausted():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        assert c.post("/api/quit", json={"trial_index": i}).json()["next"] == "/final"
        assert participant(c).stop_reason == "exhausted"


def test_zero_scored_trials_disconnect_and_skipped_final_keep_their_records():
    login_client = TestClient(app)
    login(login_client)
    withdrew = TestClient(app)
    with withdrew:
        new_session(withdrew, through_surprise=False)
        withdrew.get("/trial")
        assert withdrew.post("/api/stop", json={"trial_index": 0, "reason": "withdrawn"}).json()["ok"]
        final = withdrew.get("/final")
        assert final.url.path == "/final" and 'name="skip"' in final.text and " required" not in final.text
        withdrew.post("/final", data={"skip": "1"})
        p = participant(withdrew)
        assert p.final_skipped and not p.completed and p.stop_reason == "withdrawn"
    gone = TestClient(app)
    with gone:
        new_session(gone)  # then the page is closed: nothing more arrives
    sessions = {r["participant_id"]: r for r in rows(login_client.get("/admin/sessions.csv").text)}
    a, b = sessions[pid(withdrew)], sessions[pid(gone)]
    assert a["session_end"] == "withdrawn" and a["n_trials_recorded"] == "0" and a["stopped_at"]
    assert a["final_skipped"] == "True"
    assert b["session_end"] == "incomplete_unknown"


def test_optional_final_answers_after_a_stop():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        c.post("/api/stop", json={"trial_index": i, "reason": "exhausted"})
        c.post("/final", data={"fatigue": 90})  # only one answer given
        p = participant(c)
        assert p.completed and p.overall_difficulty is None and p.attention_ok is None
        assert p.stop_reason == "exhausted"


# ---------- F02: long task ids ----------

def _insert_every_plugin(session_factory):
    """One stored response per registered task id, each longer than the old 200-char cap."""
    with session_factory() as db:
        p = Participant(is_test=True, consented=True, group="adult")
        db.add(p)
        db.flush()
        for k, task_id in enumerate(sorted(PLUGINS)):
            db.add(TrialResult(participant_id=p.id, trial_index=k, task=task_id, image_id=f"{task_id}_00",
                               clue_lang="en", condition="L1", practice=False,
                               response=json.dumps({"events": [{"rt": 500 + n} for n in range(40)]})))
        db.commit()
        return p.id


def _check_export_has_every_plugin(client, participant_id):
    mine = [r for r in rows(client.get("/admin/export.csv").text) if r["participant_id"] == participant_id]
    assert {r["task"] for r in mine} == set(PLUGINS)
    longest = max(PLUGINS, key=len)
    assert any(r["task"] == longest for r in mine) and len(longest) > 10
    assert all(len(json.loads(r["response"])["events"]) == 40 for r in mine)


def test_every_plugin_id_is_stored_and_exported_whole():
    c = TestClient(app)
    with c:
        login(c)
        _check_export_has_every_plugin(c, _insert_every_plugin(SessionLocal))


# ---------- F03: stored version stamps ----------

def test_exported_versions_are_the_stored_ones(monkeypatch):
    c = TestClient(app)
    with c:
        new_session(c)
        login(c)
        before = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == pid(c)]
        assert before and all(r["study_version"] == config.STUDY_VERSION for r in before)
        assert all(r["translation_version"] not in ("", "unknown") for r in before)
        assert all(r["clue_text"] for r in before if r["task"] != "reading")  # rendered clue kept
        # Change the current study version, translation files and stimuli afterwards.
        monkeypatch.setattr(config, "STUDY_VERSION", "2099.01.01-changed")
        monkeypatch.setattr(config, "SOFTWARE_COMMIT", "deadbeef")
        monkeypatch.setitem(appmain.LOCALE_HASH, "tr", "0000000000")
        monkeypatch.setitem(appmain.LOCALE_HASH, "en", "1111111111")
        monkeypatch.setattr(appmain, "manifest_version", lambda: "changed")
        after = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == pid(c)]
        cols = ["study_version", "stimuli_version", "translation_version", "software_commit",
                "task_text_version"]
        assert [[r[k] for k in cols] for r in after] == [[r[k] for k in cols] for r in before]
        assert participant(c).versions["study_version"] != "2099.01.01-changed"
        # A row from before stamps were stored says "unknown" instead of today's values.
        with SessionLocal() as db:
            db.add(TrialResult(participant_id=pid(c), trial_index=999, task="search", image_id="search_00",
                               clue_lang="en", condition="L1"))
            db.commit()
        legacy = [r for r in rows(c.get("/admin/export.csv").text) if r["trial_index"] == "999"][0]
        assert legacy["study_version"] == legacy["translation_version"] == "unknown"


# ---------- F04: complete raw data ----------

def test_wrong_first_click_and_every_rt_are_kept():
    c = TestClient(app)
    with c:
        new_session(c, mix={"search": 2})
        i = to_first_scored(c)
        tg = M[participant(c).plan[i]["image_id"]]["target"]
        clicks = [{"x": tg["x"] + 300, "y": tg["y"], "t_ms": 640}, {"x": tg["x"] + 280, "y": tg["y"], "t_ms": 910},
                  {"x": tg["x"], "y": tg["y"], "t_ms": 1730}]
        c.post("/api/trial", json={"trial_index": i, "rt_ms": 1730, "click_x": tg["x"], "click_y": tg["y"],
                                   "clicks": clicks, "effort": 3})
        show(c)
        miss = {"trial_index": i + 1, "rt_ms": 2222, "click_x": 1, "click_y": 1,
                "clicks": [{"x": 1, "y": 1, "t_ms": 2222}], "effort": 5}
        assert c.post("/api/trial", json=miss).json()["hit"] is False
        login(c)
        mine = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == pid(c)]
        hit, wrong = mine[i], mine[i + 1]
        assert (hit["first_click_ms"], hit["first_click_correct"], hit["wrong_clicks"]) == ("640.0", "False", "2")
        assert hit["hit"] == "True" and hit["rt_ms"] == "1730.0" and len(json.loads(hit["response"])["clicks"]) == 3
        assert wrong["hit"] == "False" and wrong["rt_ms"] == "2222.0"  # RT kept on a miss


def test_plugin_scores_reproduce_from_the_export_alone():
    c = TestClient(app)
    with c:
        new_session(c, mix={"feature_search": 2})
        i = to_first_scored(c)
        body = body_for(c, i, correct=False)
        body["timing"] = {"instr_ms": 4000, "start_ms": 4000, "first_response_ms": 4700, "complete_ms": 30000}
        c.post("/api/trial", json=body)
        login(c)
        row = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == pid(c)][i]
        response = json.loads(row["response"])
        assert len(row["response"]) > 200 and response == body["response"]
        rescored = PLUGINS["feature_search"].logic.score(M[row["image_id"]]["target"], response)
        assert str(bool(rescored["hit"])) == row["hit"]
        metrics = json.loads(row["metrics"])
        assert all(metrics[k] == v for k, v in rescored["metrics"].items())
        assert json.loads(row["timing"])["instr_ms"] == 4000


# ---------- F08: atomic state changes ----------

def test_repeated_submission_is_stored_once():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        body = body_for(c, i)
        first = c.post("/api/trial", json=body).json()
        second = c.post("/api/trial", json=body).json()
        assert second["duplicate"] and second["hit"] == first["hit"] and second["next"] == first["next"]
        assert sum(r.trial_index == i for r in trial_rows(c)) == 1
        assert participant(c).current_trial == i + 1


def test_concurrent_duplicate_submissions_make_one_row_and_one_transition():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        body = body_for(c, i)
        with ThreadPoolExecutor(6) as pool:
            results = list(pool.map(lambda _: c.post("/api/trial", json=body), range(6)))
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
        assert sum(r.trial_index == i for r in trial_rows(c)) == 1
        assert participant(c).current_trial == i + 1


def test_setup_cannot_be_reposted_once_a_plan_exists():
    c = TestClient(app)
    with c:
        new_session(c)
        before = participant(c)
        r = c.post("/background", data={**BG, "l1": "ja", "l2": "es", "group": "adult"})
        after = participant(c)
        assert r.url.path != "/background"
        assert (after.plan, after.counterbalance, after.l1, after.group) == \
            (before.plan, before.counterbalance, before.l1, before.group)
        assert c.get("/background").url.path != "/background"


def test_allocation_pools_are_separate_and_distinct():
    with SessionLocal() as db:
        got = [appmain.allocate(db, "real:test-pool", 0) for _ in range(5)]
        test_pool = appmain.allocate(db, "test:test-pool", 0)
        db.commit()
    assert got == [0, 1, 2, 3, 4] and test_pool == 0


def test_unique_trial_index_and_legacy_duplicates_are_left_alone(tmp_path, caplog):
    from sqlalchemy import inspect, text
    from app.db import init_db, make_engine
    assert any(ix["name"] == "uq_trial_results_participant_trial" and ix["unique"]
               for ix in inspect(SessionLocal().get_bind()).get_indexes("trial_results"))
    eng = make_engine(f"sqlite:///{tmp_path}/legacy.db")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE participants (id VARCHAR(36) PRIMARY KEY, \"group\" VARCHAR(20))"))
        conn.execute(text("CREATE TABLE trial_results (id INTEGER PRIMARY KEY, participant_id VARCHAR(36), "
                          "trial_index INTEGER, task VARCHAR(10), response VARCHAR(200))"))
        conn.execute(text("INSERT INTO participants (id) VALUES ('p1')"))
        conn.execute(text("INSERT INTO trial_results (participant_id, trial_index, task) VALUES "
                          "('p1', 3, 'search'), ('p1', 3, 'search')"))
    with caplog.at_level(logging.WARNING):
        init_db(eng)
        init_db(eng)  # idempotent
    assert "not added" in caplog.text
    assert not any(ix["name"] == "uq_trial_results_participant_trial" for ix in inspect(eng).get_indexes("trial_results"))
    with eng.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM trial_results")).scalar() == 2


# ---------- F20: phase and payload checks ----------

def test_out_of_phase_requests_change_nothing():
    c = TestClient(app)
    with c:
        c.post("/start", data={"ui_lang": "en"})
        assert c.post("/api/trial", json={"trial_index": 0}).json()["next"] == "/consent"
        assert c.post("/background", data=BG).url.path == "/consent"
        assert participant(c).plan is None
        c.post("/consent", data={"agree": "yes"})
        c.post("/background", data=BG)
        assert c.post("/notice", data={"noticed": "yes"}).url.path != "/notice2"
        assert participant(c).noticed_unusual is None
        res = c.post("/api/trial", json={"trial_index": 0, "rt_ms": 1})
        assert res.status_code == 409 and res.json()["next"] == "/fatigue?point=baseline"
        assert c.post("/final", data={"difficulty": 5, "attention": "car", "fatigue": 5}).url.path != "/debrief"
        p = participant(c)
        assert not p.completed and trial_rows(c) == []


@pytest.mark.parametrize("bad", [{"rt_ms": -5}, {"rt_ms": 1e12}, {"click_x": 1e9},
                                 {"clicks": [{"x": 1, "y": 1, "t_ms": -1}]}, {"effort": 12}])
def test_invalid_numbers_are_rejected(bad):
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        assert c.post("/api/trial", json={**body_for(c, i), **bad}).status_code == 422
        assert all(r.trial_index != i for r in trial_rows(c))


def test_non_finite_numbers_are_rejected():
    c = TestClient(app)
    with c:
        new_session(c)
        i = to_first_scored(c)
        for raw in ('{"trial_index": %d, "rt_ms": NaN}' % i,
                    '{"trial_index": %d, "response": [1, Infinity]}' % i):
            res = c.post("/api/trial", content=raw, headers={"Content-Type": "application/json"})
            assert res.status_code == 422, raw
        assert all(r.trial_index != i for r in trial_rows(c))


def test_age_rules():
    for age, l2_age, ok in ((15, 5, False), (16, 5, True), (30, 31, False)):
        c = TestClient(app)
        with c:
            c.post("/start", data={"ui_lang": "en"})
            c.post("/consent", data={"agree": "yes"})
            r = c.post("/background", data={**BG, "age": age, "l2_age_acquired": l2_age})
            assert (participant(c).plan is not None) is ok, (age, l2_age, r.status_code)


# ---------- F21: admin access ----------

def test_admin_key_only_logs_in_and_never_appears_in_links():
    c = TestClient(app)
    with c:
        assert c.get("/admin/export.csv").status_code == 403  # anonymous
        assert "password" in c.get("/admin").text  # login form, no data
        r = c.get("/admin?key=test-key", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/admin"
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie and "test-key" not in cookie
        page = c.get("/admin").text
        assert "key=" not in page and "/admin/export.csv" in page
        assert c.get("/admin/export.csv").status_code == 200
        assert c.get("/admin/export.csv?key=wrong").status_code == 403
        assert c.post("/admin/login", data={"key": "wrong"}).status_code == 403


def test_public_admin_cookie_is_secure(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_DEPLOYMENT", True)
    r = TestClient(app).get("/admin?key=test-key", follow_redirects=False)
    assert "secure" in r.headers["set-cookie"].lower()


@pytest.mark.parametrize("env", [{"PUBLIC_DEPLOYMENT": "1"}, {"IRB_APPROVED": "1"},
                                 {"PUBLIC_DEPLOYMENT": "1", "ADMIN_KEY": "change-me"}])
def test_public_deployment_refuses_the_default_admin_key(env):
    base = {k: v for k, v in os.environ.items() if k not in ("ADMIN_KEY", "PUBLIC_DEPLOYMENT", "IRB_APPROVED")}
    r = subprocess.run([sys.executable, "-c", "import app.config"], env={**base, **env},
                       capture_output=True, text=True)
    assert r.returncode != 0 and "ADMIN_KEY" in r.stderr
    ok = subprocess.run([sys.executable, "-c", "import app.config"],
                        env={**base, **env, "ADMIN_KEY": "a-long-random-test-value"}, capture_output=True)
    assert ok.returncode == 0
