"""Web app: landing -> consent -> background -> surprise image -> surprise questions
-> instructions -> practice + rounds -> final -> debrief."""
import csv
import hashlib
import hmac
import io
import json
import math
import random
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse, RedirectResponse,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from . import config
from .clues import DECOY_OBJECTS, N_FOILS, make_clue, object_name
from .db import (AllocationCounter, FatigueRating, Participant, SessionLocal, TrialResult, init_db,
                 now)
from .i18n import LANGUAGES, LOCALE_HASH, LOCALES, direction, language_name, t, verified
from .plan import build_plan, load_manifest
from .reading import has_reading, reading_hash, reading_item
from .tasks import PLUGINS, ascii_digits

@asynccontextmanager
async def lifespan(_app):
    global _db_ready
    init_db()
    _db_ready = True
    yield


app = FastAPI(title="Language & Visual Search Study", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.ROOT / "app" / "static"), name="static")


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, exc):
    # One shape for every rejected payload. The submitted values are not echoed back:
    # they may be NaN/Infinity, which JSON cannot carry, or simply very large.
    errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", "")} for e in exc.errors()]
    return JSONResponse({"ok": False, "error": "invalid", "detail": errors}, status_code=422)


templates = Jinja2Templates(directory=[config.ROOT / "app" / "templates", config.ROOT / "app" / "tasks"])
COOKIE = "pid"


@app.get("/img/{name}")
def image(name: str):
    # Serve only the study images. The manifest (with every target's location)
    # stays private, so nobody can look up the answers.
    if name not in {i["file"] for i in load_manifest()["images"] if i.get("file")}:
        raise HTTPException(404)
    return FileResponse(config.STIMULI_DIR / name)


_db_ready = False


@app.get("/taskjs/{task_id}.js")
def task_js(task_id: str):
    if task_id not in PLUGINS:
        raise HTTPException(404)
    return FileResponse(PLUGINS[task_id].js, media_type="text/javascript")


@app.get("/try", response_class=HTMLResponse)
def try_index(request: Request, lang: str = "en"):
    """Task library: every task, each with a stand-alone demo. Nothing is saved."""
    lang = lang if lang in LANGUAGES else "en"
    tasks = sorted(PLUGINS.values(), key=lambda pl: pl.meta.get("card", "99"))
    return render(request, "try_index.html", lang=lang, tasks=tasks)


@app.get("/try/{task_id}", response_class=HTMLResponse)
def try_task(request: Request, task_id: str, lang: str = "en", k: int = 0):
    if task_id not in PLUGINS:
        raise HTTPException(404)
    plugin = PLUGINS[task_id]
    lang = lang if plugin.has_language(lang) else "en"
    items = [i for i in load_manifest()["images"] if i["task"] == task_id]
    if not items:
        raise HTTPException(404, "Run the stimulus generator")
    img = items[k % len(items)]
    trial = {"task": task_id, "image_id": img["id"], "clue_lang": lang, "practice": True, "round": None}
    return render(request, "plugin_trial.html", lang=lang, trial=trial, img=img, plugin=plugin,
                  text=plugin.text[lang], clue_dir=direction(lang), n=1, rounds=config.ROUNDS,
                  timeout=plugin.timeout_ms, try_mode=True, next_k=k + 1)


@app.post("/try/{task_id}/score")
async def try_score(task_id: str, request: Request):
    if task_id not in PLUGINS:
        raise HTTPException(404)
    body = await request.json()
    img = next(i for i in load_manifest()["images"] if i["id"] == body.get("image_id"))
    return PLUGINS[task_id].logic.score(img["target"], ascii_digits(body.get("response")))


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


def _utc(dt):
    if dt is not None and dt.tzinfo is None:  # SQLite hands datetimes back without a timezone; they are UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt):
    return _utc(dt).isoformat() if dt is not None else ""


def minutes_since(dt):
    if dt is None:
        return 0.0
    return (now() - _utc(dt)).total_seconds() / 60


def current(request, db):
    pid = request.cookies.get(COOKIE)
    p = db.get(Participant, pid) if pid else None
    if p is None:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return p


# ---------- session state ----------

# A browser that says "time is up" this many seconds before the server deadline is
# believed (network and timer jitter); earlier than that it is sent back to resync.
CLOCK_GRACE_S = 2.0


def _past_deadline(p, at=None):
    deadline = _utc(p.deadline_at)
    return deadline is not None and (at or now()) >= deadline


def _remaining_ms(p):
    deadline = _utc(p.deadline_at)
    return None if deadline is None else max(0, int((deadline - now()).total_seconds() * 1000))


def _ended(p):
    """The task part is over: stopped for any reason, or every planned trial answered."""
    return p.stop_reason is not None or (bool(p.plan) and p.current_trial >= len(p.plan))


def _fatigue_done(db, p, point):
    return db.scalar(select(func.count()).select_from(FatigueRating)
                     .where(FatigueRating.participant_id == p.id, FatigueRating.point == point)) > 0


def next_step(db, p):
    """Where this person belongs now. Out-of-phase requests are sent here unchanged."""
    if p.completed or p.final_skipped:
        return "/debrief"
    if not p.consented:
        return "/consent"
    if not p.plan:
        return "/background"
    if _ended(p):
        return "/final"
    if not _fatigue_done(db, p, "baseline"):
        return "/fatigue?point=baseline"
    return "/trial"


def _api_error(db, p, error, status=409):
    # Every JSON write endpoint fails the same way: nothing stored, and where to go next.
    return JSONResponse({"ok": False, "error": error, "next": next_step(db, p)}, status_code=status)


