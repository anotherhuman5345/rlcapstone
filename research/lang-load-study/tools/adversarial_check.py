"""Adversarial fixture check for every library task's server-side scorer.

Usage:  python tools/adversarial_check.py                 (all tasks)
        python tools/adversarial_check.py stop_signal sart  (some tasks)
        options: --items N (items per task, default 2), --verbose

Why: tools/check_task.py only scores each task's own example responses, so a scorer that
trusts malformed or impossible data passes it (review F12/F14/F24: replacing every RT of a
stop-signal response with 999999 still scored as a hit). This harness generates items,
takes the task's correct example response and mutates it in ways a real browser cannot
produce, and checks the scorer's behaviour against fixed rules.

Each logic.py declares TIMING:
  "window"   events have a documented response window (WINDOW_MS); only a valid, timely
             RT counts as a response that was made
  "limit"    the trial has a documented time limit (LIMIT_MS) for the decisive action
  "untimed"  times are descriptive only (checked for validity and flagged)

Rules (a violation is reported as FAIL):
  R0 shape      score() never raises; returns {"hit": bool, "errors": int >= 0,
                "metrics": dict} with metrics["flags"] (list) and metrics["invalid_events"]
                (int); the result is strict JSON (no NaN/Infinity); the scorer did not
                fall back to its exception guard (flag "scorer_exception").
  R1 examples   example_response(correct=True) is a hit with no flags; correct=False is
                a miss.
  R2 not clean  a malformed payload is never a clean hit: the result is a miss, or carries
                at least one flag, or is identical to the unmutated result (the mutated
                field is simply not used). Applied to: every timing field set to 999999,
                -5, 0, NaN, +-Infinity, 1e308, "450", true or null (drift fields such as
                "late" skip -5/0, which are legal there); one timing field at a time; the
                wrong JSON type at every node (sampled); every key deleted (sampled); the
                top-level event lists duplicated, blown up to 10 000 entries, or with every
                entry replaced by null.
  R3 timing     for TIMING "window": with every timing field set to any of the values above
                (or to just beyond the window) the result is a miss; for "limit" the same
                except 0. An impossible, non-finite, negative or late time never yields a
                timely correct response.
  R4 event      where the result reports metrics["event_status"], making one event's time
                impossible lowers the count of timely events (event-level handling).
  R5 benign     adding an unknown field to every object changes nothing; reversing the
                top-level lists and truncating them must not crash.
  R6 junk       None, {}, [], "x", 3, NaN, true and nested junk are misses.
  R7 speed      a 10 000-entry payload is scored in under 2 s.
"""
import copy
import json
import math
import random
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NAN, INF = float("nan"), float("inf")
TIMING_KEY = re.compile(r"^(rt|rts|t|ts|time|times|onsets|presses|late|resume_at|first_rt|test_rts|"
                        r"click_rts|[a-z_]*_ms|[a-z_]*_rt)$")
DRIFT_KEYS = {"late"}
# Timing leaves that are not reachable by key name: (task id, path pattern), "*" = any index.
EXTRA_TIMING = {
    "tracking_arithmetic": [("samples", "*", 0)],
    "interruption_recovery": [("cases", "*", "clicks", "*", 1)],
}
BAD_TIMES = [999999, -5, 0, NAN, INF, -INF, 1e308, "450", True, None]
DRIFT_BAD = [999999, NAN, INF, -INF, 1e308, "450", True, None]
JUNK = [None, {}, [], "x", 3, NAN, True, {"events": None}, [None, 3, "x"], {"events": [[], {}, "x"]}]
WRONG = {
    str: [12345, -1.5, [], {}, True, NAN],
    int: ["~bogus~", [], {}, True, NAN, INF],
    float: ["~bogus~", [], {}, True, NAN, INF],
    bool: ["~bogus~", 7, [], {}],
    list: ["~bogus~", 7, {}, None, True],
    dict: ["~bogus~", 7, [], None, True],
    type(None): ["~bogus~", [], {}, True, NAN],
}
OVERSIZE = 10000


