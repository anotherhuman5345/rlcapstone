"""Run with:  pytest -q   (tests/conftest.py points the app at a throwaway SQLite file)"""
import csv
import io
import re
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
    assert [t["practice"] for t in a[1:8]] == [True] * 7
    scored = [t for t in a if t["round"]]
    assert len(scored) == 336
    # Every round has the same mix: per task, 2 L1 and 2 L2 clues
    for r in range(1, 25):
        rnd = [t for t in scored if t["round"] == r]
        assert Counter((t["task"], t["condition"]) for t in rnd) == {
            (task, cond): 1 for task in ("search", "scan", "dice", "corsi", "reading", "rule", "ospan")
            for cond in ("L1", "L2")}
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


def _current(c):
    """Open the current trial, answering a fatigue check-in first if one is due."""
    r = c.get("/trial")
    if r.url.path == "/fatigue":
        point = r.text.split('name="point" value="')[1].split('"')[0]
        c.post("/fatigue", data={"point": point, "value": 40})
        r = c.get("/trial")
    page = r.text
    if 'src="/img/' in page:
        return page.split('src="/img/')[1].split(".png")[0]
    return page.split('data-item="')[1].split('"')[0]


def _answer(c, m, i, correct=True, **extra):
    img_id = _current(c)
    tg, task = m[img_id]["target"], m[img_id]["task"]
    body = {"trial_index": i, "rt_ms": 1500 + i, "false_clicks": 0, "effort": 4}
    if task == "corsi":
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
        body.update(click_x=tg["x"] + (0 if correct else 400), click_y=tg["y"])
    body.update(extra)
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
        assert _answer(c, m, 1, correct=False)[1]["hit"] is False
        total = 1 + 7 + 24 * 14  # surprise, 7 practice, 24 rounds of 14
        for i in range(2, total):
            _, res = _answer(c, m, i)
            assert res["hit"] is True
        # Words were shown, so the retention check comes before the final questions.
        ret = c.get("/trial")
        assert ret.url.path == "/retention"
        n_words = ret.text.count('name="checked"')
        assert n_words == 16  # 4 seen + 4 new, per language
        c.post("/retention", data={"checked": ["0", "1", "2"]})
        final = c.get("/final").text
        practice_obj = next(i for i in m.values() if i["id"] == "search_practice")["target"]["object"]
        assert 'value="%s"' % practice_obj in final and 'value="car"' in final
        c.post("/final", data={"difficulty": 5, "attention": practice_obj, "fatigue": 70})
        mine = _csv_rows(c.get("/admin/export.csv?key=test-key").text)
        mine = [r for r in mine if r["noticed_unusual"] == "False" and r["group"] == "high_school"]
        assert len(mine) == total
        assert {r["task"] for r in mine} == {"surprise", "search", "scan", "dice", "corsi", "reading",
                                             "rule", "ospan"}
        assert mine[0]["ret_l1_hits"] != "" and mine[0]["ret_l2_false_alarms"] != ""
        assert all(r["study_version"] and r["stimuli_version"] and r["translation_version"] for r in mine)
        fatigue = _csv_rows(c.get("/admin/fatigue.csv?key=test-key").text)
        points = [row["point"] for row in fatigue if row["participant_id"] == c.cookies.get("pid")]
        assert points == ["baseline"] + [f"after_round_{k}" for k in range(1, 24)] + ["final"]
        assert mine[0]["task"] == "surprise" and mine[0]["knew_gorilla_study"] == "True"
        assert {r["round"] for r in mine if r["practice"] == "False" and r["task"] != "surprise"} == \
            {str(k) for k in range(1, 25)}
        assert all(r["elapsed_s"] != "" for r in mine)
        assert c.get("/admin/export.csv?key=wrong").status_code == 403


def _csv_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_session_stops_at_time_limit():
    """The cap counts from the first scored stimulus, not from the start page."""
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
            p.created_at = now() - timedelta(minutes=600)  # a long consent/practice does not count
            db.commit()
        for i in range(1, 8):  # the seven practice trials
            _answer(c, m, i)
        assert c.get("/trial").url.path == "/trial"  # first scored trial: the clock starts here
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.deadline_at is not None
            p.deadline_at = now() - timedelta(seconds=1)
            db.commit()
        assert c.get("/trial").url.path == "/final"
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.time_capped is True and p.stop_reason == "time_cap"


def _start(c, l1_reading=7, l2_reading=6, l1="tr", l2="en"):
    c.post("/start", data={"ui_lang": "en"})
    c.post("/consent", data={"agree": "yes"})
    r = c.post("/background", data={
        "group": "radiologist", "age": 45, "education_years": 22, "years_reading_images": 12,
        "native_lang": "tr", "l2_age_acquired": 20, "l1": l1, "l1_reading": l1_reading,
        "l2": l2, "l2_reading": l2_reading})
    if r.status_code == 200 and r.url.path == "/fatigue":
        c.post("/fatigue", data={"point": "baseline", "value": 30})
    return r


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
        last = _csv_rows(c.get("/admin/export.csv?key=test-key").text)[-1]
        assert last["reloads"] == "1"


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
        c.post("/final", data={"difficulty": 8, "attention": "car", "fatigue": 85})  # a decoy: never a target
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert p.quit_early and p.quit_trial == 6 and p.quit_elapsed_s is not None
            assert p.completed and p.attention_ok is False