def _stop(db, p, reason, requested=None, at_trial=None):
    """Record how and when the session stopped, once. The UPDATE only matches while
    stop_reason is still empty, so two simultaneous stops cannot both write."""
    if p.stop_reason is not None:
        return False
    at = now()
    cap_start = _utc(p.cap_started_at)
    values = dict(
        stop_reason=reason, stop_requested=requested or reason, stopped_at=at,
        stop_elapsed_s=round((at - cap_start).total_seconds(), 3) if cap_start else None,
        stop_clock_basis=("server_utc; elapsed from first scored stimulus" if cap_start
                          else "server_utc; before first scored stimulus"),
        quit_trial=at_trial if at_trial is not None else (p.current_trial if p.plan else None),
        quit_elapsed_s=round(minutes_since(p.task_started_at) * 60, 1) if p.task_started_at else None,
        quit_early=reason == "exhausted", time_capped=reason == "time_cap" or bool(p.time_capped))
    if p.plan:
        values["current_trial"] = len(p.plan)
    res = db.execute(update(Participant).where(Participant.id == p.id, Participant.stop_reason.is_(None))
                     .values(**values))
    return res.rowcount == 1


def _session_ctx(p):
    """What the shared browser controller (static/session.js) needs: the time left until
    the stored deadline (None before the first scored stimulus), the trial position the
    page belongs to, and the messages it shows."""
    _ = t(p.ui_lang)
    return {"index": p.current_trial, "remainingMs": _remaining_ms(p),
            # Ties a saved-but-unsent answer in this browser to this session only.
            "sid": hashlib.sha256(p.id.encode()).hexdigest()[:12],
            "msgTimeUp": _("time_up"), "msgQuitConfirm": _("quit_confirm"),
            "msgWithdrawConfirm": _("withdraw_confirm"), "msgSaving": _("saving_retry")}


# ---------- version stamps (stored when assigned or shown, never recomputed at export) ----------

_MANIFEST_HASH = {}


def manifest_version():
    # The manifest is large; hash it once per file version.
    try:
        st = config.MANIFEST.stat()
    except OSError:
        return ""
    key = (st.st_mtime_ns, st.st_size)
    if key not in _MANIFEST_HASH:
        _MANIFEST_HASH.clear()
        _MANIFEST_HASH[key] = _short_hash(config.MANIFEST)
    return _MANIFEST_HASH[key]


def translation_version(lang):
    """Locale file plus reading passages for one language, as loaded by this process."""
    if not lang:
        return ""
    loc, read = LOCALE_HASH.get(lang, ""), reading_hash(lang)
    return f"{loc}{'+' + read if read else ''}"


def trial_versions(task, lang):
    return {"study_version": config.STUDY_VERSION, "software_commit": config.SOFTWARE_COMMIT,
            "stimuli_version": manifest_version(), "translation_version": translation_version(lang),
            # Core tasks take their text from the locale file (translation_version).
            "task_text_version": PLUGINS[task].text_hash.get(lang, "") if task in PLUGINS else "locale"}


def session_versions(ui_lang, l1, l2, plan):
    tasks = sorted({tr["task"] for tr in plan if tr["task"] in PLUGINS})
    return {"study_version": config.STUDY_VERSION, "software_commit": config.SOFTWARE_COMMIT,
            "stimuli_version": manifest_version(), "ui_translation": LOCALE_HASH.get(ui_lang, ""),
            "l1_translation": translation_version(l1), "l2_translation": translation_version(l2),
            "task_text": {tk: {lg: PLUGINS[tk].text_hash.get(lg, "") for lg in (l1, l2)} for tk in tasks}}


# ---------- participant pages ----------

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
    if not p.consented:
        p.consented = True
        db.commit()
    return RedirectResponse(next_step(db, p), status_code=303)


def _background_form(request, p, **extra):
    return render(request, "background.html", p, groups=config.GROUPS, min_age=config.MIN_AGE,
                  languages=language_choices(), all_languages=language_choices(ui=True), **extra)


@app.get("/background", response_class=HTMLResponse)
def background_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not p.consented or p.plan:
        # Setup is frozen once a plan exists; a new plan needs a new session.
        return RedirectResponse(next_step(db, p), status_code=303)
    return _background_form(request, p)


def language_choices(ui=False):
    """(code, name) pairs. Clue languages are limited to native-checked ones once
    real data collection starts; in demo mode every language can be tried."""
    codes = LANGUAGES if ui or not config.IRB_APPROVED else [c for c in LANGUAGES if verified(c)]
    return [(c, language_name(c)) for c in codes]


def allocate(db, pool, seed):
    """Next counterbalance slot in a pool, inside the caller's transaction. The single
    UPDATE ... RETURNING locks the counter row, so concurrent enrolments are serialised.
    seed starts a new pool where an older database's rotation left off."""
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    db.execute(insert(AllocationCounter).values(pool=pool, next_index=seed)
               .on_conflict_do_nothing(index_elements=["pool"]))
    n = db.execute(update(AllocationCounter).where(AllocationCounter.pool == pool)
                   .values(next_index=AllocationCounter.next_index + 1)
                   .returning(AllocationCounter.next_index)).scalar_one()
    return n - 1


