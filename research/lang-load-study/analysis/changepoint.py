"""EXPLORATORY change-point ("bend") search on log response time (review finding F19).

Model (participant fixed effects, estimated by within-participant demeaning):
    log_rt = a_i + b1*t + b2*log(t) + b3*max(0, t - k) + L2 + task + error
t is minutes on task. log(t) absorbs the early practice speed-up. The bend k is
chosen by least squares over a fixed grid of candidate minutes.

Because k is chosen to fit best, ordinary standard errors and likelihood-ratio
tests are too optimistic. Uncertainty is therefore estimated with a participant
(cluster) bootstrap that re-runs the whole breakpoint search inside every
resample.

The quantity that says whether people get slower after the bend is the
post-break slope including ALL time terms, not the change b3 alone:
    slope(t) = b1 + b2 / t + b3     for t > k.
We report its average over [k, t_end]. A positive b3 with a negative post-break
slope means improvement slows down (a plateau), not that slowing begins.
Only when the bootstrap CI of the post-break slope lies above 0 is the result
described as post-break slowing, and even then it is exploratory.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BendResult:
    ok: bool
    reason: str = ""
    k: float = float("nan")
    pre_slope_at_k: float = float("nan")
    change: float = float("nan")
    post_slope_avg: float = float("nan")
    t_end: float = float("nan")
    ci: dict = field(default_factory=dict)  # name -> (lo, hi)
    n_boot: int = 0
    n_boot_failed: int = 0
    verdict: str = "failed"
    n_participants: int = 0
    n_trials: int = 0


def _design(rt):
    """Demeaned (within-participant) covariates other than the bend term."""
    t = rt.elapsed_min.to_numpy(float)
    cols = {"t": t, "log_t": np.log(t), "L2": (rt.condition.to_numpy() == "L2").astype(float)}
    for task in sorted(rt.task.unique())[1:]:
        cols[f"task_{task}"] = (rt.task.to_numpy() == task).astype(float)
    X = pd.DataFrame(cols, index=rt.index)
    return X


def _demean(M, codes, n_groups):
    M = np.atleast_2d(M.T).T if M.ndim == 1 else M
    sums = np.zeros((n_groups, M.shape[1]))
    np.add.at(sums, codes, M)
    counts = np.bincount(codes, minlength=n_groups)[:, None]
    return M - (sums / counts)[codes]


def _search(Z, A, y, w):
    """Weighted least squares for each candidate column of A. Returns (best index, beta) or None."""
    Zw = Z * w[:, None]
    G = Zw.T @ Z
    ZA = Zw.T @ A
    AA = (A * A * w[:, None]).sum(0)
    Zy = Zw.T @ y
    Ay = (A * (w * y)[:, None]).sum(0)
    yy = float((w * y * y).sum())
    p = Z.shape[1]
    best, best_rss, best_beta = None, np.inf, None
    XtX = np.empty((p + 1, p + 1))
    for j in range(A.shape[1]):
        XtX[:p, :p] = G
        XtX[:p, p] = XtX[p, :p] = ZA[:, j]
        XtX[p, p] = AA[j]
        Xty = np.append(Zy, Ay[j])
        if np.linalg.cond(XtX) > 1e12:
            continue
        beta = np.linalg.solve(XtX, Xty)
        rss = yy - beta @ Xty
        if rss < best_rss:
            best, best_rss, best_beta = j, rss, beta
    return None if best is None else (best, best_beta)


def _summaries(k, beta, t_end):
    b1, b2, b3 = beta[0], beta[1], beta[-1]
    pre = b1 + b2 / k
    span = max(t_end - k, 1e-9)
    post_avg = b1 + b3 + b2 * (np.log(t_end) - np.log(k)) / span
    return pre, b3, post_avg


def bend_search(rt, n_boot=200, step=0.5, seed=0, alpha=0.05, max_fail_share=0.1, min_participants=5):
    """rt: correct trials with participant_id, log_rt, elapsed_min (> 0), condition, task."""
    rt = rt[np.isfinite(rt.log_rt) & (rt.elapsed_min > 0)].reset_index(drop=True)
    res = BendResult(ok=False, n_participants=rt.participant_id.nunique(), n_trials=len(rt))
    if res.n_participants < min_participants:
        res.reason = f"too few participants ({res.n_participants} < {min_participants})"
        return res
    lo, hi = rt.elapsed_min.quantile([.1, .9])
    grid = np.arange(np.ceil(lo), np.floor(hi) + 1e-9, step)
    grid = grid[grid > 0]
    if grid.size < 2:
        res.reason = "observed time range too short for a bend search"
        return res
    t_end = float(rt.elapsed_min.quantile(.95))
    codes, uniq = pd.factorize(rt.participant_id)
    G = len(uniq)
    X = _design(rt)
    Z = _demean(X.to_numpy(float), codes, G)
    keep = Z.std(0) > 1e-12  # drop covariates with no within-person variation
    if not keep[:2].all():
        res.reason = "no within-participant variation in time on task"
        return res
    Z = Z[:, keep]
    y = _demean(rt.log_rt.to_numpy(float)[:, None], codes, G)[:, 0]
    t = rt.elapsed_min.to_numpy(float)
    A = _demean(np.clip(t[:, None] - grid[None, :], 0, None), codes, G)

    full = _search(Z, A, y, np.ones(len(y)))
    if full is None:
        res.reason = "model matrix singular at every candidate bend"
        return res
    j, beta = full
    res.k = float(grid[j])
    res.pre_slope_at_k, res.change, res.post_slope_avg = _summaries(res.k, beta, t_end)
    res.t_end = t_end

    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        mult = rng.multinomial(G, np.full(G, 1.0 / G)).astype(float)
        w = mult[codes]
        out = _search(Z, A, y, w)
        if out is None:
            res.n_boot_failed += 1
            continue
        jb, bb = out
        kb = float(grid[jb])
        draws.append((kb, *_summaries(kb, bb, t_end)))
    res.n_boot = n_boot
    if n_boot <= 0:
        res.reason = "bootstrap disabled (n_boot = 0), so no uncertainty estimate"
        return res
    if res.n_boot_failed > max_fail_share * n_boot:
        res.reason = f"bootstrap failed in {res.n_boot_failed}/{n_boot} resamples"
        return res
    d = np.array(draws)
    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    for name, col in (("k", 0), ("pre_slope_at_k", 1), ("change", 2), ("post_slope_avg", 3)):
        res.ci[name] = tuple(np.percentile(d[:, col], q))
    res.ok = True
    lo_post, hi_post = res.ci["post_slope_avg"]
    if lo_post > 0:
        res.verdict = "post_break_slowing"
    elif hi_post < 0:
        res.verdict = "post_break_speedup"
    else:
        res.verdict = "no_demonstrated_slowing"
    return res


def describe(res, session_limit_min=60.0):
    """Human-readable lines. Never claims fatigue onset unless the post-break slope CI is above 0."""
    lines = ["EXPLORATORY change-point search (the bend minute was chosen to fit best; "
             "CIs come from a participant bootstrap that re-selects the bend in every resample)."]
    if not res.ok:
        lines.append(f"Change-point search FAILED: {res.reason}. No inferential results reported.")
        return lines
    ci = res.ci
    lines.append(f"Best bend: {res.k:.1f} min (95% CI {ci['k'][0]:.1f} to {ci['k'][1]:.1f}); "
                 f"{res.n_participants} people, {res.n_trials} trials, "
                 f"{res.n_boot - res.n_boot_failed}/{res.n_boot} usable resamples.")
    lines.append(f"Slope just before the bend: {res.pre_slope_at_k:+.4f} log-ms/min "
                 f"[{ci['pre_slope_at_k'][0]:+.4f}, {ci['pre_slope_at_k'][1]:+.4f}]")
    lines.append(f"Change in slope at the bend: {res.change:+.4f} "
                 f"[{ci['change'][0]:+.4f}, {ci['change'][1]:+.4f}]")
    lines.append(f"Average post-break slope ({res.k:.1f} to {res.t_end:.1f} min, all time terms): "
                 f"{res.post_slope_avg:+.4f} [{ci['post_slope_avg'][0]:+.4f}, {ci['post_slope_avg'][1]:+.4f}]")
    if res.verdict == "post_break_slowing":
        lines.append(f"Exploratory finding: response times rise after about {res.k:.1f} min "
                     "(post-break slope CI above 0). Needs confirmation in a preregistered analysis "
                     "before it is called fatigue onset.")
    elif res.verdict == "post_break_speedup":
        lines.append("Post-break slope is negative: people are still getting faster after the bend. "
                     "This is not evidence of fatigue.")
    else:
        extra = (" A positive change with a post-break slope that is not above 0 means improvement "
                 "slows down (a plateau), not that slowing begins." if res.change > 0 else "")
        lines.append(f"No demonstrated slowing within the {session_limit_min:g}-minute session: "
                     f"the post-break slope CI includes 0.{extra}")
    return lines
