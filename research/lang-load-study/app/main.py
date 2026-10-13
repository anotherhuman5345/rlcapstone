"""Web app: landing -> consent -> background -> surprise image -> surprise questions
-> instructions -> practice + rounds -> final -> debrief."""
import csv
import hashlib
import io
import json
import math
import random
from contextlib import asynccontextmanager
from datetime import timezone

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import config
import random

from .clues import DECOY_OBJECTS, N_FOILS, make_clue, object_name
from .db import FatigueRating, Participant, SessionLocal, TrialResult, init_db, now
from .i18n import LANGUAGES, LOCALES, direction, language_name, t, verified
from .plan import build_plan, load_manifest
from .reading import has_reading, reading_hash, reading_item

@asynccontextmanager
async def lifespan(_app):
    global _db_ready
    init_db()
    _db_ready = True
    yield


app = FastAPI(title="Language & Visual Search Study", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=config.ROOT / "app" / "templates")
COOKIE = "pid"


@app.get("/img/{name}")
def image(name: str):
    # Serve only the study images. The manifest (with every target's location)
    # stays private, so nobody can look up the answers.
    if name not in {i["file"] for i in load_manifest()["images"] if i.get("file")}:
        raise HTTPException(404)
    return FileResponse(config.STIMULI_DIR / name)


_db_ready = False


def get_db():
    # Serverless hosts may skip the startup hook, so make sure the tables exist once per process.
    global _db_ready
    if not _db_ready:
        init_db()
        _db_ready = True
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def render(request, name, p=None, lang="en", **ctx):
    lang = p.ui_lang if p else lang
    return templates.TemplateResponse(request, name, {
        "_": t(lang), "lang": lang, "dir": direction(lang), "demo": not config.IRB_APPROVED,
        "irb_number": config.IRB_NUMBER, **ctx})


def minutes_since(dt):
    if dt is None:
        return 0.0
    if dt.tzinfo is None:  # SQLite hands datetimes back without a timezone; they are UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    return (now() - dt).total_seconds() / 60


def current(request, db):
    pid = request.cookies.get(COOKIE)
    p = db.get(Participant, pid) if pid else None
    if p is None:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return p


@app.get("/", response_class=HTMLResponse)
def landing(request: Request, lang: str = "en"):
    lang = lang if lang in LANGUAGES else "en"
    return render(request, "landing.html", lang=lang, languages=language_choices(ui=True))


@app.post("/start")
def start(ui_lang: str = Form("en"), db=Depends(get_db)):
    p = Participant(ui_lang=ui_lang if ui_lang in LANGUAGES else "en",
                    is_test=not config.IRB_APPROVED)
    db.add(p)
    db.commit()
    resp = RedirectResponse("/consent", status_code=303)
    resp.set_cookie(COOKIE, p.id, httponly=True, samesite="lax", max_age=60 * 60 * 6)
    return resp


@app.get("/consent", response_class=HTMLResponse)
def consent_page(request: Request, db=Depends(get_db)):
    return render(request, "consent.html", current(request, db))


@app.post("/consent")
def consent(request: Request, agree: str = Form(None), db=Depends(get_db)):
    p = current(request, db)
    if agree != "yes":
        return RedirectResponse("/consent", status_code=303)
    p.consented = True
    db.commit()
    return RedirectResponse("/background", status_code=303)


@app.get("/background", response_class=HTMLResponse)
def background_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not p.consented:
        return RedirectResponse("/consent", status_code=303)
    return render(request, "background.html", p, groups=config.GROUPS,
                  languages=language_choices(), all_languages=language_choices(ui=True))


def language_choices(ui=False):
    """(code, name) pairs. Clue languages are limited to native-checked ones once
    real data collection starts; in demo mode every language can be tried."""
    codes = LANGUAGES if ui or not config.IRB_APPROVED else [c for c in LANGUAGES if verified(c)]
    return [(c, language_name(c)) for c in codes]