@app.post("/background")
def background(request: Request, group: str = Form(...),
               age: int = Form(..., ge=config.MIN_AGE, le=99),
               education_years: int = Form(..., ge=0, le=40),
               years_reading_images: float = Form(0, ge=0, le=60, allow_inf_nan=False),
               native_lang: str = Form(...), l2_age_acquired: int = Form(..., ge=0, le=99),
               l1: str = Form(...), l2: str = Form(...),
               l1_reading: int = Form(..., ge=1, le=7), l2_reading: int = Form(..., ge=1, le=7),
               equal_comfort: str = Form(None), db=Depends(get_db)):
    p = current(request, db)
    if not p.consented or p.plan:
        return RedirectResponse(next_step(db, p), status_code=303)
    allowed = {c for c, _ in language_choices()}
    if (group not in config.GROUPS or l1 not in allowed or l2 not in allowed
            or native_lang not in {*LANGUAGES, "other"}):
        raise HTTPException(400, "Invalid answer")
    if l1 == l2:
        return _background_form(request, p, error="bg_same_lang")
    if l2_age_acquired > age:
        return _background_form(request, p, error="bg_l2_age_invalid")
    # Counterbalance rotates within each group. Demo/test sessions use their own pool,
    # so they never shift the real-study rotation.
    pool = f"{'test' if p.is_test else 'real'}:{group}"
    seed = db.scalar(select(func.count()).select_from(Participant)
                     .where(Participant.group == group, Participant.plan.is_not(None),
                            Participant.is_test.is_(p.is_test)))
    counterbalance = allocate(db, pool, seed) % 4
    # Reading needs passages in both of the person's languages.
    available = set(config.ROUND_MIX) - (set() if has_reading(l1) and has_reading(l2) else {"reading"})
    # Library tasks run only when their text exists in both of the person's languages.
    available -= {tk for tk in available if tk in PLUGINS and not (PLUGINS[tk].has_language(l1)
                                                                   and PLUGINS[tk].has_language(l2))}
    plan = build_plan(p.id, counterbalance, l1, l2, available=available)
    # Conditional write: a second tab posting the form at the same time finds a plan
    # already there and changes nothing (its counter step is rolled back with it).
    res = db.execute(update(Participant).where(Participant.id == p.id, Participant.plan.is_(None)).values(
        group=group, age=age, education_years=education_years,
        years_reading_images=years_reading_images, native_lang=native_lang,
        l2_age_acquired=l2_age_acquired, l1=l1, l2=l2, l1_reading=l1_reading, l2_reading=l2_reading,
        eligible=min(l1_reading, l2_reading) >= config.MIN_READING, equal_comfort=equal_comfort == "yes",
        counterbalance=counterbalance, plan=plan, versions=session_versions(p.ui_lang, l1, l2, plan)))
    if res.rowcount != 1:
        db.rollback()
        return RedirectResponse(next_step(db, p), status_code=303)
    db.commit()
    return RedirectResponse("/fatigue?point=baseline", status_code=303)


POINT = re.compile(r"^(baseline|after_round_([1-9][0-9]{0,2}))$")


@app.get("/fatigue", response_class=HTMLResponse)
def fatigue_page(request: Request, point: str = "baseline", db=Depends(get_db)):
    p = current(request, db)
    m = POINT.match(point)
    if not m or not p.plan or (point != "baseline" and p.task_started_at is None):
        return RedirectResponse(next_step(db, p), status_code=303)
    if not _ended(p) and _past_deadline(p):
        _stop(db, p, "time_cap")
        db.commit()
    if _ended(p):
        return RedirectResponse("/final", status_code=303)
    done_round = int(m.group(2)) if m.group(2) else None
    return render(request, "fatigue.html", p, point=point, done_round=done_round, session=_session_ctx(p))


@app.post("/fatigue")
def fatigue(request: Request, point: str = Form(...), value: int = Form(..., ge=0, le=100),
            db=Depends(get_db)):
    p = current(request, db)
    if not POINT.match(point):
        raise HTTPException(400, "Invalid point")
    if not p.plan or _ended(p) or (point != "baseline" and p.task_started_at is None):
        return RedirectResponse(next_step(db, p), status_code=303)
    # A rating sent after the deadline is kept but flagged, and the cap ends the session.
    late = _past_deadline(p)
    if not _fatigue_done(db, p, point):
        db.add(FatigueRating(participant_id=p.id, point=point, value=value, late=late,
                             study_version=config.STUDY_VERSION, software_commit=config.SOFTWARE_COMMIT,
                             elapsed_s=round(minutes_since(p.task_started_at) * 60, 1)
                             if p.task_started_at else None))
    if late:
        _stop(db, p, "time_cap")
    db.commit()
    if late:
        return RedirectResponse("/final", status_code=303)
    return RedirectResponse("/surprise" if point == "baseline" else "/trial", status_code=303)


@app.get("/surprise", response_class=HTMLResponse)
def surprise_intro(request: Request, db=Depends(get_db)):
    # Deliberately says nothing about animals: the gorilla must be unexpected.
    return render(request, "surprise.html", current(request, db))


def _surprise_answered(p):
    # The surprise image is trial 0; its questions belong right after it.
    return bool(p.plan) and p.current_trial >= 1


@app.get("/notice", response_class=HTMLResponse)
def notice_page(request: Request, db=Depends(get_db)):
    return render(request, "notice.html", current(request, db))


@app.post("/notice")
def notice(request: Request, noticed: str = Form(...), db=Depends(get_db)):
    # Asked on its own page, before the gorilla is named, so the word cannot prompt the answer.
    p = current(request, db)
    if not _surprise_answered(p):
        return RedirectResponse(next_step(db, p), status_code=303)
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
    if not _surprise_answered(p):
        return RedirectResponse(next_step(db, p), status_code=303)
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
    in_plan = list(dict.fromkeys(t["task"] for t in (p.plan or []) if t["task"] in PLUGINS))
    library_instr = [PLUGINS[t].text.get(p.ui_lang, PLUGINS[t].text["en"])["instr"] for t in in_plan]
    return render(request, "instructions.html", p, has_reading_task=has_reading_task,
                  library_instr=library_instr, **names)