def test_approved_sessions_restrict_interface_as_well_as_clue_languages(monkeypatch):
    from app import config
    from app.main import language_choices

    monkeypatch.setattr(config, "IRB_APPROVED", True)
    allowed = {code for code, _ in language_choices(ui=True)}
    assert allowed == {code for code, _ in language_choices()}
    assert "en" in allowed and "tr" not in allowed
    with TestClient(app) as client:
        assert client.post("/start", data={"ui_lang": "tr"}).status_code == 400
        assert client.post("/start", data={"ui_lang": "en"}, follow_redirects=False).status_code == 303

def test_every_language_file_is_complete_and_builds_every_clue():
    import re
    from app.clues import (COLOR_NAMES, DECOY_OBJECTS, N_SCAN_LEADS, N_SEARCH_LEADS, N_WHERE,
                           TARGET_OBJECTS, make_clue)
    from app.i18n import LANGUAGES, LOCALES, PENDING_UI_KEYS, verified
    assert len(LANGUAGES) == 30
    en_ui = LOCALES["en"]["ui"]
    fields = lambda text: set(re.findall(r"{(\w+)}", text))
    for code in LANGUAGES:
        loc = LOCALES[code]
        assert loc["code"] == code and loc["name"] and loc["dir"] in ("ltr", "rtl"), code
        # Newer strings may still be untranslated (English is shown instead), but never in
        # a verified language, and a file may not carry keys English lacks.
        missing = set(en_ui) - set(loc["ui"])
        assert missing <= PENDING_UI_KEYS and set(loc["ui"]) <= set(en_ui), (code, set(en_ui) ^ set(loc["ui"]))
        assert not (missing and verified(code)), code
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
        # Practice items (one per task) all use the comfortable language, so look past them.
        for i in range(1, 30):
            page = c.get("/trial").text
            # The clue language sits on the clue line, or on the task area for reading/ospan.
            found = re.search(r'(?:class="clue"|data-item="[^"]*") lang="([a-z]{2})"', page)
            assert found, page[:300]
            langs.add(found.group(1))
            if langs == {"ja", "es"}:
                break
            _answer(c, m, i)
        assert langs == {"ja", "es"}
    c = TestClient(app)
    with c:
        c.post("/start", data={"ui_lang": "en"})
        c.post("/consent", data={"agree": "yes"})
        r = c.post("/background", data={"group": "adult", "age": 30, "education_years": 16,
                   "native_lang": "ja", "l2_age_acquired": 10, "l1": "ja", "l1_reading": 7,
                   "l2": "ja", "l2_reading": 5})
        assert r.status_code == 200 and r.url.path == "/background"  # same language twice: re-asked


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


def test_reading_only_when_both_languages_have_passages_and_scoring():
    m = load_manifest()
    no_reading = build_plan("x", 0, "ja", "es", m, available={"search", "scan", "dice", "corsi", "rule", "ospan"})
    assert "reading" not in {t["task"] for t in no_reading}
    c = TestClient(app)
    with c:
        _start(c, l1="ja", l2="es")  # both now have passages, so reading is in the plan
        from app.db import Participant, SessionLocal
        with SessionLocal() as db:
            assert "reading" in {t["task"] for t in db.get(Participant, c.cookies.get("pid")).plan}


def test_corsi_scoring_and_focus_flag():
    from app.db import SessionLocal, TrialResult
    c = TestClient(app)
    with c:
        _start(c)
        m = {i["id"]: i for i in load_manifest()["images"]}
        _answer(c, m, 0)
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "no"})
        i, seen = 1, set()
        while seen != {"corsi", "reading"}:
            img_id = _current(c)
            task = m[img_id]["task"]
            if task in ("corsi", "reading") and task not in seen:
                _, res = _answer(c, m, i, correct=False, focus_lost=2)
                assert res["hit"] is False
                seen.add(task)
            else:
                _answer(c, m, i)
            i += 1
        with SessionLocal() as db:
            rows = db.query(TrialResult).filter(TrialResult.focus_lost == 2).all()
            assert {r.task for r in rows} >= {"corsi", "reading"} and all(r.response for r in rows)


def test_rule_answers_follow_the_rule():
    import sys
    sys.path.insert(0, "stimuli")
    from generate_stimuli import rule_answer
    for img in (i for i in load_manifest()["images"] if i["task"] == "rule"):
        t = img["target"]
        assert rule_answer(t["rule"], t["color"], t["count"]) == t["answer"], img["id"]