@app.post("/background")
def background(request: Request, group: str = Form(...), age: int = Form(..., ge=10, le=99),
               education_years: int = Form(..., ge=0, le=40),
               years_reading_images: float = Form(0, ge=0, le=60),
               native_lang: str = Form(...), l2_age_acquired: int = Form(..., ge=0, le=99),
               l1: str = Form(...), l2: str = Form(...),
               l1_reading: int = Form(..., ge=1, le=7), l2_reading: int = Form(..., ge=1, le=7),
               equal_comfort: str = Form(None), db=Depends(get_db)):
    p = current(request, db)
    allowed = {c for c, _ in language_choices()}
    if group not in config.GROUPS or l1 not in allowed or l2 not in allowed:
        raise HTTPException(400, "Invalid answer")
    if l1 == l2:
        return render(request, "background.html", p, groups=config.GROUPS, error=True,
                      languages=language_choices(), all_languages=language_choices(ui=True))
    p.group, p.age, p.education_years = group, age, education_years
    p.years_reading_images, p.native_lang, p.l2_age_acquired = years_reading_images, native_lang, l2_age_acquired
    p.l1, p.l2 = l1, l2
    p.l1_reading, p.l2_reading = l1_reading, l2_reading
    p.eligible = min(l1_reading, l2_reading) >= config.MIN_READING
    p.equal_comfort = equal_comfort == "yes"

    # Rotate counterbalance index within each group.
    n_in_group = db.scalar(select(func.count()).select_from(Participant)
                           .where(Participant.group == group, Participant.plan.is_not(None)))
    p.counterbalance = n_in_group % 4
    # Reading needs passages in both of the person's languages.
    available = set(config.ROUND_MIX) - (set() if has_reading(l1) and has_reading(l2) else {"reading"})
    p.plan = build_plan(p.id, p.counterbalance, p.l1, p.l2, available=available)
    db.commit()
    return RedirectResponse("/fatigue?point=baseline", status_code=303)


def _fatigue_done(db, p, point):
    return db.scalar(select(func.count()).select_from(FatigueRating)
                     .where(FatigueRating.participant_id == p.id, FatigueRating.point == point)) > 0


@app.get("/fatigue", response_class=HTMLResponse)
def fatigue_page(request: Request, point: str = "baseline", db=Depends(get_db)):
    p = current(request, db)
    done_round = int(point.rsplit("_", 1)[1]) if point.startswith("after_round_") else None
    return render(request, "fatigue.html", p, point=point, done_round=done_round)


@app.post("/fatigue")
def fatigue(request: Request, point: str = Form(...), value: int = Form(..., ge=0, le=100),
            db=Depends(get_db)):
    p = current(request, db)
    if not (point == "baseline" or point.startswith("after_round_")):
        raise HTTPException(400, "Invalid point")
    if not _fatigue_done(db, p, point):
        db.add(FatigueRating(participant_id=p.id, point=point, value=value,
                             elapsed_s=round(minutes_since(p.task_started_at) * 60, 1)
                             if p.task_started_at else None))
        db.commit()
    return RedirectResponse("/surprise" if point == "baseline" else "/trial", status_code=303)


@app.get("/surprise", response_class=HTMLResponse)
def surprise_intro(request: Request, db=Depends(get_db)):
    # Deliberately says nothing about animals: the gorilla must be unexpected.
    return render(request, "surprise.html", current(request, db))


@app.get("/notice", response_class=HTMLResponse)
def notice_page(request: Request, db=Depends(get_db)):
    return render(request, "notice.html", current(request, db))


@app.post("/notice")
def notice(request: Request, noticed: str = Form(...), db=Depends(get_db)):
    # Asked on its own page, before the gorilla is named, so the word cannot prompt the answer.
    p = current(request, db)
    if p.noticed_unusual is None:
        p.noticed_unusual = noticed == "yes"
        db.commit()
    return RedirectResponse("/notice2", status_code=303)


@app.get("/notice2", response_class=HTMLResponse)
def notice2_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if p.noticed_unusual is None:
        return RedirectResponse("/notice", status_code=303)
    return render(request, "notice2.html", p)


