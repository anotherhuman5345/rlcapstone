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

For the Language of the Clue study, the repository owner has confirmed that an external tool helped merge changes but did not author the study code. A historical commit incorrectly recorded that tool as a code coauthor. This clarification corrects the claim in current documentation without rewriting Git history. Required academic, institutional, and licensing disclosures still apply.

## Verification and contact

To assess an experiment, inspect its training scripts, split methodology, checkpoints, and evaluation reports. Reproduction may require the original datasets and dependencies. Open a GitHub issue with questions about a specific implementation or result.
