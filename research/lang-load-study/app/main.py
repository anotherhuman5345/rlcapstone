"""Web app: landing -> consent -> background -> instructions -> trials -> final -> debrief."""
import csv
import io
import math
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import config
from .clues import make_clue
from .db import Participant, SessionLocal, TrialResult, init_db
from .i18n import t
from .plan import build_plan, load_manifest

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="Language & Visual Search Study", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=config.ROOT / "app" / "templates")
COOKIE = "pid"


@app.get("/img/{name}")
def image(name: str):
    # Serve only the study images. The manifest (with every target's location)
    # stays private, so nobody can look up the answers.
    if name not in {i["file"] for i in load_manifest()["images"]}:
        raise HTTPException(404)
    return FileResponse(config.STIMULI_DIR / name)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def render(request, name, p=None, lang="en", **ctx):
    lang = p.ui_lang if p else lang
    return templates.TemplateResponse(request, name, {
        "_": t(lang), "lang": lang, "demo": not config.IRB_APPROVED,
        "irb_number": config.IRB_NUMBER, **ctx})


def current(request, db):
    pid = request.cookies.get(COOKIE)
    p = db.get(Participant, pid) if pid else None
    if p is None:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return p


@app.get("/", response_class=HTMLResponse)
def landing(request: Request, lang: str = "en"):
    lang = lang if lang in config.LANGUAGES else "en"
    return render(request, "landing.html", lang=lang)


@app.post("/start")
def start(ui_lang: str = Form("en"), db=Depends(get_db)):
    p = Participant(ui_lang=ui_lang if ui_lang in config.LANGUAGES else "en",
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
    return render(request, "background.html", p, groups=config.GROUPS)


@app.post("/background")
def background(request: Request, group: str = Form(...), age: int = Form(..., ge=10, le=99),
               education_years: int = Form(..., ge=0, le=40),
               years_reading_images: float = Form(0, ge=0, le=60),
               native_lang: str = Form(...), l2_age_acquired: int = Form(..., ge=0, le=99),
               en_reading: int = Form(..., ge=1, le=7), tr_reading: int = Form(..., ge=1, le=7),
               comfort: str = Form(...), db=Depends(get_db)):
    p = current(request, db)
    if group not in config.GROUPS or comfort not in config.LANGUAGES:
        raise HTTPException(400, "Invalid answer")
    p.group, p.age, p.education_years = group, age, education_years
    p.years_reading_images, p.native_lang, p.l2_age_acquired = years_reading_images, native_lang, l2_age_acquired
    p.en_reading, p.tr_reading = en_reading, tr_reading
    p.l1 = comfort
    p.l2 = "tr" if comfort == "en" else "en"
    p.eligible = min(en_reading, tr_reading) >= config.MIN_READING

    # Rotate counterbalance index within each group.
    n_in_group = db.scalar(select(func.count()).select_from(Participant)
                           .where(Participant.group == group, Participant.plan.is_not(None)))
    p.counterbalance = n_in_group % 4
    p.plan = build_plan(p.id, p.counterbalance, p.l1, p.l2)
    db.commit()
    return RedirectResponse("/instructions", status_code=303)


@app.get("/instructions", response_class=HTMLResponse)
def instructions(request: Request, db=Depends(get_db)):
    return render(request, "instructions.html", current(request, db))


@app.get("/trial", response_class=HTMLResponse)
def trial_page(request: Request, db=Depends(get_db)):
    p = current(request, db)
    if not p.plan:
        return RedirectResponse("/background", status_code=303)
    if p.current_trial >= len(p.plan):
        return RedirectResponse("/final", status_code=303)
    trial = p.plan[p.current_trial]
    p.trial_views += 1
    db.commit()
    img = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]
    tg = img["target"]
    clue = make_clue(trial["task"], trial["clue_lang"], tg["x"], tg["y"], img["width"], img["height"])
    return render(request, "trial.html", p, trial=trial, img=img, clue=clue,
                  n=p.current_trial + 1, total=len(p.plan), timeout=config.TRIAL_TIMEOUT_MS)


class TrialIn(BaseModel):
    trial_index: int
    rt_ms: float | None = None
    click_x: float | None = None  # in natural image pixels, for the final click
    click_y: float | None = None
    false_clicks: int = Field(0, ge=0)
    timed_out: bool = False
    effort: int | None = Field(None, ge=1, le=9)


@app.post("/api/trial")
def record_trial(request: Request, data: TrialIn, db=Depends(get_db)):
    p = current(request, db)
    if data.trial_index != p.current_trial or p.current_trial >= len(p.plan or []):
        raise HTTPException(409, "Out-of-order trial")
    trial = p.plan[p.current_trial]
    img = {i["id"]: i for i in load_manifest()["images"]}[trial["image_id"]]
    tg = img["target"]
    # The server re-checks the hit so the browser cannot claim one.
    hit = (not data.timed_out and data.click_x is not None and data.click_y is not None
           and math.hypot(data.click_x - tg["x"], data.click_y - tg["y"]) <= tg["r"] * config.HIT_TOLERANCE)
    db.add(TrialResult(participant_id=p.id, trial_index=p.current_trial, task=trial["task"],
                       image_id=trial["image_id"], clue_lang=trial["clue_lang"],
                       condition=trial["condition"], practice=trial["practice"],
                       rt_ms=data.rt_ms if hit else None, hit=hit, timed_out=data.timed_out,
                       false_clicks=data.false_clicks, effort=data.effort,
                       reloads=max(0, p.trial_views - 1)))
    p.current_trial += 1
    p.trial_views = 0
    db.commit()
    return {"ok": True, "hit": hit, "next": "/trial" if p.current_trial < len(p.plan) else "/final"}


@app.get("/final", response_class=HTMLResponse)
def final_page(request: Request, db=Depends(get_db)):
    return render(request, "final.html", current(request, db))


@app.post("/final")
def final(request: Request, difficulty: int = Form(..., ge=1, le=9), attention: str = Form(...), db=Depends(get_db)):
    p = current(request, db)
    p.overall_difficulty = difficulty
    p.attention_ok = attention == "red"
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


EXPORT_COLS = ["participant_id", "is_test", "group", "age", "education_years", "years_reading_images",
               "native_lang", "l2_age_acquired", "en_reading", "tr_reading", "l1", "l2",
               "eligible", "counterbalance", "attention_ok", "completed", "trial_index", "task", "image_id",
               "clue_lang", "condition", "practice", "rt_ms", "hit", "timed_out", "false_clicks", "effort",
               "reloads"]


@app.get("/admin/export.csv")
def export(key: str = "", db=Depends(get_db)):
    require_admin(key)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(EXPORT_COLS)
    for tr, p in db.execute(select(TrialResult, Participant).join(Participant)
                            .order_by(Participant.created_at, TrialResult.trial_index)):
        w.writerow([p.id, p.is_test, p.group, p.age, p.education_years, p.years_reading_images,
                    p.native_lang, p.l2_age_acquired, p.en_reading, p.tr_reading, p.l1, p.l2,
                    p.eligible, p.counterbalance, p.attention_ok, p.completed, tr.trial_index, tr.task,
                    tr.image_id, tr.clue_lang, tr.condition, tr.practice, tr.rt_ms, tr.hit,
                    tr.timed_out, tr.false_clicks, tr.effort, tr.reloads])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=trials.csv"})