@app.get("/trial", response_class=HTMLResponse)
def trial_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not p.consented or not p.plan:
        return RedirectResponse(next_step(db, p), status_code=303)
    if not _ended(p) and _past_deadline(p):
        # Safety maximum reached (stated in the consent text): skip whatever is left.
        _stop(db, p, "time_cap")
        db.commit()
    if _ended(p):
        return RedirectResponse("/final", status_code=303)
    if p.current_trial == 0 and not _fatigue_done(db, p, "baseline"):
        return RedirectResponse("/fatigue?point=baseline", status_code=303)
    if p.current_trial >= 1 and p.noticed_unusual is None:
        return RedirectResponse("/notice", status_code=303)
    if p.current_trial >= 1 and p.saw_gorilla is None:
        return RedirectResponse("/notice2", status_code=303)
    trial = p.plan[p.current_trial]
    prev = p.plan[p.current_trial - 1] if p.current_trial else None
    if trial.get("round") and prev and prev.get("round") and prev["round"] < trial["round"]:
        point = f"after_round_{prev['round']}"
        if not _fatigue_done(db, p, point):
            return RedirectResponse(f"/fatigue?point={point}", status_code=303)
    img = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]
    tg = img["target"]
    plugin = PLUGINS.get(trial["task"])
    # The clue exactly as shown (library tasks carry their own text; core clues are built here).
    clue = (plugin.text[trial["clue_lang"]].get("clue", "") if plugin else
            make_clue(trial["task"], trial["clue_lang"], img["id"], tg, img.get("width"), img.get("height")))
    shown_at = now()
    if trial.get("round") and p.deadline_at is None:
        # The first scored stimulus starts the hard cap. Written once; never renewed.
        p.cap_started_at = shown_at
        p.deadline_at = shown_at + timedelta(minutes=config.SESSION_LIMIT_MIN)
    p.trial_views += 1
    if p.task_started_at is None:
        p.task_started_at = shown_at
    p.presented = {"index": p.current_trial, "at": shown_at.isoformat(), "clue": clue,
                   "versions": trial_versions(trial["task"], trial["clue_lang"])}
    db.commit()
    session = _session_ctx(p)
    if plugin:
        return render(request, "plugin_trial.html", p, trial=trial, img=img, plugin=plugin,
                      text=plugin.text[trial["clue_lang"]], clue_dir=direction(trial["clue_lang"]),
                      n=p.current_trial + 1, rounds=config.ROUNDS, timeout=plugin.timeout_ms, try_mode=False,
                      session=session)
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
                  timeout=config.TRIAL_TIMEOUT_MS, session=session)


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


# ---------- trial submission ----------

# Browser-reported times: finite, not negative, and not absurdly long.
Ms = Annotated[float | None, Field(ge=0, le=config.MAX_REPORTED_MS, allow_inf_nan=False)]
Coord = Annotated[float | None, Field(ge=-100_000, le=100_000, allow_inf_nan=False)]
MAX_RESPONSE_CHARS = 2_000_000


class Click(BaseModel):
    x: Coord  # natural image pixels
    y: Coord
    t_ms: Ms  # since clue and image appeared


class Timing(BaseModel):
    """Plugin screens: when the page appeared, when the task was started (once), the
    first response after that, and completion. All in ms from page load."""
    model_config = ConfigDict(extra="ignore")
    instr_ms: Ms = None           # time on the instruction screen before Start
    start_ms: Ms = None
    first_response_ms: Ms = None
    complete_ms: Ms = None


class TrialIn(BaseModel):
    trial_index: int = Field(ge=0)
    rt_ms: Ms = None
    click_x: Coord = None  # in natural image pixels, for the final click
    click_y: Coord = None
    # Every click on the image, in order (search, scan, dice, surprise).
    clicks: list[Click] | None = Field(None, max_length=5000)
    false_clicks: int = Field(0, ge=0, le=100_000)
    timed_out: bool = False
    effort: int | None = Field(None, ge=1, le=9)
    # Corsi: squares clicked; reading: option chosen; rule: "A"/"B";
    # operation span: {"recall": [word ids], "sums": [true/false/null per sum]}
    response: Any = None
    focus_lost: int = Field(0, ge=0, le=100_000)
    timing: Timing | None = None


def _finite(value):
    """No NaN or infinity anywhere inside a response."""
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return True


def _response_error(data):
    try:
        if not _finite(data.response):
            return "non_finite_number"
        if len(json.dumps(data.response)) > MAX_RESPONSE_CHARS:
            return "response_too_large"
    except (RecursionError, ValueError, TypeError):
        return "invalid_response"
    return None


def _on_target(x, y, tg):
    return math.hypot(x - tg["x"], y - tg["y"]) <= tg["r"] * config.HIT_TOLERANCE


def _score(trial, tg, data):
    """(hit, false_clicks, metrics JSON, click summary). The server scores every trial
    itself so the browser cannot claim a hit."""
    false_clicks, metrics = data.false_clicks, None
    clicks = {"first_click_ms": None, "first_click_correct": None, "wrong_clicks": None}
    task = trial["task"]
    if task in PLUGINS:
        try:
            result = PLUGINS[task].logic.score(tg, ascii_digits(data.response))
        except Exception as exc:  # noqa: BLE001 - keep the raw response even if a scorer chokes
            return False, false_clicks, json.dumps({"response": data.response,
                                                    "score_error": type(exc).__name__}), clicks
        hit = bool(result["hit"]) and not data.timed_out
        false_clicks = int(result.get("errors", 0))
        metrics = json.dumps({"response": data.response, **result.get("metrics", {})})
    elif task == "corsi":
        expected = tg["sequence"] if tg["direction"] == "forward" else tg["sequence"][::-1]
        picked = data.response if isinstance(data.response, list) else []
        hit = not data.timed_out and picked == expected
        false_clicks = sum(1 for a, b in zip(picked, expected) if a != b) + abs(len(picked) - len(expected))
    elif task in ("reading", "rule"):
        hit = not data.timed_out and data.response == tg["answer"]
    elif task == "ospan":
        resp = data.response if isinstance(data.response, dict) else {}
        hit = not data.timed_out and resp.get("recall") == tg["words"]
        sums = resp.get("sums") or []
        # Wrong or missing sum judgements, counted separately from memory.
        false_clicks = sum(1 for k, sm in enumerate(tg["sums"]) if k >= len(sums) or sums[k] != sm["true"])
    else:
        hit = (not data.timed_out and data.click_x is not None and data.click_y is not None
               and _on_target(data.click_x, data.click_y, tg))
        if data.clicks is not None:
            on = [c.x is not None and c.y is not None and _on_target(c.x, c.y, tg) for c in data.clicks]
            clicks = {"first_click_ms": data.clicks[0].t_ms if on else None,
                      "first_click_correct": on[0] if on else None,
                      "wrong_clicks": sum(not h for h in on)}
            false_clicks = clicks["wrong_clicks"]
    return hit, false_clicks, metrics, clicks


