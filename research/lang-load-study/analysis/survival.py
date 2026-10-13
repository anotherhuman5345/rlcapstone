"""Kaplan-Meier product-limit estimator with correct handling of ties.

All observations sharing a time are processed together: at each unique time t,
n(t) = number still at risk just before t (time >= t), d(t) = events at t, and
S(t) = S(t-) * (1 - d(t) / n(t)). Observations censored at t are still counted
in the risk set at t (the standard convention: events happen before censoring
at the same time). The result therefore does not depend on row order.

Median survival = the smallest time t with S(t) <= 0.5 (the usual definition);
None ("not reached") if the curve never drops to 0.5.
"""
import numpy as np
import pandas as pd


def _clean(times, events):
    t = np.asarray(times, dtype=float)
    e = np.asarray(events, dtype=float)
    if t.shape != e.shape:
        raise ValueError("times and events must have the same length")
    keep = np.isfinite(t) & np.isfinite(e)
    return t[keep], e[keep].astype(bool)


def km_curve(times, events):
    """Return one row per unique observed time: time, n_risk, n_events, n_censored, survival."""
    t, e = _clean(times, events)
    if t.size == 0:
        return pd.DataFrame(columns=["time", "n_risk", "n_events", "n_censored", "survival"])
    uniq, inverse = np.unique(t, return_inverse=True)
    n_events = np.bincount(inverse, weights=e.astype(float), minlength=uniq.size)
    n_total = np.bincount(inverse, minlength=uniq.size).astype(float)
    # at risk at uniq[i] = everyone whose time is >= uniq[i]
    n_risk = n_total[::-1].cumsum()[::-1]
    surv = np.cumprod(1.0 - n_events / n_risk)
    return pd.DataFrame({"time": uniq, "n_risk": n_risk.astype(int), "n_events": n_events.astype(int),
                         "n_censored": (n_total - n_events).astype(int), "survival": surv})


def km_median(times, events):
    """Median survival time (float) or None when not reached."""
    curve = km_curve(times, events)
    # Tolerance so that e.g. 1 - 1/2 is treated as exactly 0.5.
    below = curve[curve.survival <= 0.5 + 1e-12]
    return float(below.time.iloc[0]) if len(below) else None


def format_median(value, unit="min"):
    return "not reached" if value is None else f"{value:.1f} {unit}"
