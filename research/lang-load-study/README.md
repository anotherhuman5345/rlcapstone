# Language of the Clue: Visual Search, Bilingualism, and Expertise

A web platform for a cognitive load experiment: **does reading a clue in your
less comfortable language make visual search and other short tasks slower and
harder, and does that cost differ between groups with different experience and
education?**

Status: **the demo works. It is not ready for confirmatory data collection.**
No participant data has been collected. Most priority-0 problems from the October 2026
review are fixed and tested (session deadline, stop reasons, raw-data exports, stored
versions, exclusions, concurrent submissions, database column size); retention
bookkeeping (F06) is still open. Before real collection, the translations I use must
also be reviewed by native speakers, and ethics (IRB) approval must exist in writing.

## The question

Cognitive load theory (Sweller, Ayres & Kalyuga, 2011) says working memory can
hold only a few new elements at once. If a written clue is in a language you
read less comfortably, decoding the words should take working memory that would
otherwise go to searching the image. The prediction: slower search and higher
mental effort with a less comfortable language clue.

The question is personal. I am bilingual in English and Turkish, and while
reading the book I wondered whether the language of a note on an image changes
how hard it is for me to use it, and whether that differs between people of
different ages and education.

## What this design can and cannot show

This is a **mixed-language, within-person performance experiment**: every round has
both L1-clue and L2-clue items, interleaved. So it can measure each person's L2 cost
(L2 items compared with L1 items on the same task) and how that cost changes over the
session. It **cannot** say whether people tire sooner in one language: time to
exhaustion is one number per session, and every session mixes both languages, so it
cannot be attributed to L1 or L2. A version with single-language sessions (one session
all in L1, one all in L2, order counterbalanced) would be needed for that. It is only a
possible follow-up; it is not built and would need my mentor's approval.

Group comparisons (for example high school vs. adults) are associations. The groups
differ in age, education, occupation, practice and more at the same time, so a
difference cannot be pinned on one of these. The protocol lists the alternative
explanations.

## Design

People keep going **until they feel exhausted** and press the "I'm exhausted" button; the time it takes is the main (self-declared, session-level) fatigue measure. A safety maximum ends every session **60 minutes** (`SESSION_LIMIT_MIN`) after the first scored picture (consent, background, instructions and practice do not count), and the consent text says so. The deadline is stored once and enforced on every task screen and every write; the final questions are outside it and optional after any stop.

| Part | What happens | Compared |
|---|---|---|
| 1. Surprise image (once, first) | Find a small white ring on a scan. An unannounced gorilla is also in the image. Then: "Anything unusual?", "Did you see a gorilla?", "Had you heard of the invisible-gorilla study?" | **Between people:** half get the clue in L1, half in L2 |
| 2. Practice | One practice item per core task, comfortable language, not scored | — |
| 3. Rounds | Rounds of 14 items, 2 of each of the 7 core tasks (one L1, one L2, shuffled together): search scene, scan, dice board, Corsi blocks, reading passage, rule card and operation span. The mix is set in `config.ROUND_MIX`. A 0-100 fatigue rating follows every round. Rounds continue until "I'm exhausted" or the 60-minute maximum. No picture, target or clue wording repeats in a row | **Within each person:** L1 vs. L2 items, and how that difference changes over time |
| 4. End | Word-retention check, final questions | — |

| Factor | Type | Levels |
|---|---|---|
| Clue language | within each person (rounds); between people (surprise) | L1 (most comfortable) vs. L2 (less comfortable) |
| Task | within each person | 7 core tasks: search scene, scan, dice board, Corsi blocks, reading passage, rule card, operation span |
| Time on task | within each person | Elapsed minutes / round number (until exhaustion, 60-minute maximum) |
| Session length | one per person | Time to "I'm exhausted" (session-level; not attributable to L1 or L2) |
| Group | between people | High school, university, adult (not a student), PhD student, professor, physician, radiologist (compared as groups, not as isolated causes) |

