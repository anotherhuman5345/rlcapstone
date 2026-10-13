"""Shared response validation for the task scorers (app/tasks/*/logic.py).

This module is not a task (it has no folder or task.json), so the plugin loader skips it.
It gives every scorer the same event-level vocabulary and the same way of reporting
malformed data, so that a response the browser could never have sent is never scored as
a clean, timely, correct answer.

Event status (each scored event gets exactly one, counted in metrics["event_status"]):
  absent        no response at all: an omission, or a correct withhold (no-go, stop)
  invalid       malformed: wrong type, non-finite / negative / impossible time, a value
                outside the allowed set, a key without a time or a time without a key,
                or an entry missing from the list
  anticipatory  a time below the task's anticipation floor (default 100 ms)
  late          a time beyond the task's documented response window / time limit
  timely        a well-formed response inside the window. In a task with a response
                window only a timely response counts as a response that was made.
A withhold (no-go, stop signal, a standard in an oddball stream) is successful only when
the event is absent: an invalid, anticipatory or late entry is never turned into a
successful inhibition.

Every result carries metrics["flags"] (sorted names of everything abnormal that was seen,
e.g. "invalid_rt", "late_rt", "extra_events", "missing_audio") and
metrics["invalid_events"] (how many events / fields were malformed). A clean, well-formed
response has flags == [] and invalid_events == 0.

Times: every time is in ms. Besides the task's own window, any time above the trial's
hard timeout (task.json "timeout_ms") is impossible and therefore invalid.
"""
import functools
import json
import math
from pathlib import Path

ANTICIPATION_MS = 100
ABSENT, INVALID, ANTICIPATORY, LATE, TIMELY = "absent", "invalid", "anticipatory", "late", "timely"
STATUSES = (ABSENT, INVALID, ANTICIPATORY, LATE, TIMELY)
MAX_ENTRIES = 5000      # no list in a response is read beyond this many entries
DEFAULT_CEILING_MS = 600000


class _Missing:
    """Placeholder for an entry the response list should have had but did not."""

    def __repr__(self):
        return "MISSING"


MISSING = _Missing()
BAD = object()          # returned by Audit.choice for a present but not allowed value


def is_num(v):
    """A finite real number (bool is not a number here)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def member(v, allowed):
    """v is one of `allowed`, with strict types (True is not 1, 1.0 is not 1)."""
    if isinstance(v, bool) or not isinstance(v, (str, int)):
        return False
    try:
        return v in allowed
    except TypeError:
        return False


def trial_ceiling(module_file):
    """The trial's hard timeout (ms) from the task.json next to a logic.py."""
    try:
        meta = json.loads((Path(module_file).parent / "task.json").read_text(encoding="utf-8"))
        return int(meta.get("timeout_ms", DEFAULT_CEILING_MS))
    except (OSError, ValueError, TypeError):
        return DEFAULT_CEILING_MS


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(float(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2), 1)


def mean(xs, nd=1):
    return round(sum(xs) / len(xs), nd) if xs else None


def rate(k, n, nd=3):
    return round(k / n, nd) if n else None


