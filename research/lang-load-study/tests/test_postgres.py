"""PostgreSQL integration (the production database type). Skipped unless TEST_DATABASE_URL
points at a PostgreSQL server, e.g.

    TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/postgres pytest -q tests/test_postgres.py

Every test works inside its own new schema, which is dropped afterwards, so nothing
else in that database is touched."""
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.db import Participant, TrialResult, init_db, make_engine
from app.main import allocate, app, get_db
from app.plan import build_plan, load_manifest
from app.tasks import PLUGINS

from test_lifecycle import _check_export_has_every_plugin, _insert_every_plugin, rows

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL or not URL.startswith("postgresql"),
                                reason="set TEST_DATABASE_URL to a PostgreSQL URL to run")


@pytest.fixture
def pg():
    """An engine whose search_path is a fresh, private schema."""
    schema = f"t_{uuid.uuid4().hex[:12]}"
    admin = make_engine(URL)
    with admin.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    eng = make_engine(URL, options=f"-csearch_path={schema}")
    try:
        yield eng
    finally:
        eng.dispose()
        with admin.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


@pytest.fixture
def client_on(pg):
    """The app with its database dependency pointed at the private schema."""
    init_db(pg)
    factory = sessionmaker(bind=pg, expire_on_commit=False)

    def db():
        s = factory()
        try:
            yield s
        finally:
            s.close()
    app.dependency_overrides[get_db] = db
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_db, None)


LEGACY = [
    """CREATE TABLE participants (id VARCHAR(36) PRIMARY KEY, created_at TIMESTAMPTZ, is_test BOOLEAN,
       consented BOOLEAN, ui_lang VARCHAR(5), "group" VARCHAR(20), plan JSON, current_trial INTEGER)""",
    """CREATE TABLE trial_results (id SERIAL PRIMARY KEY, participant_id VARCHAR(36) REFERENCES participants(id),
       created_at TIMESTAMPTZ, trial_index INTEGER, task VARCHAR(10), image_id VARCHAR(40),
       target_object VARCHAR(20), clue_lang VARCHAR(5), condition VARCHAR(2), practice BOOLEAN,
       rt_ms FLOAT, hit BOOLEAN, response VARCHAR(200), metrics TEXT)""",
    """CREATE TABLE fatigue_ratings (id SERIAL PRIMARY KEY, participant_id VARCHAR(36) REFERENCES participants(id),
       created_at TIMESTAMPTZ, point VARCHAR(20), value INTEGER, elapsed_s FLOAT)""",
    "INSERT INTO participants (id, is_test, consented, \"group\", current_trial) VALUES ('legacy-1', true, true, 'adult', 2)",
    """INSERT INTO trial_results (participant_id, trial_index, task, image_id, clue_lang, condition, practice,
       rt_ms, hit, response) VALUES ('legacy-1', 0, 'surprise', 'surprise', 'en', 'L1', false, 812.5, true, '[1, 2]')""",
    "INSERT INTO fatigue_ratings (participant_id, point, value) VALUES ('legacy-1', 'baseline', 35)",
]


def _columns(eng, table):
    return {c["name"]: c["type"] for c in inspect(eng).get_columns(table)}


def test_old_schema_is_widened_in_place_and_data_kept(pg):
    with pg.begin() as conn:
        for stmt in LEGACY:
            conn.execute(text(stmt))
    init_db(pg)
    init_db(pg)  # a second start-up changes nothing
    cols = _columns(pg, "trial_results")
    assert cols["task"].length == 64 and cols["image_id"].length == 64
    assert getattr(cols["response"], "length", None) is None  # TEXT
    assert _columns(pg, "fatigue_ratings")["point"].length == 32
    assert any(ix["name"] == "uq_trial_results_participant_trial" and ix["unique"]
               for ix in inspect(pg).get_indexes("trial_results"))
    with pg.connect() as conn:
        row = conn.execute(text("SELECT task, rt_ms, hit, response FROM trial_results")).one()
        assert tuple(row) == ("surprise", 812.5, True, "[1, 2]")
        assert conn.execute(text("SELECT value FROM fatigue_ratings")).scalar() == 35
        assert conn.execute(text("SELECT current_trial FROM participants")).scalar() == 2


