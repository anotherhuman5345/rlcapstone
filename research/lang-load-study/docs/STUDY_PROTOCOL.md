# Study protocol (draft for mentor review)

Status: draft. The demo works, but this protocol is **not ready for confirmatory data
collection**. Most priority-0 items of the October 2026 review (F01-F05, F07, F08) are
fixed and tested. A proposed F06 retention correction and regression tests are on a
review branch; the full test suite and deployment verification must pass before that
item is considered closed. Before collection, native speakers must review the study
languages, a design-specific power analysis must be approved, and written ethics (IRB)
approval must exist. Any protocol change needs the investigator's approval first.

## Research questions
1. **Primary.** Within the same person, is performance on a task worse (slower, less
   accurate, rated as more effortful) when the clue is in their less comfortable
   language (L2) than when it is in their most comfortable language (L1)?
2. **Inattentional blindness.** Is an L2 clue on the surprise image associated with a
   lower rate of noticing an unexpected object (a gorilla in a scan)? This one is
   between people.
3. **Time on task.** During a session that runs until self-declared exhaustion (or the
   60-minute safety maximum), how does performance change with elapsed time, and does
   the L1-L2 difference get larger or smaller over the session?
4. **Groups (exploratory).** Do these effects differ between the participant groups
   (high school, university, adult not in school, PhD student, professor, physician,
   radiologist)? These are descriptive group comparisons, not tests of what age or
   education *cause*.

## What this design estimates

This is a **mixed-language, within-person performance experiment**. In every round,
each of the seven core tasks appears twice: once with an L1 clue and once with an L2
clue, shuffled together (`config.ROUND_MIX`, `app/plan.py`). So L1 and L2 items are
interleaved all through the session.

What the design can estimate:
- **The within-person L2 cost:** the difference between a person's L2-clue items and
  their L1-clue items on the same task, in a session where both languages are mixed.
- **How that difference changes with elapsed time or round number.**
- **The gorilla comparison**, between people, because the surprise clue language is
  assigned between people.

What the design **cannot** estimate:
- **Language-specific exhaustion.** Time to exhaustion is one number per session, and
  every session contains both languages in equal amounts. So the time when someone
  pressed "I'm exhausted" cannot be attributed to L1 or to L2. I will not describe
  anyone's stopping time as "L2 fatigue" or "L1 fatigue".
- **The cost of working only in L2.** Because the languages alternate, the L2 cost
  measured here includes whatever happens when you switch between languages. It may
  differ from the cost in a session that is entirely in one language.

Time to exhaustion is still useful as a **session-level** outcome (for example,
compared between groups, or related to fatigue ratings), as long as it is described
that way.

### A possible follow-up (not built, not approved)
To ask whether people tire sooner in L2 than in L1, a different design would be needed:
**single-language sessions**, where each person does one session entirely in L1 and
another entirely in L2, with the order counterbalanced across people (and matched task
forms and platform). That would need separate sessions per person, a way to link them
without names, and a new protocol. It does not exist in the code and it is only an idea
for now; it would need investigator approval before any work on it.

## Group comparisons

The groups differ from each other in many ways at once, so a difference between two
groups cannot be pinned on one characteristic. The table says what each comparison
can and cannot tell us.

| Compare | They differ in (among other things) | What I can say |
|---|---|---|
| High school students vs. adults (not students) | Age, years of education, being in school now, occupation, daily reading and screen habits | Whether the groups differ, on average. Not that age causes the difference |
| Adults vs. PhD students / professors | Education, but also age, occupation, how much academic reading and testing they do, language use at work | Whether the groups differ. Not that education causes it |
| PhD students / professors vs. radiologists | Image-reading experience, but also medical training, occupation, age, and familiarity with the gorilla study | Whether radiologists differ, especially on the scan task. Not that expertise alone causes it |
| Radiologists vs. other physicians | Radiology training, but also specialty choice (people who choose radiology may differ beforehand), age, years in practice | A descriptive difference. With small groups, mostly descriptive |

To make age and education less tangled, recruitment should aim for **overlap**: for
example, adults with and without degrees across similar ages, and university students
of different ages. Age and years of education will be entered as measured variables
where the numbers allow, instead of only being implied by group.

### Alternative explanations to keep in mind
Any difference between conditions, groups or time points could come from, or be mixed
with:
- **Age**, **education** and **occupation**, which travel together across the groups.
- **Practice:** people get faster at a task as they repeat it, which can hide or mimic
  fatigue.
- **Item difficulty:** equal task counts per round do not make items equally hard.
  Items are paired by structure, but real difficulty varies from item to item.