class Audit:
    """Collects flags and event statuses while one response is scored."""

    def __init__(self, ceiling_ms=DEFAULT_CEILING_MS):
        self.ceiling = ceiling_ms
        self.flags = {}
        self.invalid_events = 0
        self.counts = {s: 0 for s in STATUSES}
        self.counted = False

    # -- bookkeeping -----------------------------------------------------------------
    def flag(self, name, n=1):
        self.flags[name] = self.flags.get(name, 0) + n

    def malformed(self, name):
        """One malformed event or field."""
        self.invalid_events += 1
        self.flag(name)

    def record(self, status):
        self.counted = True
        self.counts[status] += 1
        return status

    # -- scalar fields -----------------------------------------------------------------
    def time(self, v, *, field="rt", window=None, floor=ANTICIPATION_MS, slack=0, required=False):
        """Classify one time in ms. Returns (status, float or None); the value is kept for
        anticipatory and late times (they are real, just not timely) and None otherwise.
        None/absent -> ABSENT (flagged missing_<field> when required)."""
        if v is None or v is MISSING:
            if required:
                self.malformed(f"missing_{field}")
                return INVALID, None
            return ABSENT, None
        if not is_num(v) or v < 0:
            self.malformed(f"invalid_{field}")
            return INVALID, None
        if self.ceiling is not None and v > self.ceiling:
            self.malformed(f"impossible_{field}")
            return INVALID, None
        if window is not None and v > window + slack:
            self.flag(f"late_{field}")
            return LATE, float(v)
        if floor and v < floor:
            self.flag(f"anticipatory_{field}")
            return ANTICIPATORY, float(v)
        return TIMELY, float(v)

    def duration(self, d, field, *, floor=ANTICIPATION_MS, required=True, window=None):
        """A descriptive time field of the response (dict d): the value when valid and in
        range, else None (flagged). Missing -> flagged when required."""
        v = d.get(field, MISSING) if isinstance(d, dict) else MISSING
        if v is MISSING:
            if required:
                self.malformed(f"missing_{field}")
            return None
        st, t = self.time(v, field=field, window=window, floor=floor)
        return t if st == TIMELY else None

    def choice(self, v, allowed, field="key"):
        """None -> None; an allowed value -> the value; anything else -> BAD (flagged)."""
        if v is None or v is MISSING:
            return None
        if member(v, allowed):
            return v
        self.malformed(f"invalid_{field}")
        return BAD

    def opt_int(self, d, field, lo=0, hi=None, required=True):
        v = d.get(field, MISSING) if isinstance(d, dict) else MISSING
        if v is MISSING:
            if required:
                self.malformed(f"missing_{field}")
            return None
        if v is None:
            return None
        if not is_int(v) or v < lo or (hi is not None and v > hi):
            self.malformed(f"invalid_{field}")
            return None
        return v

    def opt_bool(self, d, field, required=True):
        v = d.get(field, MISSING) if isinstance(d, dict) else MISSING
        if v is MISSING:
            if required:
                self.malformed(f"missing_{field}")
            return None
        if v is None:
            return None
        if not isinstance(v, bool):
            self.malformed(f"invalid_{field}")
            return None
        return v

    def opt_str(self, d, field, maxlen=200, allowed=None, required=True):
        v = d.get(field, MISSING) if isinstance(d, dict) else MISSING
        if v is MISSING:
            if required:
                self.malformed(f"missing_{field}")
            return None
        if v is None:
            return None
        if not isinstance(v, str) or len(v) > maxlen or (allowed is not None and v not in allowed):
            self.malformed(f"invalid_{field}")
            return None
        return v

    # -- lists -------------------------------------------------------------------------
    def entries(self, seq, n, field="events"):
        """A list that must hold exactly one entry per stimulus: returns exactly n entries,
        padding with MISSING (flag missing_<field>) and dropping extras (flag extra_<field>)."""
        if not isinstance(seq, list):
            self.malformed(f"no_{field}")
            return [MISSING] * n
        if len(seq) < n:
            self.flag(f"missing_{field}", n - len(seq))
        elif len(seq) > n:
            self.flag(f"extra_{field}", min(len(seq), MAX_ENTRIES) - n)
        return list(seq[:n]) + [MISSING] * (n - len(seq))

    def stream(self, seq, field, cap=MAX_ENTRIES, required=True):
        """A variable-length list (moves, clicks, presses): the list, cut at `cap` entries
        (flag too_many_<field>). Not a list -> [] (flagged)."""
        if seq is MISSING or seq is None:
            if required:
                self.malformed(f"no_{field}")
            return []
        if not isinstance(seq, list):
            self.malformed(f"no_{field}")
            return []
        if len(seq) > cap:
            self.flag(f"too_many_{field}", len(seq) - cap)
            return seq[:cap]
        return seq

    def obj(self, r, field="event"):
        """An entry that must be a dict: the dict, {} for MISSING, or None when malformed
        (flagged; the caller treats it as an invalid event)."""
        if r is MISSING:
            self.invalid_events += 1
            return None
        if not isinstance(r, dict):
            self.malformed(f"{field}_not_object")
            return None
        return r

    def monotonic(self, times, field="t"):
        """Flag times (None skipped) that go backwards (equal times are allowed); returns True when
        they never decrease."""
        prev, ok = None, True
        for t in times:
            if t is None:
                continue
            if prev is not None and t < prev:
                ok = False
            prev = t if prev is None else max(prev, t)
        if not ok:
            self.malformed(f"non_monotonic_{field}")
        return ok

    # -- events --------------------------------------------------------------------------
    def keyed(self, r, allowed, *, key="key", rt="rt", window=None, floor=ANTICIPATION_MS, slack=0):
        """One {key, rt} event -> (status, key or None, rt or None); the status is recorded.
        Only a TIMELY status carries an answer that may be scored as made in the window."""
        d = self.obj(r)
        if d is None:
            return self.record(INVALID), None, None
        if key not in d or rt not in d:
            self.malformed(f"missing_{key if key not in d else rt}")
            return self.record(INVALID), None, None
        k = self.choice(d.get(key), allowed, key)
        st, t = self.time(d.get(rt), field=rt, window=window, floor=floor, slack=slack)
        if k is BAD or st == INVALID:
            return self.record(INVALID), None, None
        if k is None and st == ABSENT:
            return self.record(ABSENT), None, None
        if k is None:
            self.malformed(f"{rt}_without_{key}")
            return self.record(INVALID), None, None
        if st == ABSENT:
            self.malformed(f"{key}_without_{rt}")
            return self.record(INVALID), None, None
        return self.record(st), k, t

    def press(self, r, *, rt="rt", window=None, floor=ANTICIPATION_MS, slack=0):
        """One press-or-not event {rt} -> (status, rt or None); the status is recorded."""
        d = self.obj(r)
        if d is None:
            return self.record(INVALID), None
        if rt not in d:
            self.malformed(f"missing_{rt}")
            return self.record(INVALID), None
        st, t = self.time(d.get(rt), field=rt, window=window, floor=floor, slack=slack)
        return self.record(st), t

    # -- results -------------------------------------------------------------------------
    def finish(self, hit, errors, metrics):
        m = dict(metrics)
        m["flags"] = sorted(self.flags)
        m["flag_counts"] = dict(sorted(self.flags.items()))
        m["invalid_events"] = self.invalid_events
        if self.counted:
            m["event_status"] = dict(self.counts)
        return {"hit": bool(hit), "errors": int(errors), "metrics": m}

    def junk(self, errors=0, why="malformed_response"):
        self.malformed(why)
        return self.finish(False, errors, {})


def junk(errors=0, why="malformed_response"):
    return Audit().junk(errors, why)


def safe(fn):
    """Last-resort wrapper for score(): a scorer must never crash on any response. An
    unexpected exception is reported as a flagged miss (the adversarial check treats the
    "scorer_exception" flag as a bug to fix, so this only protects live data collection)."""
    @functools.wraps(fn)
    def wrapper(item, response):
        try:
            return fn(item, response)
        except Exception as exc:  # noqa: BLE001 - scoring must not take a session down
            a = Audit()
            a.flag("scorer_exception")
            a.flag(f"scorer_exception:{type(exc).__name__}")
            return a.finish(False, 0, {})
    return wrapper
