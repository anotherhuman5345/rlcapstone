"""Scheduling (card 66): assign every job to one person on one day, so that each person does
at most one job per day and every written rule holds. Rules are verbal templates in
text/<lang>.json ("templates"), filled with job, person and day names from the same file;
items hold only rule types and indices.
The generator picks a hidden feasible schedule, adds true rules at random while they still
cut down the set of feasible schedules, stops once at most 4 remain and drops rules whose
removal would not change that set (no contradictions, no spare rules). An exhaustive
solver over all schedules (bitsets of schedule indices) counts the valid ones.
Pairs (k, k+1) have the same people/days/jobs, the same multiset of rule types and the
same number of valid schedules; pairs alternate 2 people x 3 days x 4 jobs and
3 people x 3 days x 5 jobs. score() checks the submitted schedule against every rule
itself, so any valid schedule is accepted."""
import functools
import json
from itertools import permutations

from app.tasks import _guard as G

TIMING = "limit"         # the Done press (rt_ms) must come inside LIMIT_MS
CEILING_MS = G.trial_ceiling(__file__)
N_JOBS_TEXT = 8          # job names in text/<lang>.json "jobs" (3 "people", 3 "days")
LEVELS = ((2, 3, 4, 3, 5), (3, 3, 5, 4, 6))   # people, days, jobs, min rules, max rules
MAX_VALID = 4
LIMIT_MS = 90000         # view.js: setTimeout(() => end(true, false), it.limit_ms || 90000)
TYPES = ("before", "same_day", "diff_day", "by_day", "off_day", "only_person", "not_person", "same_person")


def holds(rule, sched):
    """sched[j] = (person, day) of job j."""
    t = rule["type"]
    if t == "off_day":
        return all(not (p == rule["w"] and d == rule["d"]) for p, d in sched)
    pa, da = sched[rule["a"]]
    if t == "by_day":
        return da <= rule["d"]
    if t == "only_person":
        return pa == rule["w"]
    if t == "not_person":
        return pa != rule["w"]
    pb, db = sched[rule["b"]]
    if t == "before":
        return da < db
    if t == "same_day":
        return da == db
    if t == "diff_day":
        return da != db
    if t == "same_person":
        return pa == pb
    raise ValueError(t)


def all_schedules(people, days, jobs):
    cells = [(p, d) for p in range(people) for d in range(days)]
    return list(permutations(cells, jobs))


def valid_schedules(item, rules=None):
    rules = item["rules"] if rules is None else rules
    return [s for s in all_schedules(item["people"], item["days"], item["jobs"]) if all(holds(r, s) for r in rules)]


def _candidates(people, days, jobs, sched):
    out = []
    for a in range(jobs):
        out += [{"type": "by_day", "a": a, "d": d} for d in range(1, days - 1)]  # never "by the first day"
        out += [{"type": t, "a": a, "w": w} for t in ("only_person", "not_person") for w in range(people)]
        for b in range(jobs):
            if a == b:
                continue
            out.append({"type": "before", "a": a, "b": b})
            if a < b:
                out += [{"type": t, "a": a, "b": b} for t in ("same_day", "diff_day", "same_person")]
    out += [{"type": "off_day", "w": w, "d": d} for w in range(people) for d in range(days)]
    return [r for r in out if holds(r, sched)]


class _Space:
    """All schedules for one size, with a bitset of satisfying schedules per rule."""
    def __init__(self, people, days, jobs):
        self.scheds = all_schedules(people, days, jobs)
        self.full = (1 << len(self.scheds)) - 1
        self.cache = {}

    def mask(self, rule):
        key = tuple(sorted(rule.items()))
        if key not in self.cache:
            m = 0
            for i, s in enumerate(self.scheds):
                if holds(rule, s):
                    m |= 1 << i
            self.cache[key] = m
        return self.cache[key]

    def count(self, rules):
        m = self.full
        for r in rules:
            m &= self.mask(r)
        return bin(m).count("1")

    def minimal(self, rules):
        k = self.count(rules)
        return all(self.count(rules[:i] + rules[i + 1:]) != k for i in range(len(rules)))


def _first(rng, sp, people, days, jobs, lo, hi):
    while True:
        sched = rng.choice(sp.scheds)
        cands = _candidates(people, days, jobs, sched)
        rng.shuffle(cands)
        rules, k = [], len(sp.scheds)
        for r in cands:
            k2 = sp.count(rules + [r])
            if k2 < k:
                rules, k = rules + [r], k2
            if k <= MAX_VALID:
                break
        changed = True
        while changed:
            changed = False
            for i in range(len(rules)):
                rest = rules[:i] + rules[i + 1:]
                if sp.count(rest) == k:
                    rules, changed = rest, True
                    break
        if k <= MAX_VALID and lo <= len(rules) <= hi:
            return rules, k