- **Selective stopping:** people choose when to stop. Late rounds only include people
  who kept going, who may be more motivated, less tired, or more skilled. So "late in
  the session" is not the same set of people as "early in the session".
- **Language switching:** alternating languages costs something by itself, and that
  cost may differ between people.
- **Translation quality:** the 29 non-English versions are machine translations that
  have not been reviewed, so an "L2 cost" might partly be a translation problem.
- **Reading comfort and proficiency:** self-ratings are rough; two people who both
  call a language their L2 can read it very differently.
- **Device, time of day, sleep and motivation**, which are not measured yet.

## Hypotheses
- H1: Within a person, items with L2 clues are answered more slowly and rated as more
  effortful than items with L1 clues (mixed-language context).
- H2: Fewer people notice the gorilla when the surprise clue is in L2.
- H3: The L1-L2 difference changes with elapsed time in the session. (Whether
  performance itself goes down late in the session is described, but practice and
  selective stopping make it hard to interpret; see above.)
- H4 (exploratory): Radiologists find the planted object in scans faster than other
  groups, but may be no better at noticing the gorilla (Drew, Võ & Wolfe, 2013). Group
  differences by age and education are exploratory and descriptive.

There is no hypothesis about L1 versus L2 time to exhaustion, because this design
cannot test it (see "What this design estimates").

## Why this is framed as a presentation effect, not a trait claim
Earlier claims of a general "bilingual advantage" have often failed to replicate.
This study does not compare bilinguals with monolinguals. It compares the same
bilingual person under two presentation conditions, so each person serves as their
own comparison for the L1-L2 difference. (The gorilla question is the exception: it is
compared between people, because the surprise only works once.)

## Procedure (until self-declared exhaustion; 60-minute safety maximum)
1. Consent and background questions (about 3 minutes).
2. Surprise image: find a small ring; a gorilla is also present and never mentioned.
   Then, on separate pages: "Did you notice anything unusual?"; "Did you see a gorilla?";
   "Had you heard of the invisible-gorilla study?". Then a one-line explanation.
3. One practice item per task, in the comfortable language, not scored.
4. Rounds of 14 items: 2 of each of the seven core tasks (search scene, scan, dice
   board, Corsi blocks, reading passage, rule card, operation span), one with an L1
   clue and one with an L2 clue, shuffled together. A 0-100 fatigue rating follows
   every round. Rounds continue until the person presses "I'm exhausted" or the
   60-minute maximum is reached; there are enough rounds (24) that the maximum comes
   first. Then a word-retention check and the final questions.

The session normally ends with the "I'm exhausted" button. Both the button and the
60-minute maximum are my study choices, not values from the literature (see
`TASK_SOURCES.md`).

Known problems with the procedure as coded (from the review):
- Fixed: the 60-minute limit now counts from the first scored item (consent,
  background, instructions and practice excluded), is stored once and is enforced on
  every screen and every write (F01). This clock origin is my proposal and needs my
  mentor's approval.
- Fixed: "I'm exhausted" and an ordinary "Stop / withdraw" are separate; the time-limit
  stop, a stale browser tab and technical failures are recorded as their own reasons,
  and the half-finished trial is kept (F05).
- Reading passages now exist in all 30 languages, so every language pair gets the same
  core battery (F16 for the core tasks; library tasks still depend on which tasks are
  chosen).
- The English consent text now names the Stop / withdraw button, the optional final
  questions and the clock origin. The 29 unverified translations must be brought into
  alignment through human translation review before they can be approved for study use.

The 64 library tasks (`app/tasks/`) are not part of this procedure. They can be tried
one at a time at `/try`, and they are only for demonstration until a decision is made
to add any of them.

## Participants
- Inclusion: reads two of the study's 30 languages, with self-rated reading of 3 or
  more (on 1-7) in each. For real data collection, only languages whose translations
  have been reviewed by a native speaker can be used.
- High school students with parent/guardian permission for minors; adults not in
  school; PhD students and professors; physicians; radiologists and residents.
- Recruitment should overlap in age and education across groups where possible (see
  "Group comparisons").

## Sample size and power

I have **not** done a power analysis for this design yet. The earlier rough statements
("30-40 people per group gives good power") were not calculated for this model and
I have removed them. A design-specific power analysis is still to be finalized with my
mentor, before recruitment numbers are fixed. The exploratory sensitivity simulator
in `analysis/power_sensitivity.py` helps compare hypothetical scenarios but does NOT
replace fitting the approved mixed model to suitable pilot-based assumptions.

How I plan to do it:
1. **Write down the exact primary model** (for H1: log RT by clue language, task and
   elapsed time, with random intercepts for participants and items, and a random
   language slope per participant if the data can support it).
