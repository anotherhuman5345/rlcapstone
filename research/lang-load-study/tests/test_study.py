"""Run with:  pytest -q"""
import os
import re
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
    assert [t["practice"] for t in a[1:4]] == [True, True, True]
    scored = [t for t in a if t["round"]]
    assert len(scored) == 144
    # Every round has the same mix: per task, 2 L1 and 2 L2 clues
    for r in range(1, 13):
        rnd = [t for t in scored if t["round"] == r]
        assert Counter((t["task"], t["condition"]) for t in rnd) == {
            ("search", "L1"): 2, ("search", "L2"): 2, ("scan", "L1"): 2, ("scan", "L2"): 2,
            ("dice", "L1"): 2, ("dice", "L2"): 2}
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
    tg = {"x": 100, "y": 50, "object": "fish", "color": "green"}
    en = make_clue("search", "en", "search_07", tg, 1200, 800)
    tr = make_clue("search", "tr", "search_07", tg, 1200, 800)
    assert "upper-left" in en and "top edge" in en and "green fish" in en
    assert "sol üst" in tr.lower() and "üst kenar" in tr and "yeşil" in tr and "balı" in tr


def test_scan_clues_never_name_the_target():
    from app.i18n import LANGUAGES, LOCALES
    m = load_manifest()
    for img in (i for i in m["images"] if i["task"] == "scan"):
        for lang in LANGUAGES:
            clue = make_clue("scan", lang, img["id"], img["target"], img["width"], img["height"]).lower()
            obj = LOCALES[lang]["clue"]["objects"][img["target"]["object"]]
            spaced = " " in LOCALES[lang]["clue"]["np"]
            for form in {obj["nom"], obj.get("acc", obj["nom"])}:
                form = form.lower()
                # Whole words where the script uses spaces (Turkish "ok" = arrow is inside "çok").
                found = re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", clue) if spaced else form in clue
                assert not found, (lang, img["id"], clue)


def test_targets_and_wording_do_not_repeat():
    from collections import Counter as C
    m = load_manifest()
    search = [i["target"] for i in m["images"] if i["task"] == "search"]
    assert len({(t["object"], t["color"]) for t in search}) == len(search)  # every search target unique
    scans = [i["target"]["object"] for i in m["images"] if i["task"] == "scan"]
    assert "gorilla" not in scans and len(set(scans)) >= 10
    # no scan object comes back before the others have had their turn
    assert max(C(scans).values()) - min(C(scans).values()) <= 1
    leads = {make_clue("search", "en", i["id"], i["target"], 1200, 800).split(".")[0][:12]
             for i in m["images"] if i["task"] == "search"}
    assert len(leads) >= 3  # several sentence patterns in use


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
            "native_lang": "tr", "l2_age_acquired": 5, "l1": "en", "l1_reading": 7, "l2": "tr",
            "l2_reading": 6})
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
        for i in range(2, 148):
            _, res = _answer(c, m, i)
            assert res["hit"] is True
        assert c.get("/trial").url.path == "/final"
        final = c.get("/final").text
        practice_obj = next(i for i in m.values() if i["id"] == "search_practice")["target"]["object"]
        assert 'value="%s"' % practice_obj in final and 'value="car"' in final
        c.post("/final", data={"difficulty": 5, "attention": practice_obj})
        rows = c.get("/admin/export.csv?key=test-key").text.strip().splitlines()
        header = rows[0].split(",")
        mine = [dict(zip(header, r.split(","))) for r in rows[1:]]
        mine = [r for r in mine if r["noticed_unusual"] == "False" and r["group"] == "high_school"]
        assert len(mine) == 148
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


def _start(c, l1_reading=7, l2_reading=6, l1="tr", l2="en"):
    c.post("/start", data={"ui_lang": "en"})
    c.post("/consent", data={"agree": "yes"})
    return c.post("/background", data={
        "group": "radiologist", "age": 45, "education_years": 22, "years_reading_images": 12,
        "native_lang": "tr", "l2_age_acquired": 20, "l1": l1, "l1_reading": l1_reading,
        "l2": l2, "l2_reading": l2_reading})


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
        assert _start(c, l1_reading=12).status_code == 422
    c = TestClient(app)
    with c:
        assert _start(c, l2_reading=2).status_code == 200
        from app.db import Participant, SessionLocal
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.eligible is False


