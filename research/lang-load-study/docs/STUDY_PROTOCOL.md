# Study protocol (draft for mentor review)

## Research questions
1. **Primary.** Does a clue written in a person's less comfortable language (L2)
   slow visual search compared with the same clue in their most comfortable
   language (L1)?
2. **Inattentional blindness.** When attention is on a stated task, does an L2 clue
   make people less likely to notice an unexpected object (a gorilla in a scan)?
3. **Time on task.** As a session continues until self-declared exhaustion, when does performance
   start to decline, and does the L2 cost grow as people tire?
4. **Groups.** Do these effects differ by age, education and image-reading expertise?

## Group comparisons
| Compare | Isolates |
|---|---|
| High school students vs. adults (not students) | Age |
| Adults vs. PhD students / professors | Education |
| PhD students / professors vs. radiologists | Image-reading expertise (education held high) |
| Radiologists vs. other physicians | Radiology training specifically |

## Hypotheses
- H1: Search is slower and rated as more effortful with L2 clues.
- H2: Fewer people notice the gorilla when the surprise clue is in L2 (more of their
  working memory goes to decoding the clue).
- H3: Performance declines late in the session, and the L2 cost grows with time on task.
- H4 (exploratory): Radiologists find the planted object in scans faster than novices, but may
  be no better at noticing the gorilla (Drew et al., 2013). Effects of age and education
  are exploratory.

## Why this is framed as a presentation effect, not a trait claim
Earlier claims of a general "bilingual advantage" have often failed to replicate.
This study does not compare bilinguals with monolinguals. It compares the same
bilingual person under two presentation conditions, so each person is their own control.
(The gorilla question is the exception: it is compared between people, because the
surprise only works once.)

## Procedure (until self-declared exhaustion; 60-minute safety maximum)
1. Consent and background questions (about 3 minutes).
2. Surprise image: find a small ring; a gorilla is also present and never mentioned.
   Then, on separate pages: "Did you notice anything unusual?"; "Did you see a gorilla?";
   "Had you heard of the invisible-gorilla study?". Then a one-line explanation.
3. One practice item per task.
4. Identical rounds of 14 items (2 per task, one per language) until the person presses
   "I'm exhausted" or 60 minutes have passed since the start, then a word-retention
   check and the final questions. A 0-100 fatigue rating follows every round. Every
   search scene has its own named target and every scan its own unnamed, faint object
   ("something is out of the ordinary"); clue wording rotates, so nothing becomes
   automatic. The "I'm exhausted" button is the normal way to end; time to exhaustion
   is the primary self-declared fatigue outcome.

## Participants
- Inclusion: reads both English and Turkish (self-rated 3+ on 1-7 in each).
- High school students with parent/guardian permission for minors; adults not in
  school; PhD students and professors; physicians; radiologists and residents.

## Sample size (planning estimate)
- Language effect (within person): ~30-40 people per group gives good power for a
  medium effect.
- Gorilla (between people, one yes/no answer each): needs more people. About 40 per
  language per group (~80 per group) can detect a large difference (for example 50%
  vs. 80% missing). Smaller groups such as radiologists will be descriptive only.
- Final numbers to be set with mentor guidance.

## Measures
Time to correct click; found vs. timed out (30 s); false clicks; mental effort
(Paas 1-9) per picture; elapsed time of every answer; round number; whether the
session hit the time limit; whether and when the person pressed "I'm exhausted";
the three surprise questions; overall difficulty; attention check (which object they
searched for, against objects that never appeared); background questionnaire (group, age, years of education, years
reading medical images, first language, age of L2 acquisition, reading proficiency in
each language, most comfortable reading language). No names, emails, or IP addresses
are stored.

## Exclusions (decided in advance)
Incomplete sessions; failed attention check; self-rated reading below 3/7 in
either language; response times under 200 ms; trials whose page was reloaded
before answering (the image had already been seen). Pressing "I'm exhausted" is not
an exclusion: those people answer the final questions and their trials up to that
point are kept. For the gorilla, results are
reported both with and without people who already knew the study.

## Analysis plan
- H1: mixed-effects model, log RT ~ clue language x group x task, random intercept
  per person; same for effort ratings.
- H2: share who saw the gorilla by group and clue language; logistic regression
  (saw ~ clue language + group) among people who did not know the study.
- H3: speed, accuracy and L2 cost per round; mixed model of log RT on elapsed minutes x
  clue language; a piecewise model searches for the minute where slowing starts,
  with a log-time term so the early practice speed-up is not mistaken for a bend.
  Compare the start of slowing with the self-declared exhaustion time and the 0-100
  ratings; they need not coincide. Time to exhaustion by group and language profile is
  analysed with a survival model (people stopped by the 60-minute maximum are censored).

## Open questions for the lab
1. IRB: which protocol or pathway should this fall under?
2. Images: can the lab provide ~50 de-identified scans (rounds, practice and
   the surprise image)?
3. Recruitment of radiologists and physicians: appropriate channel and approvals.
4. Eye-tracking: would gaze data for the gorilla trial be useful and possible? (In the
   original study most radiologists who missed the gorilla looked right at it.)
5. Authorship and publication norms, if the work turns out well.