def _stored_trial(db, p, index):
    # Earliest first: on a legacy database with duplicates, the first answer counts.
    return db.scalars(select(TrialResult).where(TrialResult.participant_id == p.id,
                                                TrialResult.trial_index == index)
                      .order_by(TrialResult.id).limit(1)).first()


def _trial_row(p, index, data, late, partial, complete=True):
    """Build (not add) the row for trial `index`, using the version stamps of the page
    that showed it when they match."""
    trial = p.plan[index]
    tg = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]["target"]
    hit, false_clicks, metrics, clicks = _score(trial, tg, data)
    shown = p.presented if (p.presented or {}).get("index") == index else None
    versions = shown["versions"] if shown else trial_versions(trial["task"], trial["clue_lang"])
    raw = data.response
    if raw is None and data.clicks is not None:
        raw = {"clicks": [c.model_dump() for c in data.clicks]}
    return TrialResult(participant_id=p.id, trial_index=index, task=trial["task"],
                       image_id=trial["image_id"], target_object=tg.get("object"),
                       clue_lang=trial["clue_lang"], condition=trial["condition"], practice=trial["practice"],
                       rt_ms=data.rt_ms, hit=hit and complete, timed_out=data.timed_out,
                       false_clicks=false_clicks, effort=data.effort, focus_lost=data.focus_lost,
                       response=json.dumps(raw) if raw is not None else None, metrics=metrics,
                       timing=data.timing.model_dump_json() if data.timing else None,
                       reloads=max(0, p.trial_views - 1), round=trial.get("round"),
                       elapsed_s=round(minutes_since(p.task_started_at) * 60, 1),
                       presented_at=datetime.fromisoformat(shown["at"]) if shown else None,
                       clue_text=shown.get("clue") if shown else None,
                       late=late, partial=partial, **clicks, **versions)


def _after(p, trial_index):
    """Next page after trial `trial_index` has been stored."""
    if p.stop_reason is not None:
        return "/final"
    if p.plan[trial_index]["task"] == "surprise":
        return "/notice"
    return "/trial" if p.current_trial < len(p.plan) else "/final"


def _trial_phase_error(db, p, index):
    if not p.consented or not p.plan or not _fatigue_done(db, p, "baseline"):
        return "out_of_phase"
    if index >= 1 and (p.noticed_unusual is None or p.saw_gorilla is None):
        return "out_of_phase"
    return None


@app.post("/api/trial")
def record_trial(request: Request, data: TrialIn, db=Depends(get_db)):
    p = current(request, db)
    if err := _trial_phase_error(db, p, data.trial_index):
        return _api_error(db, p, err)
    # Idempotent: a retried or doubled submission gets the stored answer back.
    if stored := _stored_trial(db, p, data.trial_index):
        return {"ok": True, "hit": stored.hit, "next": _after(p, data.trial_index), "duplicate": True}
    # After a stop, only the trial that was in progress may still arrive (kept, flagged late).
    expected = p.quit_trial if p.stop_reason is not None else p.current_trial
    if expected is None or data.trial_index != expected or expected >= len(p.plan):
        return _api_error(db, p, "out_of_order")
    if err := _response_error(data):
        return _api_error(db, p, err, status=422)
    late = _past_deadline(p)
    row = _trial_row(p, data.trial_index, data, late=late, partial=False)
    try:
        db.add(row)
        if p.stop_reason is None:
            # Atomic transition: only advances from exactly this trial.
            res = db.execute(update(Participant).where(Participant.id == p.id,
                                                       Participant.current_trial == data.trial_index)
                             .values(current_trial=data.trial_index + 1, trial_views=0))
            if res.rowcount != 1:
                raise IntegrityError("advance", None, Exception("trial already advanced"))
            p.current_trial = data.trial_index + 1
            if late:
                # Kept but flagged; the cap then ends the session at the next trial.
                _stop(db, p, "time_cap", at_trial=p.current_trial)
        db.commit()
    except IntegrityError:
        db.rollback()
        db.refresh(p)
        if stored := _stored_trial(db, p, data.trial_index):
            return {"ok": True, "hit": stored.hit, "next": _after(p, data.trial_index), "duplicate": True}
        return _api_error(db, p, "conflict")
    db.refresh(p)
    return {"ok": True, "hit": row.hit, "next": _after(p, data.trial_index), "late": late}


class StopIn(BaseModel):
    trial_index: int = Field(ge=0)
    # The person: "exhausted" or "withdrawn". The page itself: "time_cap" when the
    # deadline passes, "technical_failure" when a task cannot run.
    reason: Literal["exhausted", "withdrawn", "time_cap", "technical_failure"] = "exhausted"
    # Whatever the browser had for the trial on screen; "complete": true when only the
    # effort rating was missing.
    partial: dict | None = None