**Task library.** Besides the 7 core tasks there is a library of 64 more task modules
(`app/tasks/`), each of which can be tried alone at `/try`. None of them is in the
default round mix, so they do not run in study sessions. Where each core and library
task comes from, and what I changed, is in `docs/TASK_SOURCES.md`.

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
  - **Dice board:** a 9x9 grid with a star on the start square and two dice, A and B.
    The clue gives the directions in words ("move up as many squares as die A shows, then
    right as many as die B shows"); the numbers are only on the dice. Holding the
    numbers while reading the directions loads working memory, so this task is
    especially sensitive to the clue's language (instruction execution).
  - **Corsi blocks:** nine squares light up one by one; the clue says whether to click
    them back in the same or the reverse order. Both items of an L1/L2 pair have the same
    length and direction.
  - **Reading passage:** a short original passage and a question that needs two sentences
    combined (instructions and content both in the assigned language). Passages exist in
    English and Turkish so far (`app/reading/`); people whose two languages do not both
    have passages skip this task (so they get a different battery, which is a known
    problem).
  - **Rule card:** the clue states a sorting rule (by color, not-color, number of shapes,
    or an and/or combination); the person decides whether the card belongs to group A or B.
    Pairs share the rule type and the correct answer.
  - **Operation span with words:** judge 3-5 sums as correct or wrong; after each, a word
    appears for one second in the trial's language. Then click the words back in order.
    Memory and sum accuracy are scored separately.
  - **Word retention:** before the final questions, up to 8 words seen earlier (from L1
    and L2 trials) are mixed with the same number never shown; ticking the remembered
    ones gives hit and false-alarm rates for each language. The delay is not controlled,
    and the review found the word-to-language bookkeeping needs fixing (F06).
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
- **"I'm exhausted" button:** at the top of every item. This is how a session normally
  ends: the minute and round where someone stops (time to exhaustion) is the main,
  self-declared measure of fatigue for the session as a whole. Because every session
  mixes both languages, it cannot be split into L1 and L2 exhaustion. The button and
  the 60-minute maximum are my own study choices, not values from the literature or
  from the Cognitive Load Theory book.
- **Time on task:** every round has the same task mix, which removes one obvious
  difference between early and late rounds. It does not make time the only difference:
  items still vary in difficulty, people get practice, they switch languages all the
  time, and the people still going in late rounds are the ones who chose not to stop.
  There are 24 rounds, enough to reach the 60-minute safety maximum. Every answer
  carries its elapsed time, so the analysis can describe how performance changes over
  the session; looking for the minute where slowing starts is exploratory.
- **Fatigue:** "How mentally tired do you feel right now?" (0-100) at the start, after
  every round and at the end, kept separate from performance (`/admin/fatigue.csv`).
- **Equal comfort:** people can say they read both languages equally comfortably; the
  tie is stored rather than forcing a preference.
- **Quality flags:** reloaded trials and trials where the tab was hidden are recorded and
  dropped in analysis. Study, software, stimulus and translation versions are stored
  when each trial is shown; rows recorded before this change export "unknown".
- **Outcomes:** for search scenes and scans, time to the correct click (ms), whether
  the target was found within 30 s and false clicks; the other tasks have their own
  response-time and accuracy definitions. A 1-9 mental-effort rating (Paas scale)
  follows each item.
- **Data quality:** reloading a trial page restarts the clock after the image was
  already seen, so reloaded trials are recorded and dropped from analysis. People who
  rate either language below 3 of 7 can finish but are excluded (see protocol). The
  file of target locations is never served to the browser as a file.
- **Counterbalancing:** each image appears in L1 for half of participants and L2 for
  the other half; the surprise clue language alternates too; rotation runs separately
  within each group. Which images fall in which round is shuffled per person.

## Languages

The platform has text for **30 languages**: English, Chinese (Mandarin), Hindi, Spanish, French,
Arabic, Bengali, Portuguese, Russian, Urdu, Indonesian, German, Japanese, Marathi,
Telugu, Turkish, Hausa, Tamil, Swahili, Vietnamese, Filipino, Korean, Persian, Italian,
Punjabi, Gujarati, Thai, Amharic, Kannada and Polish. Each participant picks the
language they are **most comfortable** reading (L1) and another language they also read
(L2); clues alternate between those two. Arabic, Urdu and Persian display right to left.

Every language lives in `app/locales/<code>.json`: the interface text, plus the clue
vocabulary and grammar (word order, and agreement of "small" and the color with the
noun's gender or class). Check a file and print sample clues with
`python tools/check_locale.py <code> --all`.

English is the source. **The other 29 languages are machine translations and none has
been reviewed by a native speaker yet**, so they are for the demo only. Each
file has `"verified": false` until a native speaker has checked it. The 64 library
tasks also have their own text files in all 30 languages, with the same status. In demo mode every language can be tried; once
`IRB_APPROVED=1`, only verified languages can be chosen for clues. English is the source
and counts as verified.

See `docs/STUDY_PROTOCOL.md` for the estimand, hypotheses, the (still missing) power
analysis, and open questions.

## Run it locally

```bash
pip install -r requirements-dev.txt   # app + images, analysis, tests
python stimuli/generate_stimuli.py      # makes images + manifest (placeholder scans)
uvicorn app.main:app --reload           # open http://127.0.0.1:8000
pytest -q                               # automated tests
```

Admin page: `http://127.0.0.1:8000/admin?key=change-me` logs in (an HttpOnly cookie) and redirects to a URL without the key; the trial, session and fatigue CSV exports are linked from there.

## Analysis

```bash
python analysis/simulate.py                                       # FAKE data for testing
python analysis/analyze.py analysis/SIMULATED_trials.csv --include-test
python analysis/analyze.py trials.csv                             # real export
```

Primary model in the current script: mixed-effects regression on log response time,
`log_rt ~ condition * group * task` with a random intercept per participant. The
protocol lists the planned changes (item random effects, task-specific outcomes, an
exploratory-only change-point search, and fixes the review found). Group terms are
read as associations, not causes. No power analysis has been done yet; the protocol
explains how it will be done (by simulation for the mixed model).
**`SIMULATED_trials.csv` is made-up data to check the pipeline. It is not a result.**

## Before any real data collection

1. Fix the review's remaining priority-0 item (F06, retention bookkeeping).
2. Ethics/IRB approval in writing. Until then the site runs with `IRB_APPROVED=0`,
   shows a "demo only" banner, and marks every session as test data.
3. Replace placeholder scans with 50 de-identified images provided by the lab (48 for
   the rounds, 1 practice, 1 for the surprise gorilla):
   put them in `stimuli/real_scans/` (git-ignored) and run
   `python stimuli/generate_stimuli.py --real-scans`.
4. Have a native speaker check each language that will be used (`app/locales/<code>.json`),
   then set `"verified": true` in that file.
5. Do the design-specific power analysis and settle sample sizes with my mentor.
6. Set environment variables on the server:
   `ADMIN_KEY` (long random string), `DATABASE_URL` (e.g. Postgres), `IRB_APPROVED=1`, `IRB_NUMBER`.

## Deploying to rlcapstone.ai

The live study runs on **Vercel** (team UAD NGO, project `rlcapstone-study`) with a
**Supabase** Postgres database, at https://study.rlcapstone.ai. Vercel detects the
FastAPI app on its own; `requirements.txt` holds only what the web app needs, and
`.vercelignore` keeps analysis, tests and docs out of the deployment.

```bash
npx vercel deploy --prod --scope uad-ngo      # from this folder
```

Settings live in the Vercel project, never in the repo: `DATABASE_URL` (Supabase
transaction pooler, port 6543, as the `study_app` role, which can only see the `study`
schema), `ADMIN_KEY`, `IRB_APPROVED`, `IRB_NUMBER`. The app creates its tables on first
use and adds new columns automatically when a later version needs them.

Any other host that runs Python or Docker also works: the included `Dockerfile`
generates the images and starts the server on `$PORT` with a local SQLite file.
The server refuses to start with `IRB_APPROVED=1` or `PUBLIC_DEPLOYMENT=1` while `ADMIN_KEY` is still the default; set `PUBLIC_DEPLOYMENT=1` on every internet-facing host, demo included.

## Project layout

```
app/        web app (FastAPI): routes, database, bilingual text, clue builder, trial planner
app/templates, app/static   pages, styling, browser timing script
stimuli/    image generator (search scenes with varied targets, scans with faint planted objects)
analysis/   simulate.py (fake data), analyze.py (statistics)
tests/      automated tests
docs/       study protocol, task sources (TASK_SOURCES.md)
```

## Credits

Study idea grew out of reading *Cognitive Load Theory* at the suggestion of my
mentor at the Northwestern Hybrid Intelligence lab. My father and I worked out
the study design together; he also helped with technical problems.