def test_ospan_scoring_and_retention_rates():
    from app.db import Participant, SessionLocal, TrialResult
    c = TestClient(app)
    with c:
        _start(c)
        m = {i["id"]: i for i in load_manifest()["images"]}
        _answer(c, m, 0)
        c.post("/notice", data={"noticed": "no"})
        c.post("/notice2", data={"saw_gorilla": "no", "knew_study": "no"})
        i, wrong_done, scored = 1, False, 0
        while scored < 2:  # until two scored operation-span sets are done
            img_id = _current(c)
            if m[img_id]["task"] == "ospan" and not m[img_id]["practice"]:
                _, res = _answer(c, m, i, correct=wrong_done)
                assert res["hit"] is wrong_done
                wrong_done, scored = True, scored + 1
            else:
                _answer(c, m, i)
            i += 1
        c.post("/api/quit", json={"trial_index": i})
        page = c.get("/final")
        assert page.url.path == "/retention"
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            items = p.retention
        seen_idx = [str(n) for n, it in enumerate(items) if it["seen"]]
        c.post("/retention", data={"checked": seen_idx})  # tick exactly the seen words
        assert c.get("/final").url.path == "/final"
        with SessionLocal() as db:
            p = db.get(Participant, c.cookies.get("pid"))
            assert all(it["checked"] == it["seen"] for it in p.retention)
            from app.main import retention_summary
            hits_l1, fa_l1, hits_l2, fa_l2 = retention_summary(p)
            assert fa_l1 in (0, None) and fa_l2 in (0, None) and 1 in (hits_l1, hits_l2)



def test_retention_tracks_same_word_index_in_both_languages(monkeypatch):
    """F06 regression: identical numeric word IDs in L1/L2 are separate exposures."""
    from types import SimpleNamespace
    from app import main as study

    images = [
        {"id": "ospan_l1", "target": {"words": [2, 4, 8]}},
        {"id": "ospan_l1_again", "target": {"words": [2, 4]}},
        {"id": "ospan_l2", "target": {"words": [2, 9, 11]}},
    ]
    monkeypatch.setattr(study, "load_manifest", lambda: {"images": images})
    trials = [
        SimpleNamespace(image_id="ospan_l1", clue_lang="en", condition="L1"),
        SimpleNamespace(image_id="ospan_l1_again", clue_lang="en", condition="L1"),
        SimpleNamespace(image_id="ospan_l2", clue_lang="tr", condition="L2"),
    ]

    class StubDB:
        def scalars(self, _query):
            return trials

    participant = SimpleNamespace(id="test-overlap", l1="en", l2="tr")
    seen = study._seen_words(StubDB(), participant)
    assert seen == {
        ("en", "L1", 2), ("en", "L1", 4), ("en", "L1", 8),
        ("tr", "L2", 2), ("tr", "L2", 9), ("tr", "L2", 11),
    }

    items = study._retention_items(participant, seen)
    old = {(it["lang"], it["cond"], it["word"]) for it in items if it["seen"]}
    assert old == seen  # both languages still include index 2
    assert len(items) == 12  # 3 seen + 3 unseen in each language
    assert len({it["word"] for it in items if not it["seen"]}) == 6
    assert all(it["word"] >= 50 for it in items if not it["seen"])
    assert study._retention_items(participant, seen) == items  # stable on reload


def test_retention_handles_single_language_exposure_without_inventing_other():
    from types import SimpleNamespace
    from app.main import _retention_items

    participant = SimpleNamespace(id="only-l1", l1="en", l2="tr")
    items = _retention_items(participant, {("en", "L1", 7)})
    assert len(items) == 2
    assert {it["cond"] for it in items} == {"L1"}
    assert sum(it["seen"] for it in items) == 1

def test_every_library_task_passes_its_checks():
    """Runs tools/check_task.py for each task in app/tasks (determinism, scoring of
    correct/wrong/junk responses, text keys per language, template, JS syntax)."""
    import subprocess
    import sys
    from app.tasks import LOAD_ERRORS, PLUGINS
    assert not LOAD_ERRORS, LOAD_ERRORS
    assert PLUGINS, "no library tasks found"
    failed = {}
    for task_id in PLUGINS:
        r = subprocess.run([sys.executable, "tools/check_task.py", task_id], capture_output=True, text=True)
        if r.returncode != 0:
            failed[task_id] = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")][:3]
    assert not failed, failed


def test_library_task_runs_inside_a_session():
    """A library task listed in the round mix appears in a participant's plan,
    renders on the shared screen, and is scored on the server."""
    from app import main as appmain
    from app.tasks import PLUGINS
    m = load_manifest()
    plan = build_plan("lib", 0, "en", "tr", m, mix={"flanker": 2}, rounds=2)
    assert [t["task"] for t in plan if t["round"]] == ["flanker"] * 4
    c = TestClient(app)
    with c:
        r = c.get("/try/flanker?lang=tr")
        assert r.status_code == 200 and "/taskjs/flanker.js" in r.text
        item = next(i for i in m["images"] if i["id"] == "flanker_00")
        ok = c.post("/try/flanker/score", json={"image_id": "flanker_00",
                    "response": PLUGINS["flanker"].logic.example_response(item["target"], True)}).json()
        assert ok["hit"] is True and "flanker_cost_ms" in ok["metrics"]
    assert appmain.PLUGINS is PLUGINS


def test_reading_passages_match_english():
    """Every app/reading/<lang>.json has the same items, option counts and correct
    answers as en.json (tools/check_reading.py)."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "tools/check_reading.py"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
