"""Number sequences (card 52): six numbers are shown; type the number that comes next.
The instructions state the only rule families used (a finite sequence fits many rules,
so the family is restricted and stated):

  add   add (or subtract) the same number each time         3, 8, 13, 18, ...
  mul   multiply by 2 each time                             3, 6, 12, 24, ...
  grow  the step grows by the same amount each time         2, 3, 5, 8, 12, ...
  alt   two sequences take turns, each adding its own step  4, 30, 7, 27, 10, 24, ...

One trial = 4 sequences, one per family, shuffled. Both items of a pair (k, k+1) use the
same family order and parameter ranges with different numbers. All values are whole
numbers 0..999.

Answer key (oracle, in score()): every stated family is fitted to the six shown numbers;
the prediction of EVERY family that fits exactly is accepted (documented alternatives).
The generator additionally rejects sequences where two families predict different
numbers, so in practice the accepted set has one value.
"""
import statistics
import unicodedata

FAMILIES = ["add", "mul", "grow", "alt"]
SHOWN = 6


def _make(rng, fam, desc):
    if fam == "add":
        d = rng.randint(3, 15)
        if not desc:
            start = rng.randint(2, 60)
            return [start + d * i for i in range(SHOWN + 1)]
        start = rng.randint(7 * d, 7 * d + 60)
        return [start - d * i for i in range(SHOWN + 1)]
    if fam == "mul":
        s = rng.randint(2, 14)
        return [s * 2 ** i for i in range(SHOWN + 1)]
    if fam == "grow":
        t, d, dd = rng.randint(1, 30), rng.randint(1, 6), rng.randint(1, 4)
        seq = [t]
        for i in range(SHOWN):
            seq.append(seq[-1] + d + i * dd)
        return seq
    a, da = rng.randint(1, 30), rng.randint(2, 9)
    db = rng.randint(2, 9)
    b = rng.randint(3 * db + 20, 3 * db + 80)
    seq = []
    for i in range(SHOWN + 1):
        seq.append(a + da * (i // 2) if i % 2 == 0 else b - db * (i // 2))
    return seq


def _arith(xs):
    return all(xs[i + 1] - xs[i] == xs[1] - xs[0] for i in range(len(xs) - 1))


def fits(terms):
    """Oracle: {family: predicted next number} for every stated family that fits exactly."""
    t = list(terms)
    out = {}
    if len(t) < 4:
        return out
    diffs = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    if _arith(t):
        out["add"] = t[-1] + diffs[-1]
    if all(x != 0 for x in t) and all(t[i + 1] == 2 * t[i] for i in range(len(t) - 1)):
        out["mul"] = t[-1] * 2
    if _arith(diffs):
        out["grow"] = t[-1] + diffs[-1] + (diffs[-1] - diffs[-2])
    ev, od = t[0::2], t[1::2]
    if len(ev) >= 3 and len(od) >= 3 and _arith(ev) and _arith(od):
        nxt = ev if len(t) % 2 == 0 else od
        out["alt"] = nxt[-1] + (nxt[-1] - nxt[-2])
    return out


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        order = FAMILIES[:]
        rng.shuffle(order)
        desc = rng.random() < 0.5  # same direction for "add" in both items of the pair
        for _ in range(2):
            seqs = []
            for fam in order:
                while True:
                    s = _make(rng, fam, desc)
                    shown = s[:SHOWN]
                    preds = set(fits(shown).values())
                    if (min(s) >= 0 and max(s) <= 999 and preds == {s[SHOWN]}
                            and fits(shown).get(fam) == s[SHOWN] and len(set(shown)) == SHOWN):
                        break
                seqs.append({"family": fam, "terms": shown})
            items.append({"sequences": seqs})
    return items[:n]


def parse_int(s):
    """Typed answer -> int or None (any Unicode decimal digits, optional leading minus)."""
    if isinstance(s, bool) or not isinstance(s, (str, int)):
        return None
    s = str(s).strip().replace(" ", "")
    neg = s[:1] in ("-", "−")
    if neg:
        s = s[1:]
    if not s or len(s) > 7:
        return None
    try:
        v = int("".join(str(unicodedata.decimal(ch)) for ch in s))
    except (TypeError, ValueError):
        return None
    return -v if neg else v


def score(item, response):
    """response: [{"answer": "29" | null, "rt": ms}] in sequence order.
    A sequence is correct when the typed number equals the prediction of any stated rule
    family that fits the shown numbers exactly. hit = at least 3 of the 4 correct."""
    seqs = item.get("sequences", []) if isinstance(item, dict) else []
    resp = response if isinstance(response, list) else []
    rows = []
    for k, s in enumerate(seqs):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        accepted = set(fits(s["terms"]).values())
        given = parse_int(r.get("answer"))
        rt = r.get("rt") if isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) else None
        rows.append({"family": s["family"], "ok": given is not None and given in accepted, "rt": rt,
                     "omit": given is None, "n_accepted": len(accepted)})
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"]]
    return {"hit": bool(rows) and n_ok >= 3, "errors": len(rows) - n_ok,
            "metrics": {"accuracy": round(n_ok / (len(rows) or 1), 3),
                        "correct_by_family": {r["family"]: r["ok"] for r in rows},
                        "rt_by_family": {r["family"]: r["rt"] for r in rows},
                        "median_rt_correct": round(statistics.median(rts), 1) if rts else None,
                        "omissions": sum(r["omit"] for r in rows),
                        "sequences_with_alternatives": sum(r["n_accepted"] > 1 for r in rows)}}


def example_response(item, correct=True):
    out = []
    for s in item["sequences"]:
        v = min(fits(s["terms"]).values())
        out.append({"answer": str(v if correct else v + 1), "rt": 8000})
    return out
