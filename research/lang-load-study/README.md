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

The whole session takes **at most 15 minutes**, for everyone.

| Part | What happens | Compared |
|---|---|---|
| 1. Surprise image (once, first) | Find a small white ring on a scan. An unannounced gorilla is also in the image. Then: "Anything unusual?", "Did you see a gorilla?", "Had you heard of the invisible-gorilla study?" | **Between people:** half get the clue in L1, half in L2 |
| 2. Practice | One search scene and one scan, comfortable language, not scored | — |
| 3. Rounds | Rounds of 8 pictures: 4 search scenes (find the named object) and 4 scans (find what is out of the ordinary), half with L1 clues and half with L2 clues. No picture, target or clue wording repeats in a row | **Within each person:** L1 vs. L2, and change over time |

| Factor | Type | Levels |
|---|---|---|
| Clue language | within each person (rounds); between people (surprise) | L1 (most comfortable) vs. L2 (less comfortable) |
| Task | within each person | Search scene vs. scan |
| Time on task | within each person | Elapsed minutes / round number |
| Group | between people | High school, university, adult (not a student), PhD student, professor, physician, radiologist |

- **No autopilot.** Pilot testers said that with a fixed target (always a red umbrella,
  always a monkey) the task became automatic after a few pictures and they stopped
  reading the clue. An unread clue cannot show a language effect, so nothing repeats:
  - **Search scene:** an original cluttered picture with its own target, a unique
    object-and-color pair (a green fish, a purple key, ...), among distractors that share
    its shape or its color (conjunction search). The clue names the target.
  - **Scan:** a grayscale medical image with a small, faint silhouette planted in it
    (cat, bird, key, house, ...). Object, size and contrast vary per picture; contrast
    is +16 to +22 gray levels over the background, half of the first version's +38.
    The clue never names it: it says something is out of the ordinary, the way a
    reader of a real scan looks for an abnormality. Nobody is asked to diagnose anything.
  - **Wording:** each clue uses one of several equivalent sentence patterns, the same
    pattern in both languages for a given picture.
- **Surprise gorilla:** the inattentional-blindness paradigm of Drew, Võ & Wolfe (2013),
  where 83% of radiologists missed a gorilla in a lung CT. It runs first, before anything
  mentions animals, because once someone knows about it the surprise is gone. The
  "unusual?" question gets its own page so the word "gorilla" cannot prompt the answer.
  Radiologists may know the study, so everyone is asked and the analysis reports
  results with and without those who knew.
- **Clue:** names what to find (search scenes only), the region of the image and the
  nearer edge, in English or Turkish. Both versions carry identical information.
- **"I'm exhausted" button:** under every picture. Stopping is always allowed; the
  minute and round where someone stops is recorded as a direct measure of fatigue.
- **Time on task:** every round has the same mix, so a change across rounds comes from
  time, not from a harder task. There are more rounds (12) than most people finish:
  at 14 minutes from the start page the session moves to the final questions. Every
  answer carries its elapsed time, so the analysis can look for the minute where
  slowing starts. If no decay appears within 15 minutes, that is reported as a finding
  and a longer follow-up can be proposed.
- **Outcomes:** time to the correct click (ms), whether the target was found within
  30 s, false clicks, and a 1-9 mental-effort rating (Paas scale) after each picture.
- **Data quality:** reloading a trial page restarts the clock after the image was
  already seen, so reloaded trials are recorded and dropped from analysis. People who
  rate either language below 3 of 7 can finish but are excluded (see protocol). The
  file of target locations is never served to the browser as a file.
- **Counterbalancing:** each image appears in L1 for half of participants and L2 for
  the other half; the surprise clue language alternates too; rotation runs separately
  within each group. Which images fall in which round is shuffled per person.

See `docs/STUDY_PROTOCOL.md` for hypotheses, sample size, and open questions.

## Run it locally

```bash
pip install -r requirements.txt
python stimuli/generate_stimuli.py      # makes images + manifest (placeholder scans)
uvicorn app.main:app --reload           # open http://127.0.0.1:8000
pytest -q                               # 8 tests
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
2. Replace placeholder scans with 50 de-identified images provided by the lab (48 for
   the rounds, 1 practice, 1 for the surprise gorilla):
   put them in `stimuli/real_scans/` (git-ignored) and run
   `python stimuli/generate_stimuli.py --real-scans`.
3. Have a native speaker proofread all Turkish text in `app/i18n.py` and `app/clues.py`.
4. Set environment variables on the server:
   `ADMIN_KEY` (long random string), `DATABASE_URL` (e.g. Postgres), `IRB_APPROVED=1`, `IRB_NUMBER`.

## Deploying to rlcapstone.ai

Any host that runs Python or Docker works (Render, Railway, Fly.io, a VPS). The
included `Dockerfile` installs everything, generates the images, and starts the
server on `$PORT`:

```bash
docker build -t lang-load-study .
docker run -p 8000:8000 -e ADMIN_KEY=<long-random-string> lang-load-study
```

Without Docker, the start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
The server refuses to start with `IRB_APPROVED=1` while `ADMIN_KEY` is still the default.

## Project layout

```
app/        web app (FastAPI): routes, database, bilingual text, clue builder, trial planner
app/templates, app/static   pages, styling, browser timing script
stimuli/    image generator (search scenes with varied targets, scans with faint planted objects)
analysis/   simulate.py (fake data), analyze.py (statistics)
tests/      automated tests
docs/       study protocol
```

## Credits

Study idea grew out of reading *Cognitive Load Theory* at the suggestion of my
mentor at the Northwestern Hybrid Intelligence lab. My father and I worked out
the study design together; he also helped with technical problems.
The first version of the code was drafted with an AI assistant (Claude); I have
studied, tested and changed it, and I can explain every part.