def _save_partial(db, p, index, partial, late):
    """Keep the in-progress trial's data. Scored only if the browser says the response
    was complete; an unfinished trial is never a hit."""
    complete = partial.get("complete") is True
    try:
        data = TrialIn.model_validate({**partial, "trial_index": index})
        if _response_error(data):
            raise ValueError("invalid response")
        row = _trial_row(p, index, data, late=late, partial=True, complete=complete)
    except (ValidationError, ValueError, TypeError):
        trial = p.plan[index]
        row = TrialResult(participant_id=p.id, trial_index=index, task=trial["task"],
                          image_id=trial["image_id"], clue_lang=trial["clue_lang"],
                          condition=trial["condition"], practice=trial["practice"], round=trial.get("round"),
                          response=json.dumps(partial, default=str),
                          metrics=json.dumps({"invalid_partial": True}), late=late, partial=True,
                          **trial_versions(trial["task"], trial["clue_lang"]))
    db.add(row)


@app.post("/api/stop")
def stop_session(request: Request, data: StopIn, db=Depends(get_db)):
    """Stopping is always allowed; when and why it happens is data. Idempotent."""
    p = current(request, db)
    if p.stop_reason is not None or p.completed or p.final_skipped or (p.plan and _ended(p)):
        return {"ok": True, "next": next_step(db, p), "already": True}
    late = _past_deadline(p)
    if data.reason == "time_cap" and not _past_deadline(p, now() + timedelta(seconds=CLOCK_GRACE_S)):
        return _api_error(db, p, "deadline_not_reached")  # browser clock ran fast: resync
    # A tab showing an older trial cannot speak for the current one: its stop is still
    # honoured, but recorded as stale and its partial data is not attached to this trial.
    stale = bool(p.plan) and data.trial_index != p.current_trial
    reason = "time_cap" if late else "stale_request" if stale else data.reason
    at = p.current_trial if p.plan else None
    if (data.partial is not None and p.plan and not stale
            and _stored_trial(db, p, at) is None):
        _save_partial(db, p, at, data.partial, late=late and data.reason != "time_cap")
    try:
        stopped = _stop(db, p, reason, requested=data.reason, at_trial=at)
        db.commit()
    except IntegrityError:  # the trial row arrived meanwhile: record the stop without it
        db.rollback()
        db.refresh(p)
        stopped = _stop(db, p, reason, requested=data.reason, at_trial=at)
        db.commit()
    db.refresh(p)
    return {"ok": True, "next": next_step(db, p), "reason": p.stop_reason, "already": not stopped}


class QuitIn(BaseModel):
    trial_index: int = Field(ge=0)


@app.post("/api/quit")
def quit_early(request: Request, data: QuitIn, db=Depends(get_db)):
    """The "I'm exhausted" button on pages loaded before /api/stop existed."""
    return stop_session(request, StopIn(trial_index=data.trial_index, reason="exhausted"), db)


# ---------- end of session ----------

def attention_options(p):
    """Correct answer: the target of the practice search scene, which everyone saw.
    Wrong answers: objects that never appear as a target anywhere in the study."""
    images = {i["id"]: i for i in load_manifest()["images"]}
    practice = next((t for t in (p.plan or []) if t["practice"] and t["task"] == "search"), None)
    if practice is None:
        return None, []
    correct = images[practice["image_id"]]["target"]["object"]
    options = [correct, *DECOY_OBJECTS[:3]]
    random.Random(p.id).shuffle(options)
    return correct, options


def _seen_words(db, p):
    """Distinct (language, condition, word-id) exposures from completed OSPAN trials.

    The vocabulary index is reused across translations. Keying only by word-id
    silently drops an L2 exposure when the same index was already seen in L1.
    """
    images = {i["id"]: i for i in load_manifest()["images"]}
    seen = set()
    for tr in db.scalars(select(TrialResult).where(TrialResult.participant_id == p.id,
                                                   TrialResult.task == "ospan",
                                                   TrialResult.practice.is_(False),
                                                   TrialResult.partial.is_(False))):
        for word_id in images[tr.image_id]["target"]["words"]:
            seen.add((tr.clue_lang, tr.condition, word_id))
    return seen


def _retention_items(p, seen):
    """Create a balanced, reproducible recognition check without losing L1/L2 overlap."""
    rng = random.Random(p.id + "retention")
    items = []
    n_words = len(LOCALES[p.l1]["clue"]["words"])
    foils = list(range(n_words - N_FOILS, n_words))  # reserved, never presented
    rng.shuffle(foils)
    for cond, lang in (("L1", p.l1), ("L2", p.l2)):
        mine = sorted({word_id for seen_lang, seen_cond, word_id in seen
                       if seen_lang == lang and seen_cond == cond})
        old = rng.sample(mine, min(4, len(mine)))
        new = [foils.pop() for _ in old]  # independent foils for each condition
        items += [{"word": k, "lang": lang, "cond": cond, "seen": True} for k in old]
        items += [{"word": k, "lang": lang, "cond": cond, "seen": False} for k in new]
    rng.shuffle(items)
    return items


@app.get("/retention", response_class=HTMLResponse)
def retention_page(request: Request, db=Depends(get_db)):
    """At the end of the session: up to four seen words and matched foils per language."""
    p = current(request, db)
    if not _ended(p):
        return RedirectResponse(next_step(db, p), status_code=303)
    seen = _seen_words(db, p)
    if not seen or p.retention is not None:
        return RedirectResponse("/final", status_code=303)
    items = _retention_items(p, seen)
    p.retention = items  # fixed now, so a reload shows the same list
    db.commit()
    shown = [(n, LOCALES[it["lang"]]["clue"]["words"][it["word"]], it["lang"], direction(it["lang"]))
             for n, it in enumerate(items)]
    return render(request, "retention.html", p, shown=shown)


