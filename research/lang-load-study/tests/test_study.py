"""Run with:  pytest -q"""
import os
import tempfile

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
os.environ["ADMIN_KEY"] = "test-key"

from collections import Counter  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.clues import make_clue  # noqa: E402
from app.plan import build_plan, load_manifest  # noqa: E402
from app.main import app  # noqa: E402


def test_plan_order_balance_and_counterbalance():
    m = load_manifest()
    a = build_plan("p-a", 0, "en", "tr", m)
    b = build_plan("p-b", 1, "en", "tr", m)
    # Surprise first, then one practice per task, all before any scored trial
    assert a[0]["task"] == "surprise" and a[0]["condition"] == "L1"
    assert [t["practice"] for t in a[1:3]] == [True, True]
    scored = [t for t in a if t["round"]]
    assert len(scored) == 96
    # Every round has the same mix: per task, 2 L1 and 2 L2 clues
    for r in range(1, 13):
        rnd = [t for t in scored if t["round"] == r]
        assert Counter((t["task"], t["condition"]) for t in rnd) == {
            ("search", "L1"): 2, ("search", "L2"): 2, ("scan", "L1"): 2, ("scan", "L2"): 2}
    # Counterbalance flips which images get which language
    cond_a = {t["image_id"]: t["condition"] for t in scored}
    cond_b = {t["image_id"]: t["condition"] for t in b if t["round"]}
    assert all(cond_a[k] != cond_b[k] for k in cond_a)


def test_surprise_language_counterbalanced():
    m = load_manifest()
    assert build_plan("x", 0, "en", "tr", m)[0]["condition"] == "L1"
    assert build_plan("x", 2, "en", "tr", m)[0]["condition"] == "L2"
    assert build_plan("x", 2, "en", "tr", m)[0]["clue_lang"] == "tr"


def test_clues_carry_same_information():
    en = make_clue("scan", "en", 100, 50, 1200, 800)
    tr = make_clue("scan", "tr", 100, 50, 1200, 800)
    assert "upper-left" in en and "top edge" in en
    assert "sol üst" in tr and "üst kenara" in tr


def _answer(c, m, i, **extra):
    img_id = c.get("/trial").text.split('src="/img/')[1].split(".png")[0]
    tg = m[img_id]["target"]
    body = {"trial_index": i, "rt_ms": 1500 + i, "click_x": tg["x"], "click_y": tg["y"],
            "false_clicks": 0, "effort": 4, **extra}
    return img_id, c.post("/api/trial", json=body).json()


def test_full_session_flow():
    c = TestClient(app)
    with c:
        assert c.get("/").status_code == 200
        c.post("/start", data={"ui_lang": "tr"})
        c.post("/consent", data={"agree": "yes"})
        r = c.post("/background", data={
            "group": "high_school", "age": 17, "education_years": 12, "years_reading_images": 0,
            "native_lang": "tr", "l2_age_acquired": 5, "en_reading": 7, "tr_reading": 6, "comfort": "en"})
        assert r.status_code == 200 and "goril" not in r.text.lower()  # surprise intro never hints
        m = {i["id"]: i for i in load_manifest()["images"]}
        img_id, res = _answer(c, m, 0)
        assert img_id == "surprise" and res["next"] == "/notice"
        # The surprise questions cannot be skipped
        assert c.get("/trial").url.path == "/notice"
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "yes"})
        # A click far from the target is not a hit, even if the browser sends it
        first = c.get("/trial").text.split('src="/img/')[1].split(".png")[0]
        tg0 = m[first]["target"]
        miss = c.post("/api/trial", json={"trial_index": 1, "rt_ms": 900, "click_x": tg0["x"] + 400,
                                          "click_y": tg0["y"], "effort": 3})
        assert miss.json()["hit"] is False
        for i in range(2, 99):
            _, res = _answer(c, m, i)
            assert res["hit"] is True
        assert c.get("/trial").url.path == "/final"
        c.post("/final", data={"difficulty": 5, "attention": "red"})
        rows = c.get("/admin/export.csv?key=test-key").text.strip().splitlines()
        header = rows[0].split(",")
        mine = [dict(zip(header, r.split(","))) for r in rows[1:]]
        mine = [r for r in mine if r["noticed_unusual"] == "False" and r["group"] == "high_school"]
        assert len(mine) == 99
        assert mine[0]["task"] == "surprise" and mine[0]["knew_gorilla_study"] == "True"
        assert {r["round"] for r in mine if r["practice"] == "False" and r["task"] != "surprise"} == \
            {str(k) for k in range(1, 13)}
        assert all(r["elapsed_s"] != "" for r in mine)
        assert c.get("/admin/export.csv?key=wrong").status_code == 403


def test_session_stops_at_time_limit():
    from datetime import timedelta
    from app.db import Participant, SessionLocal, now
    c = TestClient(app)
    with c:
        _start(c)
        m = {i["id"]: i for i in load_manifest()["images"]}
        _answer(c, m, 0)
        c.post("/notice", data={"noticed": "yes"})
        c.post("/notice2", data={"saw_gorilla": "yes", "knew_study": "no"})
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            p.created_at = now() - timedelta(minutes=14.5)
            db.commit()
        assert c.get("/trial").url.path == "/final"
        with SessionLocal() as db:
            assert db.get(Participant, c.cookies.get("pid")).time_capped is True


def _start(c, en_reading=7, tr_reading=6):
    c.post("/start", data={"ui_lang": "en"})
    c.post("/consent", data={"agree": "yes"})
    return c.post("/background", data={
        "group": "radiologist", "age": 45, "education_years": 22, "years_reading_images": 12,
        "native_lang": "tr", "l2_age_acquired": 20, "en_reading": en_reading,
        "tr_reading": tr_reading, "comfort": "tr"})


def test_manifest_with_answers_is_not_public():
    c = TestClient(app)
    with c:
        assert c.get("/img/manifest.json").status_code == 404
        assert c.get("/img/../app/config.py").status_code == 404
        assert c.get("/img/search_00.png").status_code == 200


def test_reloaded_trial_is_flagged():
    c = TestClient(app)
    with c:
        _start(c)
        c.get("/trial")
        page = c.get("/trial")  # reload: image already seen before the clock restarted
        img_id = page.text.split('src="/img/')[1].split(".png")[0]
        tg = {i["id"]: i for i in load_manifest()["images"]}[img_id]["target"]
        c.post("/api/trial", json={"trial_index": 0, "rt_ms": 800, "click_x": tg["x"],
                                   "click_y": tg["y"], "effort": 2})
        last = c.get("/admin/export.csv?key=test-key").text.strip().splitlines()[-1]
        assert last.endswith(",1")  # reloads column


def test_out_of_range_answers_rejected_and_eligibility_flagged():
    c = TestClient(app)
    with c:
        assert _start(c, en_reading=12).status_code == 422
    c = TestClient(app)
    with c:
        assert _start(c, en_reading=2).status_code == 200
        from app.db import Participant, SessionLocal
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.eligible is False
