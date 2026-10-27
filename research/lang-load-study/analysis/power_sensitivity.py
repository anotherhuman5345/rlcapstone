"""SIMULATION ONLY: exploratory sample-size sensitivity for the bilingual study.

Not a preregistered power calculation. Assumptions are hypothetical until approved
by the investigator using pilot data and the final mixed-effects analysis plan.

Primary approximation: a paired L2-L1 log-response-time contrast, matched within
participant, round and core task, tested across participants with a two-sided t-test.
This is NOT the full planned mixed-effects regression. Item effects are shared
across participants and counterbalanced; participant-specific language slopes,
trial noise and variable stopping times are simulated.
"""
import argparse
import json
import math

import numpy as np
from scipy import stats


TASKS = 7


def simulate_power(n, repetitions, *, l2_percent=5.0, slope_sd=0.08,
                   item_sd=0.15, trial_sd=0.30, stop_probability=0.85,
                   stop_low=12.0, stop_high=55.0, session_limit=60.0,
                   minutes_per_round=2.5, max_rounds=24, alpha=0.05, seed=1):
    """Monte Carlo detection rate under explicit assumed parameters (not real data)."""
    if n < 4 or repetitions < 1 or max_rounds < 1:
        raise ValueError("n >= 4, repetitions >= 1, and max_rounds >= 1 required")
    if not (0 < alpha < 1 and 0 <= stop_probability <= 1):
        raise ValueError("alpha and stopping probability outside valid range")
    if not (0 < stop_low <= stop_high <= session_limit and minutes_per_round > 0):
        raise ValueError("invalid stopping window or round duration")
    if min(slope_sd, item_sd, trial_sd) < 0 or l2_percent <= -100:
        raise ValueError("standard deviations must be nonnegative and L2 percent > -100")
    rng = np.random.default_rng(seed)
    effect = math.log1p(l2_percent / 100.0)
    detected = 0
    for _ in range(repetitions):
        stop_at = np.where(rng.random(n) < stop_probability,
                           rng.uniform(stop_low, stop_high, n), session_limit)
        rounds = np.clip(np.floor(stop_at / minutes_per_round).astype(int), 1, max_rounds)
        # Each task-round has two items. Counterbalance reverses the item-language
        # assignment across participants so item difficulty is not conflated with L2.
        item = rng.normal(0, item_sd, size=(max_rounds, TASKS, 2))
        item_delta = item[:, :, 1] - item[:, :, 0]
        direction = rng.choice([-1, 1], size=(n, 1, 1))
        participant_l2_slope = rng.normal(0, slope_sd, size=(n, 1, 1))
        noise = rng.normal(0, trial_sd, size=(n, max_rounds, TASKS, 2))
        pair_diff = (effect + participant_l2_slope + direction * item_delta
                     + noise[:, :, :, 1] - noise[:, :, :, 0])
        mask = np.arange(max_rounds)[None, :] < rounds[:, None]
        mean_by_person = (pair_diff * mask[:, :, None]).sum(axis=(1, 2)) / (rounds * TASKS)
        p = stats.ttest_1samp(mean_by_person, 0.0).pvalue
        detected += bool(np.isfinite(p) and p < alpha)
    power = detected / repetitions
    mc_se = math.sqrt(power * (1 - power) / repetitions)
    return {"n": n, "repetitions": repetitions, "detection_rate": round(power, 4),
            "monte_carlo_se": round(mc_se, 4), "simulation_only": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-sizes", default="20,40,60,80,120")
    ap.add_argument("--repetitions", type=int, default=500)
    ap.add_argument("--l2-percent", type=float, default=5.0)
    ap.add_argument("--slope-sd", type=float, default=0.08)
    ap.add_argument("--item-sd", type=float, default=0.15)
    ap.add_argument("--trial-sd", type=float, default=0.30)
    ap.add_argument("--stop-probability", type=float, default=0.85)
    ap.add_argument("--stop-low", type=float, default=12.0)
    ap.add_argument("--stop-high", type=float, default=55.0)
    ap.add_argument("--seed", type=int, default=20261027)
    args = ap.parse_args()
    sizes = [int(s.strip()) for s in args.sample_sizes.split(",")]
    results = [simulate_power(n, args.repetitions, l2_percent=args.l2_percent,
                              slope_sd=args.slope_sd, item_sd=args.item_sd,
                              trial_sd=args.trial_sd, stop_probability=args.stop_probability,
                              stop_low=args.stop_low, stop_high=args.stop_high,
                              seed=args.seed + i) for i, n in enumerate(sizes)]
    print(json.dumps({"label": "HYPOTHETICAL SENSITIVITY ONLY; NOT RESEARCH FINDINGS",
                      "method": "within-participant task/round paired contrast; not final mixed model",
                      "assumptions": vars(args), "results": results}, indent=2))


if __name__ == "__main__":
    main()