@app.post("/notice2")
def notice2(request: Request, saw_gorilla: str = Form(...), knew_study: str = Form(...),
            db=Depends(get_db)):
    p = current(request, db)
    if p.noticed_unusual is None:
        return RedirectResponse("/notice", status_code=303)
    if p.saw_gorilla is None:
        p.saw_gorilla = saw_gorilla == "yes"
        p.knew_gorilla_study = knew_study == "yes"
        db.commit()
    return RedirectResponse("/instructions", status_code=303)


@app.get("/instructions", response_class=HTMLResponse)
def instructions(request: Request, db=Depends(get_db)):
    p = current(request, db)
    names = {"l1": language_name(p.l1), "l2": language_name(p.l2)} if p.l1 else {"l1": "", "l2": ""}
    has_reading_task = any(t["task"] == "reading" for t in (p.plan or []))
    return render(request, "instructions.html", p, has_reading_task=has_reading_task, **names)


@app.get("/trial", response_class=HTMLResponse)
def trial_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not p.plan:
        return RedirectResponse("/background", status_code=303)
    if p.current_trial == 0 and not _fatigue_done(db, p, "baseline"):
        return RedirectResponse("/fatigue?point=baseline", status_code=303)
    if p.current_trial >= 1 and p.noticed_unusual is None:
        return RedirectResponse("/notice", status_code=303)
    if p.current_trial >= 1 and p.saw_gorilla is None:
        return RedirectResponse("/notice2", status_code=303)
    if p.current_trial >= 1 and minutes_since(p.created_at) > config.SESSION_LIMIT_MIN:
        # Safety maximum reached (stated in the consent text): skip whatever is left.
        p.time_capped = True
        p.current_trial = len(p.plan)
        db.commit()
    if p.current_trial >= len(p.plan):
        return RedirectResponse("/final", status_code=303)
    trial = p.plan[p.current_trial]
    prev = p.plan[p.current_trial - 1] if p.current_trial else None
    if trial.get("round") and prev and prev.get("round") and prev["round"] < trial["round"]:
        point = f"after_round_{prev['round']}"
        if not _fatigue_done(db, p, point):
            return RedirectResponse(f"/fatigue?point={point}", status_code=303)
    p.trial_views += 1
    if p.task_started_at is None:
        p.task_started_at = now()
    db.commit()
    img = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]
    tg = img["target"]
    clue = make_clue(trial["task"], trial["clue_lang"], img["id"], tg, img.get("width"), img.get("height"))
    template = {"corsi": "trial_corsi.html", "reading": "trial_reading.html", "rule": "trial_rule.html",
                "ospan": "trial_ospan.html"}.get(trial["task"], "trial.html")
    item = None
    if trial["task"] == "reading":
        item = reading_item(trial["clue_lang"], img["id"])
    elif trial["task"] == "rule":
        item = LOCALES[trial["clue_lang"]]["clue"]["rule"]
    elif trial["task"] == "ospan":
        item = ospan_view(trial["clue_lang"], img)
    return render(request, template, p, trial=trial, img=img, clue=clue, item=item,
                  n=p.current_trial + 1, total=len(p.plan), rounds=config.ROUNDS,
                  clue_dir=direction(trial["clue_lang"]),
                  timeout=config.TRIAL_TIMEOUT_MS)


def ospan_view(lang, img):
    """What the browser needs for one operation-span set, in the trial's language: the
    sums, the words to remember, and the recall choices (the words plus three others)."""
    words = LOCALES[lang]["clue"]["words"]
    target = img["target"]["words"]
    rng = random.Random(img["id"])
    others = rng.sample([k for k in range(len(words)) if k not in target], 3)
    choices = target + others
    rng.shuffle(choices)
    return {"sums": [s["text"] for s in img["target"]["sums"]],
            "words": [words[k] for k in target],
            "choices": [[k, words[k]] for k in choices],
            "labels": LOCALES[lang]["clue"]["ospan"]}


