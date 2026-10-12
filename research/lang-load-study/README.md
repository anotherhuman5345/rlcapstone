# Language of the Clue: Visual Search, Bilingualism, and Expertise

A web platform for a cognitive load experiment: **does reading a clue in your
less comfortable language slow down visual search, and do experience and
education change that cost?**

Status: **built and tested; awaiting mentor review and ethics (IRB) approval.
No participant data has been collected.**

## The question

Cognitive load theory (Sweller, Ayres & Kalyuga, 2011) says working memory can
hold only a few new elements at once. If a written clue is in a language you
read less comfortably, decoding the words should take working memory that would
otherwise go to searching the image. The prediction: slower search and higher
mental effort with a less comfortable language clue.

The question is personal. I am bilingual in English and Turkish, and while
reading the book I wondered whether the language of a note on an image changes
how hard it is for me to use it, and whether that changes as people get older
and more educated.

## Design

| Factor | Type | Levels |
|---|---|---|
| Clue language | within each person | L1 (most comfortable) vs. L2 (less comfortable) |
| Task | within each person | Search scene (find the red umbrella) vs. scan (find the planted monkey) |
| Group | between people | High school students, radiologists (optional: PhD students, professors) |

- **Search scene:** an original cluttered picture; the target is a small red umbrella
  among distractors that share its color or its shape (conjunction search).
- **Scan:** a grayscale medical image with a small, low-contrast monkey planted in it,
  inspired by the "invisible gorilla" study in radiology (Drew, Võ & Wolfe, 2013).
  Everyone does both tasks; nobody is asked to diagnose anything.
- **Clue:** names the region of the image and the nearer edge, in English or Turkish.
  Both versions carry identical information.
- **Outcomes:** time to the correct click (ms), whether the target was found within
  60 s, false clicks, and a 1-9 mental-effort rating (Paas scale) after each picture.
- **Counterbalancing:** each image appears in L1 for half of participants and L2 for
  the other half; task order alternates; rotation runs separately within each group.
  Trial order is shuffled per person. One unscored practice trial starts each task.

See `docs/STUDY_PROTOCOL.md` for hypotheses, sample size, and open questions.

## Run it locally

```bash
pip install -r requirements.txt
python stimuli/generate_stimuli.py      # makes images + manifest (placeholder scans)
uvicorn app.main:app --reload           # open http://127.0.0.1:8000
pytest -q                               # 4 tests
```

Admin page: `http://127.0.0.1:8000/admin?key=change-me` (CSV export from there).

## Analysis

```bash
python analysis/simulate.py                                       # FAKE data for testing
python analysis/analyze.py analysis/SIMULATED_trials.csv --include-test
python analysis/analyze.py trials.csv                             # real export
```

Primary model: mixed-effects regression on log response time,
`log_rt ~ condition * group * task` with a random intercept per participant.
**`SIMULATED_trials.csv` is made-up data to check the pipeline. It is not a result.**

## Before any real data collection

1. Ethics/IRB approval in writing. Until then the site runs with `IRB_APPROVED=0`,
   shows a "demo only" banner, and marks every session as test data.
2. Replace placeholder scans with de-identified images provided by the lab:
   put them in `stimuli/real_scans/` (git-ignored) and run
   `python stimuli/generate_stimuli.py --real-scans`.
3. Have a native speaker proofread all Turkish text in `app/i18n.py` and `app/clues.py`.
4. Set environment variables on the server:
   `ADMIN_KEY` (long random string), `DATABASE_URL` (e.g. Postgres), `IRB_APPROVED=1`, `IRB_NUMBER`.

## Deploying to rlcapstone.ai

Any host that runs Python works (Render, Railway, Fly.io, a VPS). Start command:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Run the stimulus generator
during the build step, or commit `stimuli/output/` with placeholder images only.

## Project layout

```
app/        web app (FastAPI): routes, database, bilingual text, clue builder, trial planner
app/templates, app/static   pages, styling, browser timing script
stimuli/    image generator (search scenes, scans with planted monkey)
analysis/   simulate.py (fake data), analyze.py (statistics)
tests/      automated tests
docs/       study protocol
```

## Credits

Study idea grew out of reading *Cognitive Load Theory* at the suggestion of my
mentor at the Northwestern Hybrid Intelligence lab. I wrote this code; where I got
help (for example, from my father on technical problems), I say so.
