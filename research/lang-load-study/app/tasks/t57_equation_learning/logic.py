"""Equation learning (card 57): two invented symbol operations are explained in words
(text file) with two worked examples each, plus a stated precedence ("work out HI
before LO"). After Start, the person evaluates 4 new expressions with the keypad:
  2 single  - one operation each, new numbers           (rule application)
  2 transfer - both operations: [a HI b LO c] and [a LO b HI c] (precedence + combination)
The rule explanations stay visible (this is learning-from-instructions, not memory).

Each item uses one "additive" and one "multiplicative" rule. Rules come in matched
couples (e.g. "2a+b" / "a+2b", "ab-1" / "ab+1"); the two items of a pair (k, k+1) get
the two members of the same couples and different symbols, so they are equally hard
but never share a rule. The symbols carry no arithmetic meaning.

Answer key (oracle, in score()): a shunting-yard parser over the shown tokens with the
item's stated precedence (HI binds tighter, left-associative), then the rule formulas.
"""
import unicodedata

from app.tasks import _guard as G

TIMING = "untimed"   # view.js ask() has no time limit; rt / study_ms are descriptive (see _guard.py)
CEILING_MS = G.trial_ceiling(__file__)

RULES = {  # rule id -> formula; the words for each id are in text/<lang>.json "rule_<id>"
    "dbl_first": lambda a, b: 2 * a + b,
    "dbl_second": lambda a, b: a + 2 * b,
    "sum_dbl": lambda a, b: 2 * (a + b),
    "sum_ten": lambda a, b: a + b + 10,
    "mul_minus1": lambda a, b: a * b - 1,
    "mul_plus1": lambda a, b: a * b + 1,
    "mul_plus_first": lambda a, b: a * b + a,
    "mul_plus_second": lambda a, b: a * b + b,
}
ADD_COUPLES = [("dbl_first", "dbl_second"), ("sum_dbl", "sum_ten")]
MUL_COUPLES = [("mul_minus1", "mul_plus1"), ("mul_plus_first", "mul_plus_second")]
SYMBOLS = ["◆", "●", "▲", "■", "★", "✚"]  # ◆ ● ▲ ■ ★ ✚


def _value_direct(form, nums, hi, lo, rules):
    """Generator-side value from the known structure (independent of the parser)."""
    a, b, c = nums
    f = {s: RULES[r] for s, r in rules.items()}
    if form == "hi_lo":
        return f[lo](f[hi](a, b), c)
    return f[lo](a, f[hi](b, c))


def _item(rng, add_rule, mul_rule, syms):
    hi_rule, lo_rule = (add_rule, mul_rule) if rng.random() < 0.5 else (mul_rule, add_rule)
    hi, lo = syms
    rules = {hi: hi_rule, lo: lo_rule}
    examples = []
    for s in (hi, lo):
        for _ in range(2):
            a, b = rng.randint(1, 9), rng.randint(1, 9)
            examples.append({"tokens": [a, s, b], "value": RULES[rules[s]](a, b)})
    problems = []
    order = [hi, lo]
    rng.shuffle(order)
    for s in order:
        while True:
            a, b = rng.randint(2, 9), rng.randint(2, 9)
            if [a, s, b] not in [e["tokens"] for e in examples]:
                break
        problems.append({"kind": "single", "tokens": [a, s, b], "expected": RULES[rules[s]](a, b)})
    forms = ["hi_lo", "lo_hi"]
    rng.shuffle(forms)
    for form in forms:
        while True:
            nums = [rng.randint(1, 6) for _ in range(3)]
            v = _value_direct(form, nums, hi, lo, rules)
            if 0 <= v <= 999:
                break
        a, b, c = nums
        toks = [a, hi, b, lo, c] if form == "hi_lo" else [a, lo, b, hi, c]
        problems.append({"kind": "transfer", "form": form, "tokens": toks, "expected": v})
    return {"hi": hi, "lo": lo, "rules": rules, "examples": examples, "problems": problems}


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        ac, mc = list(rng.choice(ADD_COUPLES)), list(rng.choice(MUL_COUPLES))
        rng.shuffle(ac)
        rng.shuffle(mc)
        syms = SYMBOLS[:]
        rng.shuffle(syms)
        for j in range(2):
            it = _item(rng, ac[j], mc[j], syms[2 * j:2 * j + 2])
            for p in it["problems"]:
                p.pop("expected")  # the key is recomputed by the parser in score()
            items.append(it)
    return items[:n]


def evaluate(tokens, hi, lo, rules):
    """Oracle: shunting-yard with precedence HI (2) > LO (1), left-associative."""
    prec = {hi: 2, lo: 1}
    out, ops = [], []

    def apply(op):
        b, a = out.pop(), out.pop()
        out.append(RULES[rules[op]](a, b))

    expect_num = True
    for t in tokens:
        if expect_num:
            if isinstance(t, bool) or not isinstance(t, int):
                raise ValueError("number expected")
            out.append(t)
        else:
            if t not in prec:
                raise ValueError("operator expected")
            while ops and prec[ops[-1]] >= prec[t]:
                apply(ops.pop())
            ops.append(t)
        expect_num = not expect_num
    if expect_num:
        raise ValueError("dangling operator")
    while ops:
        apply(ops.pop())
    return out[0]


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


@G.safe
def score(item, response):
    """response: {"study_ms": ms, "answers": [{"answer": "23" | null, "rt": ms}]} in problem
    order, one answer per problem (missing entries are omissions, extra ones ignored; both
    flagged). The answer must be a digit string (what was typed); anything else is flagged
    and scored wrong, null is an omission.
    A problem is correct when the typed number equals the parser's value.
    hit = at least 3 of the 4 problems correct (so a transfer item must be solved).
    Untimed: rt and study_ms are descriptive, checked (finite, >= 100 ms, below the trial
    timeout) and null when bad (flagged); correctness stands."""
    a = G.Audit(CEILING_MS)
    probs = item["problems"]
    if not isinstance(response, dict):
        return a.junk(len(probs))
    ans = a.entries(response.get("answers", G.MISSING), len(probs), "answers")
    rows = []
    for k, (p, r) in enumerate(zip(probs, ans)):
        key = evaluate(p["tokens"], item["hi"], item["lo"], item["rules"])
        ev = a.obj(r)
        given, rt = None, None
        if ev is not None:
            raw = ev.get("answer", G.MISSING)
            if raw is G.MISSING:
                a.malformed("missing_answer")
            elif raw is not None:
                given = parse_int(raw) if isinstance(raw, str) else None
                if given is None:
                    a.malformed("invalid_answer")
            rt = a.duration(ev, "rt")
        rows.append({"kind": p["kind"], "ok": given is not None and given == key, "rt": rt, "omit": given is None})
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"] is not None]
    study = a.duration(response, "study_ms")
    return a.finish(bool(rows) and n_ok >= 3, len(rows) - n_ok, {
        "accuracy": round(n_ok / (len(rows) or 1), 3),
        "single_accuracy": _acc([r for r in rows if r["kind"] == "single"]),
        "transfer_accuracy": _acc([r for r in rows if r["kind"] == "transfer"]),
        "median_rt_correct": G.median(rts),
        "study_ms": study,
        "omissions": sum(r["omit"] for r in rows)})


def _acc(rows):
    return round(sum(r["ok"] for r in rows) / len(rows), 3) if rows else None


def example_response(item, correct=True):
    out = []
    for p in item["problems"]:
        v = evaluate(p["tokens"], item["hi"], item["lo"], item["rules"])
        out.append({"answer": str(v if correct else v + 3), "rt": 9000})
    return {"study_ms": 20000, "answers": out}