class TrialIn(BaseModel):
    trial_index: int
    rt_ms: float | None = None
    click_x: float | None = None  # in natural image pixels, for the final click
    click_y: float | None = None
    false_clicks: int = Field(0, ge=0)
    timed_out: bool = False
    effort: int | None = Field(None, ge=1, le=9)
    # Corsi: squares clicked; reading: option chosen; rule: "A"/"B";
    # operation span: {"recall": [word ids], "sums": [true/false/null per sum]}
    response: list[int] | int | str | dict | None = None
    focus_lost: int = Field(0, ge=0)


@app.post("/api/trial")
def record_trial(request: Request, data: TrialIn, db=Depends(get_db)):
    p = current(request, db)
    if data.trial_index != p.current_trial or p.current_trial >= len(p.plan or []):
        raise HTTPException(409, "Out-of-order trial")
    trial = p.plan[p.current_trial]
    img = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]
    tg = img["target"]
    # The server scores every trial itself so the browser cannot claim a hit.
    false_clicks = data.false_clicks
    if trial["task"] == "corsi":
        expected = tg["sequence"] if tg["direction"] == "forward" else tg["sequence"][::-1]
        clicks = data.response if isinstance(data.response, list) else []
        hit = not data.timed_out and clicks == expected
        false_clicks = sum(1 for a, b in zip(clicks, expected) if a != b) + abs(len(clicks) - len(expected))
    elif trial["task"] == "reading":
        hit = not data.timed_out and data.response == tg["answer"]
    elif trial["task"] == "rule":
        hit = not data.timed_out and data.response == tg["answer"]
    elif trial["task"] == "ospan":
        resp = data.response if isinstance(data.response, dict) else {}
        hit = not data.timed_out and resp.get("recall") == tg["words"]
        sums = resp.get("sums") or []
        # Wrong or missing sum judgements, counted separately from memory.
        false_clicks = sum(1 for k, sm in enumerate(tg["sums"]) if k >= len(sums) or sums[k] != sm["true"])
    else:
        hit = (not data.timed_out and data.click_x is not None and data.click_y is not None
               and math.hypot(data.click_x - tg["x"], data.click_y - tg["y"]) <= tg["r"] * config.HIT_TOLERANCE)
    db.add(TrialResult(participant_id=p.id, trial_index=p.current_trial, task=trial["task"],
                       image_id=trial["image_id"], target_object=tg.get("object"),
                       clue_lang=trial["clue_lang"],
                       condition=trial["condition"], practice=trial["practice"],
                       rt_ms=data.rt_ms if hit else None, hit=hit, timed_out=data.timed_out,
                       false_clicks=false_clicks, effort=data.effort, focus_lost=data.focus_lost,
                       response=json.dumps(data.response) if data.response is not None else None,
                       reloads=max(0, p.trial_views - 1), round=trial.get("round"),
                       elapsed_s=round(minutes_since(p.task_started_at) * 60, 1)))
    p.current_trial += 1
    p.trial_views = 0
    db.commit()
    if trial["task"] == "surprise":
        nxt = "/notice"
    else:
        nxt = "/trial" if p.current_trial < len(p.plan) else "/final"
    return {"ok": True, "hit": hit, "next": nxt}


class QuitIn(BaseModel):
    trial_index: int


@app.post("/api/quit")
def quit_early(request: Request, data: QuitIn, db=Depends(get_db)):
    """The "I'm exhausted" button. Stopping is always allowed; when it happens is data."""
    p = current(request, db)
    if p.plan and p.current_trial < len(p.plan) and not p.quit_early:
        p.quit_early = True
        p.quit_trial = p.current_trial
        p.quit_elapsed_s = round(minutes_since(p.task_started_at) * 60, 1)
        p.current_trial = len(p.plan)
        db.commit()
    return {"ok": True, "next": "/final"}


def attention_options(p):
    """Correct answer: the target of the practice search scene, which everyone saw.
    Wrong answers: objects that never appear as a target anywhere in the study."""
    images = {i["id"]: i for i in load_manifest()["images"]}
    practice = next(t for t in p.plan if t["practice"] and t["task"] == "search")
    correct = images[practice["image_id"]]["target"]["object"]
    options = [correct, *DECOY_OBJECTS[:3]]
    random.Random(p.id).shuffle(options)
    return correct, options