def test_duplicate_rows_block_the_unique_index_but_are_kept(pg, caplog):
    with pg.begin() as conn:
        for stmt in LEGACY:
            conn.execute(text(stmt))
        conn.execute(text("INSERT INTO trial_results (participant_id, trial_index, task, image_id, clue_lang, "
                          "condition) VALUES ('legacy-1', 0, 'surprise', 'surprise', 'en', 'L1')"))
    with caplog.at_level(logging.WARNING):
        init_db(pg)
    assert "not added" in caplog.text
    assert not any(ix["name"] == "uq_trial_results_participant_trial" for ix in inspect(pg).get_indexes("trial_results"))
    with pg.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM trial_results")).scalar() == 2


def test_every_plugin_id_round_trips_on_postgres(client_on):
    c = TestClient(app)
    with c:
        assert c.get("/admin?key=test-key").status_code == 200
        _check_export_has_every_plugin(c, _insert_every_plugin(client_on))


def test_longest_task_id_through_the_api(client_on):
    """A full submit of the longest library task id, scored and exported, on PostgreSQL."""
    longest = max(PLUGINS, key=len)
    manifest = load_manifest()
    c = TestClient(app)
    with c:
        c.post("/start", data={"ui_lang": "en"})
        pid = c.cookies.get("pid")
        with client_on() as db:
            p = db.get(Participant, pid)
            p.consented, p.l1, p.l2, p.group = True, "en", "tr", "adult"
            p.plan = build_plan(pid, 0, "en", "tr", manifest, mix={longest: 2}, rounds=1)
            p.current_trial, p.noticed_unusual, p.saw_gorilla = 1, False, False
            db.commit()
        c.post("/fatigue", data={"point": "baseline", "value": 20})
        page = c.get("/trial")
        assert f"/taskjs/{longest}.js" in page.text
        with client_on() as db:
            image_id = db.get(Participant, pid).plan[1]["image_id"]
        tg = next(i for i in manifest["images"] if i["id"] == image_id)["target"]
        response = PLUGINS[longest].logic.example_response(tg, True)
        res = c.post("/api/trial", json={"trial_index": 1, "response": response, "rt_ms": 4000, "effort": 5})
        assert res.status_code == 200 and res.json()["hit"] is True
        assert c.post("/api/trial", json={"trial_index": 1, "response": response}).json()["duplicate"]
        assert c.get("/admin?key=test-key").status_code == 200
        mine = [r for r in rows(c.get("/admin/export.csv").text) if r["participant_id"] == pid]
        assert [r["task"] for r in mine] == [longest] and json.loads(mine[0]["response"]) == response


def test_concurrent_allocations_are_distinct(client_on):
    def one(_):
        with client_on() as db:
            n = allocate(db, "real:pg-test", 0)
            db.commit()
            return n
    with ThreadPoolExecutor(8) as pool:
        got = sorted(pool.map(one, range(16)))
    assert got == list(range(16))


def test_concurrent_duplicate_submits_store_one_row(client_on):
    manifest = load_manifest()
    c = TestClient(app)
    with c:
        c.post("/start", data={"ui_lang": "en"})
        pid = c.cookies.get("pid")
        with client_on() as db:
            p = db.get(Participant, pid)
            p.consented, p.l1, p.l2 = True, "en", "tr"
            p.plan = build_plan(pid, 0, "en", "tr", manifest, mix={"search": 2}, rounds=1)
            db.commit()
        c.post("/fatigue", data={"point": "baseline", "value": 20})
        c.get("/trial")
        tg = next(i for i in manifest["images"] if i["id"] == "surprise")["target"]
        body = {"trial_index": 0, "click_x": tg["x"], "click_y": tg["y"], "rt_ms": 900, "effort": 2}
        with ThreadPoolExecutor(6) as pool:
            results = list(pool.map(lambda _: c.post("/api/trial", json=body), range(6)))
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
        with client_on() as db:
            assert db.query(TrialResult).filter_by(participant_id=pid).count() == 1
            assert db.get(Participant, pid).current_trial == 1
