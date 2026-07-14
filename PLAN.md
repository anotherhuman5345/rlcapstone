# RLcapstone — Portfolio Roadmap & Status

Six end-to-end applied-AI projects, each taken from a public dataset through training, honest
evaluation, and deployment to a live demo and (mostly) an on-device Flutter app.
Live site: **https://rlcapstone.ai**

> This file tracks the portfolio as it stands today. The original single-project MoleCheck build
> plan (phases 0–4) lives in the git history.

## Status by project

| # | Project | Status | Key iterations / notes |
|---|---|---|---|
| 1 | **MoleCheck** — skin lesion | Live (web + Android) | v1 ISIC dermoscopy → **v2** PAD-UFES phone-photo domain-gap fix (0.914 → 0.743 → 0.920); Fitzpatrick fairness audit |
| 2 | **ECG arrhythmia** | Live (web + Android) | inter-patient DS1/DS2; the 96% → 44% macro-recall generalization lesson |
| 3 | **ADHD from EEG** | Live (web + Android) | strict subject-level split; 91.7% on 24 unseen children |
| 4 | **Leukemia cell subtyping** | Live (web + Android) | v1 leakage 99.8% → **v2** patient-split 81% → **v3** multi-source, cross-lab generalization (unseen-lab specificity 20% → 67%) |
| 5 | **Stock volatility & sentiment** | Live (web + Android) | temporal split; sentiment ablation = honest negative result (~57%, 3-class) |
| 6 | **Autonomous pentest agent** | Live (web) | tabular Q-learning on a sandbox MDP; JADEPUFFER defensive detector |

## The method every project follows

Public dataset → leakage-aware prep/split → train on local GPU → honest evaluation
(sensitivity/specificity, ROC-AUC, macro-recall over raw accuracy) → export to ONNX/TFLite →
ship a browser demo + Flutter app. See the live ["how it's built" pipeline](https://rlcapstone.ai/pipeline).

## The through-line

Rigorous, honest evaluation: no data leakage, task-appropriate metrics, and negative results
reported rather than hidden. A lower honest number beats an inflated one — that principle runs
through every project and every iteration above.

## Possible next steps

- **MoleCheck** — image + clinical-metadata fusion; darker-skin data to close the fairness gap.
- **Leukemia** — a held-out external *blast* source (e.g. ALL-IDB2) to extend the v3 cross-lab test.
- **ADHD** — subject-level cross-validation and bootstrap confidence intervals.
- **Engineering** — optional CI and a shared Flutter UI package (deferred; low ROI for a solo portfolio).