def _seen_words(db, p):
    """Words this person saw in completed operation-span trials: {word id: (lang, L1/L2)}."""
    images = {i["id"]: i for i in load_manifest()["images"]}
    seen = {}
    for tr in db.scalars(select(TrialResult).where(TrialResult.participant_id == p.id,
                                                   TrialResult.task == "ospan",
                                                   TrialResult.practice.is_(False))):
        for k in images[tr.image_id]["target"]["words"]:
            seen.setdefault(k, (tr.clue_lang, tr.condition))
    return seen


@app.get("/retention", response_class=HTMLResponse)
def retention_page(request: Request, db=Depends(get_db)):
    """About ten minutes after the words were shown: which do you recognise? Up to four
    seen words per language plus the same number never shown, in random order."""
    p = current(request, db)
    seen = _seen_words(db, p)
    if not seen or p.retention is not None:
        return RedirectResponse("/final", status_code=303)
    rng = random.Random(p.id + "retention")
    items = []
    n_words = len(LOCALES[p.l1]["clue"]["words"])
    foils = list(range(n_words - N_FOILS, n_words))  # never shown in operation span
    rng.shuffle(foils)
    for cond, lang in (("L1", p.l1), ("L2", p.l2)):
        mine = [k for k, (_, c) in seen.items() if c == cond]
        old = rng.sample(mine, min(4, len(mine)))
        new = [foils.pop() for _ in old]  # different foil words for each language
        items += [{"word": k, "lang": lang, "cond": cond, "seen": True} for k in old]
        items += [{"word": k, "lang": lang, "cond": cond, "seen": False} for k in new]
    rng.shuffle(items)
    p.retention = items  # fixed now, so a reload shows the same list
    db.commit()
    shown = [(n, LOCALES[it["lang"]]["clue"]["words"][it["word"]], it["lang"], direction(it["lang"]))
             for n, it in enumerate(items)]
    return render(request, "retention.html", p, shown=shown)


@app.post("/retention")
async def retention(request: Request, db=Depends(get_db)):
    p = current(request, db)
    form = await request.form()
    checked = {int(v) for v in form.getlist("checked")}
    if p.retention and not any("checked" in it for it in p.retention):
        p.retention = [{**it, "checked": n in checked} for n, it in enumerate(p.retention)]
        db.commit()
    return RedirectResponse("/final", status_code=303)


@app.get("/final", response_class=HTMLResponse)
def final_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if p.retention is None and _seen_words(db, p):
        return RedirectResponse("/retention", status_code=303)
    if p.retention is not None and not any("checked" in it for it in p.retention):
        return RedirectResponse("/retention", status_code=303)
    _, options = attention_options(p)
    return render(request, "final.html", p,
                  options=[(o, object_name(o, p.ui_lang)) for o in options])


@app.post("/final")
def final(request: Request, difficulty: int = Form(..., ge=1, le=9), attention: str = Form(...),
          fatigue: int = Form(..., ge=0, le=100), db=Depends(get_db)):
    p = current(request, db)
    if not _fatigue_done(db, p, "final"):
        db.add(FatigueRating(participant_id=p.id, point="final", value=fatigue,
                             elapsed_s=round(minutes_since(p.task_started_at) * 60, 1)
                             if p.task_started_at else None))
    p.overall_difficulty = difficulty
    p.attention_ok = attention == attention_options(p)[0]
    p.completed = True
    db.commit()
    return RedirectResponse("/debrief", status_code=303)


@app.get("/debrief", response_class=HTMLResponse)
def debrief(request: Request, db=Depends(get_db)):
    return render(request, "debrief.html", current(request, db))


# ---------- admin ----------