def test_exhausted_button_ends_session_and_is_recorded():
    from app.db import Participant, SessionLocal
    c = TestClient(app)
    with c:
        _start(c)
        m = {i["id"]: i for i in load_manifest()["images"]}
        _answer(c, m, 0)
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "no"})
        for i in range(1, 6):
            _answer(c, m, i)
        assert 'id="quit"' in c.get("/trial").text
        assert c.post("/api/quit", json={"trial_index": 6}).json()["next"] == "/final"
        assert c.get("/trial").url.path == "/final"
        c.post("/final", data={"difficulty": 8, "attention": "car"})  # a decoy: never a target
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.quit_early and p.quit_trial == 6 and p.quit_elapsed_s is not None
            assert p.completed and p.attention_ok is False


def test_every_language_file_is_complete_and_builds_every_clue():
    import re
    from app.clues import (COLOR_NAMES, DECOY_OBJECTS, N_SCAN_LEADS, N_SEARCH_LEADS, N_WHERE,
                           TARGET_OBJECTS, make_clue)
    from app.i18n import LANGUAGES, LOCALES
    assert len(LANGUAGES) == 30
    en_ui = LOCALES["en"]["ui"]
    fields = lambda text: set(re.findall(r"{(\w+)}", text))
    for code in LANGUAGES:
        loc = LOCALES[code]
        assert loc["code"] == code and loc["name"] and loc["dir"] in ("ltr", "rtl"), code
        assert set(loc["ui"]) == set(en_ui), (code, set(en_ui) ^ set(loc["ui"]))
        for key, text in loc["ui"].items():
            assert text.strip(), (code, key)
            assert fields(text) == fields(en_ui[key]), (code, key)
        cl = loc["clue"]
        assert set(TARGET_OBJECTS + DECOY_OBJECTS) <= set(cl["objects"]), code
        assert set(COLOR_NAMES) <= set(cl["colors"]), code
        assert len(cl["regions"]) == 9 and set(cl["edges"]) == {"top", "bottom", "left", "right"}, code
        assert (len(cl["search_leads"]), len(cl["scan_leads"]), len(cl["where"])) == \
            (N_SEARCH_LEADS, N_SCAN_LEADS, N_WHERE), code
        for kind in TARGET_OBJECTS:
            for color in COLOR_NAMES:
                for k in range(N_SEARCH_LEADS * N_WHERE * 3):
                    clue = make_clue("search", code, f"x{k}", {"x": 90 * k % 1200, "y": 37 * k % 800,
                                     "object": kind, "color": color}, 1200, 800)
                    assert "{" not in clue and "  " not in clue, (code, clue)
        for k in range(12):
            make_clue("scan", code, f"s{k}", {"x": 100, "y": 700, "object": "cat", "color": None}, 1200, 800)
        make_clue("surprise", code, "surprise", {"x": 600, "y": 400}, 1200, 800)


def test_language_choice_drives_the_clue_language():
    c = TestClient(app)
    with c:
        _start(c, l1="ja", l2="es")
        m = {i["id"]: i for i in load_manifest()["images"]}
        _answer(c, m, 0)
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "no"})
        langs = set()
        for i in range(1, 12):
            page = c.get("/trial").text
            langs.add(page.split('class="clue" lang="')[1].split('"')[0])
            _answer(c, m, i)
        assert langs == {"ja", "es"}
        assert c.post("/background", data={"group": "adult", "age": 30, "education_years": 16,
                      "native_lang": "ja", "l2_age_acquired": 10, "l1": "ja", "l1_reading": 7,
                      "l2": "ja", "l2_reading": 5}).status_code == 200  # same language twice: re-asked


def test_right_to_left_languages_render_rtl():
    c = TestClient(app)
    with c:
        assert 'dir="rtl"' in c.get("/?lang=ar").text
        assert 'dir="ltr"' in c.get("/?lang=ja").text


def test_dice_target_is_the_square_the_moves_lead_to():
    from app.clues import make_clue
    step = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    for img in (i for i in load_manifest()["images"] if i["task"] == "dice"):
        t = img["target"]
        # Work back from the target to the start: it must land on a board square.
        col = (t["x"] - 40 - 39) / 78 - step[t["dir_a"]][0] * t["a"] - step[t["dir_b"]][0] * t["b"]
        row = (t["y"] - 49 - 39) / 78 - step[t["dir_a"]][1] * t["a"] - step[t["dir_b"]][1] * t["b"]
        assert col == int(col) and row == int(row) and 0 <= col < 9 and 0 <= row < 9, img["id"]
        assert {t["dir_a"], t["dir_b"]} & {"up", "down"} and {t["dir_a"], t["dir_b"]} & {"left", "right"}
        clue = make_clue("dice", "en", img["id"], t, 1200, 800)
        assert t["dir_a"] in clue and t["dir_b"] in clue and not any(ch.isdigit() for ch in clue)
