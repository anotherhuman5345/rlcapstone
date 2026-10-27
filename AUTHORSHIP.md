# Authorship, Development Process, and Project Provenance

RLcapstone is a machine-learning and software-development portfolio owned and maintained by [anotherhuman5345](https://github.com/anotherhuman5345).

## Ownership and scope

I am the owner and maintainer of this repository. It brings together six machine-learning projects, five Flutter applications, research documentation, training and evaluation scripts, and interactive demonstrations.

I designed and wrote the training and evaluation code for the reported experiments, selected and implemented the patient-level evaluation split, and ran the evaluations myself. I take responsibility for the technical claims, limitations, and reported results. No coauthor is claimed for those evaluation results.

## How to evaluate the work

- **MoleCheck:** dermoscopy and smartphone-photo evaluation, including skin-type fairness analysis.
- **ECG:** explicit reporting of the gap between validation and unseen-patient macro-recall.
- **ADHD EEG:** subject-level evaluation on a small held-out sample of 24 children.
- **Leukemia:** identification of patient leakage, rebuilding the patient-level split, and subsequent cross-laboratory experiments.
- **Stock risk:** temporal evaluation and an ablation in which sentiment did not improve the model.
- **Security sandbox:** constrained Q-learning against an intentionally vulnerable local teaching application.

Inspect [`src/`](src), [`trained_models/`](trained_models), [`notebooks/`](notebooks), [`docs/`](docs), and [`PLAN.md`](PLAN.md), alongside project write-ups at https://rlcapstone.ai. Some experiments require separately licensed datasets or dependencies.

## Research study

The [Language of the Clue study](research/lang-load-study) is ongoing. Its documentation describes the study design and review requirements. No approved participant data collection or study findings are claimed.

## Tools, collaboration, and attribution

Development tools or administrative merging assistance do not automatically establish authorship of underlying research or code. Historical credits should accurately describe actual contributions. An earlier co-author credit was identified as inaccurate; the study documentation clarifies the attribution without rewriting Git history. Any material contributions or required disclosures remain subject to applicable academic, institutional, and licensing policies.

## Verification and contact

To assess an experiment, inspect its training scripts, split methodology, checkpoints, and evaluation reports. Reproduction may require the original datasets and dependencies. Open a GitHub issue with questions about a specific implementation or result.