def require_admin(key: str):
    # Set ADMIN_KEY in the environment before deploying; "change-me" is for local use only.
    if key != config.ADMIN_KEY:
        raise HTTPException(403, "Forbidden")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, key: str = "", db=Depends(get_db)):
    require_admin(key)
    rows = db.execute(select(Participant.group, Participant.is_test, Participant.completed, func.count())
                      .group_by(Participant.group, Participant.is_test, Participant.completed)).all()
    return render(request, "admin.html", rows=rows, key=key, irb=config.IRB_APPROVED)


def _short_hash(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    except OSError:
        return ""


def versions_for(lang):
    """Version stamps for one data row: study code, stimulus set, and the exact
    translation files used for that row's clue language."""
    from .i18n import LOCALE_DIR
    loc = _short_hash(LOCALE_DIR / f"{lang}.json") if lang else ""
    read = reading_hash(lang) if lang else ""
    return config.STUDY_VERSION, _short_hash(config.MANIFEST), f"{loc}{'+' + read if read else ''}"


def retention_summary(p):
    """Hit and false-alarm rates for words from L1 and from L2 trials (None if not asked)."""
    out = []
    for cond in ("L1", "L2"):
        items = [it for it in (p.retention or []) if it["cond"] == cond and "checked" in it]
        old = [it for it in items if it["seen"]]
        new = [it for it in items if not it["seen"]]
        out.append(round(sum(it["checked"] for it in old) / len(old), 3) if old else None)
        out.append(round(sum(it["checked"] for it in new) / len(new), 3) if new else None)
    return out


EXPORT_COLS = ["participant_id", "is_test", "group", "age", "education_years", "years_reading_images",
               "native_lang", "l2_age_acquired", "l1", "l2", "l1_reading", "l2_reading",
               "eligible", "equal_comfort", "counterbalance", "attention_ok", "completed", "time_capped",
               "quit_early", "quit_elapsed_s", "quit_trial",
               "noticed_unusual", "saw_gorilla", "knew_gorilla_study",
               "trial_index", "round", "elapsed_s", "task", "image_id", "target_object",
               "clue_lang", "condition", "practice", "rt_ms", "hit", "timed_out", "false_clicks", "effort",
               "reloads", "focus_lost", "response", "study_version", "stimuli_version", "translation_version",
               "ret_l1_hits", "ret_l1_false_alarms", "ret_l2_hits", "ret_l2_false_alarms"]


@app.get("/admin/export.csv")
def export(key: str = "", db=Depends(get_db)):
    require_admin(key)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(EXPORT_COLS)
    for tr, p in db.execute(select(TrialResult, Participant).join(Participant)
                            .order_by(Participant.created_at, TrialResult.trial_index)):
        w.writerow([p.id, p.is_test, p.group, p.age, p.education_years, p.years_reading_images,
                    p.native_lang, p.l2_age_acquired, p.l1, p.l2, p.l1_reading, p.l2_reading,
                    p.eligible, p.equal_comfort, p.counterbalance, p.attention_ok, p.completed, p.time_capped,
                    p.quit_early, p.quit_elapsed_s, p.quit_trial,
                    p.noticed_unusual, p.saw_gorilla, p.knew_gorilla_study,
                    tr.trial_index, tr.round, tr.elapsed_s, tr.task,
                    tr.image_id, tr.target_object, tr.clue_lang, tr.condition, tr.practice, tr.rt_ms, tr.hit,
                    tr.timed_out, tr.false_clicks, tr.effort, tr.reloads, tr.focus_lost, tr.response,
                    *versions_for(tr.clue_lang), *retention_summary(p)])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=trials.csv"})


@app.get("/admin/fatigue.csv")
def export_fatigue(key: str = "", db=Depends(get_db)):
    require_admin(key)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["participant_id", "is_test", "group", "age", "education_years", "l1", "l2",
                "equal_comfort", "point", "value", "elapsed_s", "study_version"])
    for f, p in db.execute(select(FatigueRating, Participant).join(Participant)
                           .order_by(Participant.created_at, FatigueRating.created_at)):
        w.writerow([p.id, p.is_test, p.group, p.age, p.education_years, p.l1, p.l2,
                    p.equal_comfort, f.point, f.value, f.elapsed_s, config.STUDY_VERSION])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=fatigue.csv"})