@app.post("/retention")
async def retention(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not _ended(p):
        return RedirectResponse(next_step(db, p), status_code=303)
    form = await request.form()
    checked = {int(v) for v in form.getlist("checked") if str(v).isdigit()}
    if p.retention and not any("checked" in it for it in p.retention):
        p.retention = [{**it, "checked": n in checked} for n, it in enumerate(p.retention)]
        db.commit()
    return RedirectResponse("/final", status_code=303)


@app.get("/final", response_class=HTMLResponse)
def final_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if p.completed or p.final_skipped or not _ended(p):
        return RedirectResponse(next_step(db, p), status_code=303)
    if p.retention is None and _seen_words(db, p):
        return RedirectResponse("/retention", status_code=303)
    if p.retention is not None and not any("checked" in it for it in p.retention):
        return RedirectResponse("/retention", status_code=303)
    _, options = attention_options(p)
    # Outside the time cap. After a stop of any kind these questions are optional.
    return render(request, "final.html", p, optional=p.stop_reason is not None,
                  options=[(o, object_name(o, p.ui_lang)) for o in options])


@app.post("/final")
def final(request: Request, difficulty: int | None = Form(None, ge=1, le=9),
          attention: str | None = Form(None), fatigue: int | None = Form(None, ge=0, le=100),
          skip: str | None = Form(None), db=Depends(get_db)):
    p = current(request, db)
    if p.completed or p.final_skipped or not _ended(p):
        return RedirectResponse(next_step(db, p), status_code=303)
    optional = p.stop_reason is not None
    if optional and skip == "1":
        # Skipping never touches the stop record; it only notes the questions were skipped.
        p.final_skipped = True
        db.commit()
        return RedirectResponse("/debrief", status_code=303)
    if not optional and None in (difficulty, attention, fatigue):
        raise HTTPException(422, "Please answer every question")
    if fatigue is not None and not _fatigue_done(db, p, "final"):
        db.add(FatigueRating(participant_id=p.id, point="final", value=fatigue,
                             study_version=config.STUDY_VERSION, software_commit=config.SOFTWARE_COMMIT,
                             elapsed_s=round(minutes_since(p.task_started_at) * 60, 1)
                             if p.task_started_at else None))
    p.overall_difficulty = difficulty
    if attention is not None:
        p.attention_ok = attention == attention_options(p)[0]
    p.completed = True
    db.commit()
    return RedirectResponse("/debrief", status_code=303)


@app.get("/debrief", response_class=HTMLResponse)
def debrief(request: Request, db=Depends(get_db)):
    return render(request, "debrief.html", current(request, db))


# ---------- admin ----------

ADMIN_COOKIE = "admin"
ADMIN_TTL_S = 8 * 60 * 60


def _admin_token(expires: int) -> str:
    sig = hmac.new(config.ADMIN_KEY.encode(), f"admin:{expires}".encode(), "sha256").hexdigest()
    return f"{expires}.{sig}"


def _admin_cookie_ok(request) -> bool:
    raw = request.cookies.get(ADMIN_COOKIE, "")
    expires = raw.partition(".")[0]
    if not expires.isdigit() or int(expires) < time.time():
        return False
    return hmac.compare_digest(raw, _admin_token(int(expires)))


def _key_ok(key: str) -> bool:
    return bool(key) and hmac.compare_digest(key.encode(), config.ADMIN_KEY.encode())


def _admin_login(request, to: str):
    """Signed, HttpOnly session cookie for /admin only; the key itself is never stored."""
    resp = RedirectResponse(to, status_code=303)
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie(ADMIN_COOKIE, _admin_token(int(time.time()) + ADMIN_TTL_S), max_age=ADMIN_TTL_S,
                    httponly=True, samesite="strict", path="/admin",
                    secure=https or config.PUBLIC_DEPLOYMENT or config.IRB_APPROVED)
    return resp


def require_admin(request, key: str = ""):
    """None when the request may go on. A ?key= in the URL only logs in: it sets the
    cookie and redirects to the same page without the key, so the secret does not stay
    in links, history, or later request logs."""
    if key:
        if not _key_ok(key):
            raise HTTPException(403, "Forbidden")
        return _admin_login(request, request.url.path)
    if not _admin_cookie_ok(request):
        raise HTTPException(403, "Forbidden")
    return None


ADMIN_LOGIN_PAGE = """<!doctype html><meta charset="utf-8"><title>Admin</title>
<form method="post" action="/admin/login"><label>Admin key <input type="password" name="key"
autocomplete="current-password" required></label> <button type="submit">Log in</button></form>"""


@app.post("/admin/login")
def admin_login(request: Request, key: str = Form(...)):
    if not _key_ok(key):
        raise HTTPException(403, "Forbidden")
    return _admin_login(request, "/admin")


@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(ADMIN_COOKIE, path="/admin")
    return resp


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, key: str = "", db=Depends(get_db)):
    if not key and not _admin_cookie_ok(request):
        return HTMLResponse(ADMIN_LOGIN_PAGE)
    if redirect := require_admin(request, key):
        return redirect
    rows = db.execute(select(Participant.group, Participant.is_test, Participant.completed, func.count())
                      .group_by(Participant.group, Participant.is_test, Participant.completed)).all()
    return render(request, "admin.html", rows=rows, irb=config.IRB_APPROVED)