def _partner(rng, sp, people, days, jobs, types, k):
    for _ in range(4000):
        sched = rng.choice(sp.scheds)
        cands = _candidates(people, days, jobs, sched)
        rules = []
        for t in types:
            opts = [c for c in cands if c["type"] == t and c not in rules]
            if not opts:
                break
            rules.append(rng.choice(opts))
        if len(rules) == len(types) and sp.count(rules) == k and sp.minimal(rules):
            return rules
    return None


def generate(rng, n, save_image):
    items, spaces = [], {}
    while len(items) < n:
        people, days, jobs, lo, hi = LEVELS[(len(items) // 2) % len(LEVELS)]
        sp = spaces.setdefault((people, days, jobs), _Space(people, days, jobs))
        a, k = _first(rng, sp, people, days, jobs, lo, hi)
        b = _partner(rng, sp, people, days, jobs, sorted(r["type"] for r in a), k)
        if b is None:
            continue
        for rules in (a, b):
            rng.shuffle(rules)
            items.append({"people": people, "days": days, "jobs": jobs,
                          "job_names": rng.sample(range(N_JOBS_TEXT), jobs),
                          "rules": rules, "n_valid": k, "limit_ms": LIMIT_MS})
    return items[:n]


@functools.lru_cache(maxsize=256)
def _solver_summary(key):
    """(number of valid schedules, fewest days any of them needs) for one item, memoized on
    a JSON key of the item fields the solver reads."""
    people, days, jobs, rules = json.loads(key)
    valid = valid_schedules({"people": people, "days": days, "jobs": jobs, "rules": rules})
    return len(valid), (min(max(d for _, d in s) + 1 for s in valid) if valid else None)


def _assign(a, assign, P, D, J):
    """The submitted schedule: (list of (person, day) or None per job, complete). null =
    an unplaced job (the browser sends it on time-out / give up). A value that is not a
    list of J entries, or an entry that is not null or a real [person, day] cell, is
    malformed (flagged)."""
    if assign is G.MISSING:
        a.malformed("missing_assign")
        return None, False
    if not isinstance(assign, list):
        a.malformed("invalid_assign")
        return None, False
    if len(assign) != J:
        a.malformed("missing_assign_entries" if len(assign) < J else "extra_assign_entries")
        return None, False
    sched = []
    for x in assign:
        if x is None:
            sched.append(None)
        elif (isinstance(x, list) and len(x) == 2 and G.member(x[0], range(P))
              and G.member(x[1], range(D))):
            sched.append((x[0], x[1]))
        else:
            a.malformed("invalid_assign_entry")
            return None, False
    return sched, all(c is not None for c in sched)


@G.safe
def score(item, response):
    """response: {"assign": [[person, day] for job 0..jobs-1], "changes", "first_move_ms",
    "rt_ms", "gave_up"} (0-based person and day indices; null for an unplaced job).
    hit = every job is placed in a real (person, day) cell, no cell holds two jobs
    (one job per person per day), every rule holds (any such schedule counts) AND the
    schedule was sent with a valid rt_ms inside the 90 s limit (a missing, non-finite,
    negative or late time never counts).
    errors = number of broken rules (all rules if the schedule is incomplete or has a
    clash). Metrics also hold the solver's count of valid schedules, the days used
    (last day with a job) against the fewest days any valid schedule needs (descriptive
    only: participants are not asked to minimise days), changes and times. A clash (two
    jobs in one cell, which the browser cannot send) and malformed fields are flagged."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk()
    P, D, J, rules = item["people"], item["days"], item["jobs"], item["rules"]
    sched, complete = _assign(a, response.get("assign", G.MISSING), P, D, J)
    placed = [c for c in sched if c is not None] if sched else []
    clash = len(set(placed)) != len(placed)
    if clash:
        a.malformed("clash")
    ok = complete and not clash
    broken = sum(1 for r in rules if not holds(r, sched)) if ok else len(rules)
    st, rt = a.time(response.get("rt_ms"), field="rt_ms", window=LIMIT_MS, required=True)
    correct = ok and broken == 0
    if correct and st != G.TIMELY:
        a.flag("solved_outside_time_limit")
    hit = correct and st == G.TIMELY
    n_valid, min_days = _solver_summary(json.dumps([P, D, J, rules], sort_keys=True))
    return a.finish(hit, broken, {
        "complete": complete, "clash": bool(clash), "broken_rules": broken,
        "rules": len(rules), "n_valid": n_valid,
        "days_used": max(d for _, d in sched) + 1 if hit else None,
        "min_days": min_days,
        "changes": a.opt_int(response, "changes"),
        "first_move_ms": a.duration(response, "first_move_ms", window=LIMIT_MS),
        "rt_ms": rt, "rt_status": st, "gave_up": a.opt_bool(response, "gave_up")})


def example_response(item, correct=True):
    sched = [list(c) for c in valid_schedules(item)[0]]
    if not correct:
        sched[0] = list(sched[1])   # two jobs in one cell is never valid
    return {"assign": sched, "changes": item["jobs"], "first_move_ms": 6000, "rt_ms": 45000, "gave_up": False}