def _paths(obj, prefix=()):
    """Every (path, value) below obj, depth first; containers included."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append((prefix + (k,), v))
            out += _paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.append((prefix + (i,), v))
            out += _paths(v, prefix + (i,))
    return out


def _get(obj, path):
    for p in path:
        obj = obj[p]
    return obj


def _set(obj, path, value):
    if not path:
        return value
    _get(obj, path[:-1])[path[-1]] = value
    return obj


def _nearest_key(path):
    for p in reversed(path):
        if isinstance(p, str):
            return p
    return None


def _matches(path, pattern):
    return len(path) == len(pattern) and all(q == "*" or q == p for p, q in zip(path, pattern))


def timing_paths(task_id, resp):
    """Leaves (non-container values) that hold times, with whether they are drift fields."""
    out = []
    for path, v in _paths(resp):
        if isinstance(v, (dict, list)):
            continue
        key = _nearest_key(path)
        extra = any(_matches(path, pat) for pat in EXTRA_TIMING.get(task_id, []))
        if extra or (key is not None and TIMING_KEY.match(key)):
            # a list of plain values under a timing key (presses, onsets, times) counts too
            out.append((path, key in DRIFT_KEYS))
    return out


def _top_lists(resp):
    if isinstance(resp, list):
        return [()]
    if isinstance(resp, dict):
        return [(k,) for k, v in resp.items() if isinstance(v, list)]
    return []


def _strict_json(x):
    json.dumps(x, allow_nan=False)


class Checker:
    def __init__(self, task_id, plugin, verbose=False):
        self.id = task_id
        self.logic = plugin.logic
        self.verbose = verbose
        self.fails = []
        self.seen = {}
        self.n_fail = 0
        self.calls = 0
        self.timing = getattr(self.logic, "TIMING", None)
        self.window = getattr(self.logic, "WINDOW_MS", None) if self.timing == "window" else \
            getattr(self.logic, "LIMIT_MS", None) if self.timing == "limit" else None
        self.ceiling = plugin.timeout_ms

    def fail(self, rule, msg):
        """Record a failure; similar messages (same text up to numbers) are shown 2 times."""
        sig = rule + re.sub(r"[0-9.]+", "#", msg.split(":")[0])
        self.seen[sig] = self.seen.get(sig, 0) + 1
        self.n_fail += 1
        if self.seen[sig] <= 2 and len(self.fails) < 30:
            self.fails.append(f"{rule}: {msg}")

    def score(self, item, resp, what):
        self.calls += 1
        try:
            res = self.logic.score(copy.deepcopy(item), resp)
        except Exception as exc:  # noqa: BLE001
            self.fail("R0", f"{what}: score() raised {type(exc).__name__}: {exc}")
            return None
        ok = (isinstance(res, dict) and isinstance(res.get("hit"), bool) and isinstance(res.get("errors"), int)
              and not isinstance(res.get("errors"), bool) and res["errors"] >= 0 and isinstance(res.get("metrics"), dict)
              and isinstance(res["metrics"].get("flags"), list) and isinstance(res["metrics"].get("invalid_events"), int))
        if not ok:
            self.fail("R0", f"{what}: bad result shape {str(res)[:160]}")
            return None
        try:
            _strict_json(res)
        except (TypeError, ValueError) as exc:
            self.fail("R0", f"{what}: result is not strict JSON ({exc})")
        if "scorer_exception" in res["metrics"]["flags"]:
            self.fail("R0", f"{what}: scorer fell back to its exception guard {res['metrics']['flags']}")
        return res

    def not_clean(self, res, base, what):
        """R2: a miss, or flagged, or identical to the unmutated result."""
        if res is None:
            return
        if res["hit"] and not res["metrics"]["flags"] and res != base:
            self.fail("R2", f"{what}: scored as a clean hit {json.dumps(res['metrics'], default=str)[:200]}")

    def strong(self, res, what):
        if res is not None and res["hit"]:
            self.fail("R3", f"{what}: impossible/late timing still scored as a hit (flags {res['metrics']['flags']})")

    def check_item(self, item, rng):
        L = self.logic
        good = L.example_response(copy.deepcopy(item), True)
        bad = L.example_response(copy.deepcopy(item), False)
        base = self.score(item, copy.deepcopy(good), "correct example")
        res_bad = self.score(item, copy.deepcopy(bad), "wrong example")
        if base is None:
            return
        if not base["hit"] or base["metrics"]["flags"] or base["metrics"]["invalid_events"]:
            self.fail("R1", f"correct example is not a clean hit: hit={base['hit']} flags={base['metrics']['flags']}")
        if res_bad is not None and res_bad["hit"]:
            self.fail("R1", "wrong example scored as a hit")

        # R6 junk
        for j in JUNK:
            r = self.score(item, copy.deepcopy(j), f"junk {j!r}")
            if r is not None and r["hit"]:
                self.fail("R6", f"junk {j!r} scored as a hit")

        # R2/R3 timing: all timing leaves at once, present-only and including nulls
        tpaths = timing_paths(self.id, good)
        if self.timing in ("window", "limit") and not tpaths:
            self.fail("R3", "task declares timing but its response has no timing fields")
        values = list(BAD_TIMES)
        late_value = None
        if self.window is not None and self.window + 5000 < self.ceiling:
            late_value = self.window + 5000
            values.append(late_value)
        for v in values:
            for mode in ("present", "all"):
                resp = copy.deepcopy(good)
                n = 0
                for path, drift in tpaths:
                    if drift and v in (-5, 0) and not isinstance(v, bool):
                        continue
                    if mode == "present" and _get(resp, path) is None:
                        continue
                    _set(resp, path, v)
                    n += 1
                if not n:
                    continue
                what = f"every timing field ({mode}) = {v!r}"
                r = self.score(item, resp, what)
                if self.timing == "untimed" and v is None:
                    continue
                self.not_clean(r, base, what)
                strong = (self.timing == "window" or (self.timing == "limit" and not (v == 0 and not isinstance(v, bool))))
                if strong:
                    self.strong(r, what)

        # one timing leaf at a time (sampled) + R4 event level
        present = [(p, d) for p, d in tpaths if _get(good, p) is not None]
        for path, drift in rng.sample(present, min(len(present), 12)):
            for v in ([999999, NAN, "450"] if drift else [999999, -5, NAN, "450", INF]):
                resp = copy.deepcopy(good)
                _set(resp, path, v)
                what = f"timing field {list(path)} = {v!r}"
                r = self.score(item, resp, what)
                self.not_clean(r, base, what)
                es0 = base["metrics"].get("event_status")
                if (r is not None and es0 and not drift and path[-1] in ("rt", "t")
                        and r["metrics"].get("event_status", {}).get("timely", 0) >= es0.get("timely", 0)):
                    self.fail("R4", f"{what}: the event was still counted as timely")

        # R2 wrong types at every node (sampled) and deleted keys (sampled)
        nodes = _paths(good)
        shallow = [p for p, _ in nodes if len(p) <= 2]
        deep = [p for p, _ in nodes if len(p) > 2]
        chosen = shallow[:60] + rng.sample(deep, min(len(deep), 30))
        for path in chosen:
            orig = _get(good, path)
            for v in WRONG.get(type(orig), []):
                resp = copy.deepcopy(good)
                _set(resp, path, v)
                what = f"type: {list(path)} {type(orig).__name__} -> {v!r}"
                self.not_clean(self.score(item, resp, what), base, what)
        dict_keys = [p for p, _ in nodes if isinstance(p[-1], str)]
        if isinstance(good, dict):
            pass
        for path in dict_keys[:40] + rng.sample(dict_keys[40:], min(len(dict_keys[40:]), 20)):
            resp = copy.deepcopy(good)
            del _get(resp, path[:-1])[path[-1]]
            what = f"deleted key {list(path)}"
            self.not_clean(self.score(item, resp, what), base, what)

        # R5 benign extra fields
        resp = copy.deepcopy(good)
        for path, v in [((), resp)] + _paths(resp):
            obj = _get(resp, path)
            if isinstance(obj, dict):
                obj["zz_unknown_field"] = 1
        r = self.score(item, resp, "extra unknown fields")
        if r is not None and r != base:
            self.fail("R5", "an unknown extra field changed the result")

        # structure of the top-level lists
        for lp in _top_lists(good):
            seq = _get(good, lp)
            if not seq:
                continue
            name = list(lp) or "response"
            for kind in ("reverse", "empty", "half", "dup", "nulls", "oversize"):
                resp = copy.deepcopy(good)
                if kind == "reverse":
                    new = seq[::-1]
                elif kind == "empty":
                    new = []
                elif kind == "half":
                    new = seq[: len(seq) // 2]
                elif kind == "dup":
                    new = seq + seq
                elif kind == "nulls":
                    new = [None] * len(seq)
                else:
                    new = [copy.deepcopy(seq[i % len(seq)]) for i in range(OVERSIZE)]
                resp = _set(resp, lp, new)
                what = f"{kind} {name}"
                t0 = time.perf_counter()
                r = self.score(item, resp, what)
                dt = time.perf_counter() - t0
                if kind in ("dup", "nulls", "oversize"):
                    self.not_clean(r, base, what)
                if kind == "oversize" and dt > 2.0:
                    self.fail("R7", f"{what}: took {dt:.2f} s")

    def run(self, n_items, seed=11):
        with tempfile.TemporaryDirectory() as tmp:
            def save_image(name, img):
                fname = f"{self.id}_{name}.png"
                img.save(Path(tmp) / fname)
                return fname
            n = max(2, n_items + n_items % 2)
            items = self.logic.generate(random.Random(seed), n, save_image)[:n_items]
        if self.timing not in ("window", "limit", "untimed"):
            self.fail("decl", f"logic.TIMING must be 'window', 'limit' or 'untimed' (got {self.timing!r})")
        if self.timing in ("window", "limit") and not self.window:
            self.fail("decl", f"TIMING {self.timing!r} needs {'WINDOW_MS' if self.timing == 'window' else 'LIMIT_MS'}")
        rng = random.Random(seed)
        for item in items:
            item = {k: v for k, v in item.items() if k != "file"}
            self.check_item(item, rng)
        if self.n_fail > len(self.fails):
            self.fails.append(f"... {self.n_fail} failure(s) in all, similar ones not repeated")
        return self.fails


def run(task_ids=None, n_items=2, verbose=False, out=print):
    from app.tasks import LOAD_ERRORS, PLUGINS
    failures = {}
    for folder, err in LOAD_ERRORS.items():
        failures[folder] = [f"load error: {err}"]
    ids = task_ids or sorted(PLUGINS, key=lambda t: PLUGINS[t].folder.name)
    for tid in ids:
        if tid not in PLUGINS:
            failures[tid] = ["unknown task id"]
            continue
        t0 = time.perf_counter()
        ch = Checker(tid, PLUGINS[tid], verbose)
        fails = ch.run(n_items)
        dt = time.perf_counter() - t0
        out(f"{'ok  ' if not fails else 'FAIL'} {tid:28s} timing={ch.timing!s:8s} calls={ch.calls:5d} {dt:5.1f}s")
        if fails:
            failures[tid] = fails
            for f in fails:
                out(f"       {f}")
    return failures


def main(argv):
    n_items, verbose, ids = 2, False, []
    it = iter(argv)
    for a in it:
        if a == "--items":
            n_items = int(next(it))
        elif a == "--verbose":
            verbose = True
        else:
            ids.append(a)
    failures = run(ids or None, n_items, verbose)
    print(f"\n{len(failures)} task(s) with failures" if failures else "\nall tasks pass the adversarial checks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
