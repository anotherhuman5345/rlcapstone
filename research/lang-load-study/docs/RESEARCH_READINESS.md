# Research readiness and sign-off checklist

**Status: DEMO / NOT APPROVED FOR CONFIRMATORY DATA COLLECTION.**

This is a working checklist, **not** an IRB determination, ethics approval,
translation certificate, completed power analysis, or statement of research
findings. No participant research data is claimed. Keep `IRB_APPROVED=0`
until the responsible investigator has documented approval in writing.

## Software verification

- [ ] Run the complete test suite (`pytest -q`), including F06 retention
  overlap/reload regression tests and approved-language gate tests.
- [ ] Review the F06 fix against the intended retention estimand. Word indices
  are reusable across languages; an exposure is tracked by **language,
  condition, and word index**. Historic demo exports are not retroactively fixed.
- [ ] Run an end-to-end staging session in English and in each *approved*
  language pair. Inspect exported L1/L2 retention hit/false-alarm columns,
  reload behavior, time-cap behavior and stop reasons.
- [ ] Confirm that the deployed version and recorded `STUDY_VERSION` match the
  reviewed release and that no production deployment occurs from an unreviewed
  branch.

## Translation / participant materials

Every language beyond English is currently listed as unverified. Do **not** flip
`verified` to `true` merely because automatic checks pass. For every
language used in live recruitment or consent:

- [ ] Obtain an identified qualified native-language reviewer approved by the
  study investigator; record review date, locale revision/hash and corrections
  in the private study review log.
- [ ] Review **consent**, privacy/withdrawal language, 60-minute clock origin,
  minors' guardian language, exhaustion and withdrawal controls.
- [ ] Review interface labels, all clue patterns, inflections, colors, regions,
  reading passages, operation-span words and any task-library text selected
  for the approved protocol; examine right-to-left rendering where relevant.
- [ ] Run `python tools/check_locale.py <code> --all` and
  `python tools/check_reading.py <code>` plus participant-flow tests.
- [ ] Only after **human** content review and investigator sign-off, set
  `app/locales/<code>.json` `verified=true` and retain review evidence.
  Run all tests again. English consent was clarified in this change; translated
  consent text must be independently updated and reviewed.

The application restricts approved-session **interface and clue** languages
to reviewed files; language choices describing participants' native language
remain available for demographic reporting. A `verified` flag is a local
attestation of review, **not** independent evidence that review occurred.

## Study design, images and sample size

- [ ] Replace placeholder medical-style scans with suitably licensed,
  de-identified images and obtain lab/ethics permission for the use case.
- [ ] Investigator approves the current clock rule: first *scored* stimulus
  starts a 60-minute maximum; consent/background/instructions/practice excluded.
- [ ] Finalize the primary mixed-effects estimand, items/random-effects
  structure, exclusions, stopping assumptions and smallest effect of interest.
- [ ] Obtain plausible variances and dropout/stopping distributions from
  appropriate published evidence or an approved pilot.
- [ ] Run `python analysis/power_sensitivity.py --help` and compare plausible
  **hypothetical** scenarios. It uses paired contrasts as a screening
  approximation, **not the planned confirmatory mixed model**.
- [ ] Fit the final approved model in simulation under agreed assumptions;
  consider the surprise gorilla binary-outcome endpoint separately.
  Document uncertainty and obtain investigator approval for recruitment
  targets. **No definitive sample size is established by this branch.**

## Ethics, recruitment, and operations

- [ ] Obtain written IRB/ethics approval or an authorized determination,
  with approved protocol, consent language, recruitment plan, protections for
  minors, data retention/security and study-site requirements.
- [ ] Review participant-facing withdrawal instructions with the investigator
  and ethics board. The English consent has been clarified but **not approved**.
- [ ] Verify server security, test/real data isolation, retention period, backups,
  and data export access before recruitment.
- [ ] Only after written clearance and above checks, configure secure
  `ADMIN_KEY`, production database, `IRB_APPROVED=1`, and the real
  `IRB_NUMBER`. The app rejects placeholder approval identifiers; this
  technical gate cannot validate the underlying approval document.

## Release decision

**No-go until every mandatory item is evidenced and the responsible
investigator signs off.** The present work resolves implementable software and
documentation issues on a review branch; it does not complete independent
language reviews or institutional research approval.
