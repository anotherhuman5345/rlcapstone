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


def test_plan_is_balanced_and_counterbalanced():
    m = load_manifest()
    a = build_plan("p-a", 0, "en", "tr", m)
    b = build_plan("p-b", 1, "en", "tr", m)
    scored = [t for t in a if not t["practice"]]
    assert Counter(t["condition"] for t in scored) == {"L1": 12, "L2": 12}
    assert Counter(t["task"] for t in scored) == {"search": 12, "scan": 12}
    # Counterbalance flips which images get which language
    cond_a = {t["image_id"]: t["condition"] for t in a if not t["practice"]}
    cond_b = {t["image_id"]: t["condition"] for t in b if not t["practice"]}
    assert all(cond_a[k] != cond_b[k] for k in cond_a)
    # Practice trials are first in each block and in the comfortable language
    assert a[0]["practice"] and a[0]["clue_lang"] == "en"


def test_task_order_counterbalanced():
    m = load_manifest()
    assert build_plan("x", 0, "en", "tr", m)[0]["task"] == "search"
    assert build_plan("x", 2, "en", "tr", m)[0]["task"] == "scan"


def test_clues_carry_same_information():
    en = make_clue("scan", "en", 100, 50, 1200, 800)
    tr = make_clue("scan", "tr", 100, 50, 1200, 800)
    assert "upper-left" in en and "top edge" in en
    assert "sol üst" in tr and "üst kenara" in tr


def test_full_session_flow():
    c = TestClient(app)
    with c:
        assert c.get("/").status_code == 200
        c.post("/start", data={"ui_lang": "tr"})
        c.post("/consent", data={"agree": "yes"})
        r = c.post("/background", data={
            "group": "high_school", "age": 17, "education_years": 12, "years_reading_images": 0,
            "native_lang": "tr", "l2_age_acquired": 5, "en_reading": 7, "tr_reading": 6, "comfort": "en"})
        assert r.status_code == 200
        m = {i["id"]: i for i in load_manifest()["images"]}
        # A click far from the target is not a hit, even if the browser sends it
        first = c.get("/trial").text.split('src="/img/')[1].split(".png")[0]
        tg0 = m[first]["target"]
        miss = c.post("/api/trial", json={"trial_index": 0, "rt_ms": 900, "click_x": tg0["x"] + 400,
                                          "click_y": tg0["y"], "effort": 3})
        assert miss.json()["hit"] is False
        for i in range(1, 26):
            page = c.get("/trial")
            assert page.status_code == 200
            # find which image this trial uses
            img_id = page.text.split('src="/img/')[1].split(".png")[0]
            tg = m[img_id]["target"]
            res = c.post("/api/trial", json={"trial_index": i, "rt_ms": 1500 + i, "click_x": tg["x"],
                                             "click_y": tg["y"], "false_clicks": 0, "effort": 4})
            assert res.json()["hit"] is True
        assert c.get("/trial").status_code == 200  # redirects to final
        c.post("/final", data={"difficulty": 5, "attention": "red"})
        csv_text = c.get("/admin/export.csv?key=test-key").text
        assert csv_text.count("\n") == 27
        assert c.get("/admin/export.csv?key=wrong").status_code == 403