2. **Choose the smallest effect worth detecting** (for example, an L2 cost of a certain
   percentage in response time) and justify it from earlier studies or pilot data.
3. **Get plausible numbers for the other parts of the model:** variance between people,
   between items, and residual noise, ideally from a small pilot.
4. **Simulate the stopping process too.** People stop at different times, so the number
   of trials per person varies. The simulation should draw stopping times from a
   realistic spread (including people who stop early), not assume everyone does all
   rounds.
5. **Simulate many fake data sets** for each candidate sample size, fit the same mixed
   model to each, and count how often the effect is detected. That proportion is the
   power. (Tools: for example `simr` in R, or a simulation loop in Python with
   `statsmodels`.)
6. **Do the same separately for the gorilla question** (one yes/no answer per person,
   between people), where the result depends heavily on the base rate of noticing, which
   is uncertain.
7. Groups that end up small (for example radiologists) will be reported descriptively
   only, and I will say that in advance.

## Measures
Time to correct click (search and scan) or the task-specific response time (the
definition differs by task, see review F11); found vs. timed out (30 s); false clicks;
mental effort (Paas 1-9) per item; elapsed time of every answer; round number; whether
the session hit the time limit; whether and when the person pressed "I'm exhausted";
the three surprise questions; 0-100 fatigue ratings; overall difficulty; attention check
(which object they searched for, against objects that never appeared); background
questionnaire (group, age, years of education, years reading medical images, first
language, age of L2 acquisition, reading proficiency in each language, most comfortable
reading language, or a stated tie).

The app does not ask for or store names, emails or IP addresses. The hosting platform
keeps its own access logs, which are separate and still need to be checked (review F21).

Raw data (fixed after the review): every response keeps its RT and full raw data,
search and scan record every click, task metrics and timing are exported (F04), and
study, software, stimulus and translation versions are stored when each trial is shown,
so later changes cannot rewrite what a person saw (F03).

## Exclusions (draft, to be finalised before collection)
Failed attention check; self-rated reading below 3/7 in either language; response
times under 200 ms; trials whose page was reloaded before answering (the image had
already been seen). Pressing "I'm exhausted" is not an exclusion: trials up to that
point are kept. For the gorilla, results are reported both with and without people who
already knew the study.

The analysis no longer drops sessions without a final questionnaire (review F07, fixed):
each analysis has its own inclusion rule, a person who stopped and left before the final
questions still counts for the stopping and performance analyses, and the report lists
every exclusion with its reason. These rules still need to be agreed before collection.

## Analysis plan
- H1: mixed-effects model, log RT ~ clue language x task (x group, exploratory), with
  random intercepts per person and per item, and a random language slope per person if
  supported; similar models for accuracy (logistic) and effort ratings. Task-specific
  outcomes will be used instead of one generic "hit" flag (review F12).
- H2: share who saw the gorilla by clue language (and by group, descriptively); logistic
  regression (saw ~ clue language + group) among people who did not know the study.
- H3: mixed model of log RT on elapsed minutes x clue language, with a log-time term for
  the early practice speed-up. A search for the minute where slowing starts
  (change-point) is **exploratory** only: choosing the best-fitting bend among many
  candidates overstates certainty, and a positive slope change can just mean that
  improvement slows down, not that people get worse (review F19).
- Time to exhaustion: a **session-level** outcome, described with a survival model by
  group (people stopped by the 60-minute maximum are censored), and compared with the
  fatigue ratings. It is not split by clue language, because every session mixes both.
  The survival code now handles tied times correctly (review F13, fixed and tested).
- Every group difference is reported as an association, together with the alternative
  explanations listed above.

## Task sources
Where each task comes from, how it was adapted, and which parts are my own choices:
see `TASK_SOURCES.md`.

## Open questions for the lab
1. IRB: which protocol or pathway should this fall under?
2. Estimand: is the mixed-language within-person design (this document) the one we
   want, or should single-language sessions be planned as a follow-up?
3. Clock: implemented from the first scored item, excluding consent, background,
   instructions and practice; confirm this decision in the signed-off IRB protocol.
   This is no longer an unresolved software behavior.
4. Images: can the lab provide ~50 de-identified scans (rounds, practice and
   the surprise image)?
5. Recruitment of radiologists and physicians: appropriate channel and approvals, and
   how to get overlapping ages and education levels across groups.
6. Translations: who can review the languages we actually need?
7. Power analysis: which pilot data or published estimates should feed the simulation?
8. Eye-tracking: would gaze data for the gorilla trial be useful and possible? (In the
   original study most radiologists who missed the gorilla looked right at it.)
9. Authorship and publication norms, if the work turns out well.