def _short_hash(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    except OSError:
        return ""


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


def session_end(p):
    """How the session ended: a stop reason, "plan_finished", or "incomplete_unknown"
    (page closed or connection lost: nothing tells us why)."""
    if p.stop_reason:
        return p.stop_reason
    if p.quit_early:  # rows from before stop reasons were stored
        return "exhausted"
    if p.time_capped:
        return "time_cap"
    if p.plan and p.current_trial >= len(p.plan):
        return "plan_finished"
    return "incomplete_unknown"


def _v(value):
    # Stored version stamps only; rows from before stamps existed say so honestly.
    return value or "unknown"


def _csv(header, rows, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


SESSION_COLS = ["participant_id", "is_test", "created_at", "consented", "ui_lang", "group", "age",
                "education_years", "years_reading_images", "native_lang", "l2_age_acquired", "l1", "l2",
                "l1_reading", "l2_reading", "eligible", "equal_comfort", "counterbalance",
                "planned_trials", "current_trial", "n_trials_recorded", "task_started_at", "cap_started_at",
                "deadline_at", "session_end", "stop_reason", "stop_requested", "stopped_at", "stop_elapsed_s",
                "stop_clock_basis", "quit_trial", "quit_elapsed_s", "completed", "final_skipped",
                "attention_ok", "overall_difficulty", "session_versions"]


def _session_row(p, n_trials):
    return [p.id, p.is_test, _iso(p.created_at), p.consented, p.ui_lang, p.group, p.age,
            p.education_years, p.years_reading_images, p.native_lang, p.l2_age_acquired, p.l1, p.l2,
            p.l1_reading, p.l2_reading, p.eligible, p.equal_comfort, p.counterbalance,
            len(p.plan) if p.plan else 0, p.current_trial, n_trials, _iso(p.task_started_at),
            _iso(p.cap_started_at), _iso(p.deadline_at), session_end(p), p.stop_reason, p.stop_requested,
            _iso(p.stopped_at), p.stop_elapsed_s, p.stop_clock_basis, p.quit_trial, p.quit_elapsed_s,
            p.completed, p.final_skipped, p.attention_ok, p.overall_difficulty,
            json.dumps(p.versions) if p.versions else "unknown"]


# One row per stored trial. "response" is the complete raw response JSON, "metrics" the
# library task's full scores, "timing" the browser's timing envelope (all JSON text).
# rt_ms is the reported response time whether or not the answer was right.
EXPORT_COLS = ["participant_id", "is_test", "group", "age", "education_years", "years_reading_images",
               "native_lang", "l2_age_acquired", "l1", "l2", "l1_reading", "l2_reading",
               "eligible", "equal_comfort", "counterbalance", "attention_ok", "completed", "time_capped",
               "quit_early", "quit_elapsed_s", "quit_trial",
               "noticed_unusual", "saw_gorilla", "knew_gorilla_study",
               "trial_index", "round", "elapsed_s", "task", "image_id", "target_object",
               "clue_lang", "condition", "practice", "rt_ms", "hit", "timed_out", "false_clicks", "effort",
               "reloads", "focus_lost", "response", "study_version", "stimuli_version", "translation_version",
               "ret_l1_hits", "ret_l1_false_alarms", "ret_l2_hits", "ret_l2_false_alarms",
               "session_end", "stop_reason", "stopped_at", "cap_started_at", "deadline_at",
               "presented_at", "received_at", "late", "partial",
               "first_click_ms", "first_click_correct", "wrong_clicks", "metrics", "timing",
               "software_commit", "task_text_version", "clue_text"]


@app.get("/admin/export.csv")
def export(request: Request, key: str = "", db=Depends(get_db)):
    if redirect := require_admin(request, key):
        return redirect
    rows = []
    for tr, p in db.execute(select(TrialResult, Participant).join(Participant)
                            .order_by(Participant.created_at, TrialResult.trial_index, TrialResult.id)):
        rows.append([p.id, p.is_test, p.group, p.age, p.education_years, p.years_reading_images,
                     p.native_lang, p.l2_age_acquired, p.l1, p.l2, p.l1_reading, p.l2_reading,
                     p.eligible, p.equal_comfort, p.counterbalance, p.attention_ok, p.completed, p.time_capped,
                     p.quit_early, p.quit_elapsed_s, p.quit_trial,
                     p.noticed_unusual, p.saw_gorilla, p.knew_gorilla_study,
                     tr.trial_index, tr.round, tr.elapsed_s, tr.task,
                     tr.image_id, tr.target_object, tr.clue_lang, tr.condition, tr.practice, tr.rt_ms, tr.hit,
                     tr.timed_out, tr.false_clicks, tr.effort, tr.reloads, tr.focus_lost, tr.response,
                     _v(tr.study_version), _v(tr.stimuli_version), _v(tr.translation_version),
                     *retention_summary(p),
                     session_end(p), p.stop_reason, _iso(p.stopped_at), _iso(p.cap_started_at),
                     _iso(p.deadline_at), _iso(tr.presented_at), _iso(tr.created_at), tr.late, tr.partial,
                     tr.first_click_ms, tr.first_click_correct, tr.wrong_clicks, tr.metrics, tr.timing,
                     _v(tr.software_commit), _v(tr.task_text_version), tr.clue_text])
    return _csv(EXPORT_COLS, rows, "trials.csv")


@app.get("/admin/sessions.csv")
def export_sessions(request: Request, key: str = "", db=Depends(get_db)):
    """One row per session, including sessions that stopped before any scored trial."""
    if redirect := require_admin(request, key):
        return redirect
    counts = dict(db.execute(select(TrialResult.participant_id, func.count())
                             .group_by(TrialResult.participant_id)).all())
    rows = [_session_row(p, counts.get(p.id, 0))
            for p in db.scalars(select(Participant).order_by(Participant.created_at))]
    return _csv(SESSION_COLS, rows, "sessions.csv")


@app.get("/admin/fatigue.csv")
def export_fatigue(request: Request, key: str = "", db=Depends(get_db)):
    if redirect := require_admin(request, key):
        return redirect
    rows = [[p.id, p.is_test, p.group, p.age, p.education_years, p.l1, p.l2,
             p.equal_comfort, f.point, f.value, f.elapsed_s, _v(f.study_version), f.late,
             _v(f.software_commit), _iso(f.created_at)]
            for f, p in db.execute(select(FatigueRating, Participant).join(Participant)
                                   .order_by(Participant.created_at, FatigueRating.created_at))]
    return _csv(["participant_id", "is_test", "group", "age", "education_years", "l1", "l2",
                 "equal_comfort", "point", "value", "elapsed_s", "study_version", "late",
                 "software_commit", "received_at"], rows, "fatigue.csv")
