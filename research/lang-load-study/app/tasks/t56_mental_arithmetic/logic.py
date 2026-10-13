"""Mental arithmetic (card 56): work out each problem in your head and type the answer on
an on-screen keypad (or the keyboard). One trial is 4 problems, one of each kind, in
shuffled order, each with a fixed 20 s response deadline:

  add   two 2-digit numbers, exactly one carry           (1 step)
  sub   2-digit minus 2-digit, exactly one borrow        (1 step)
  mul   2-digit times 1-digit, carry from the ones       (1 step)
  two   (b x c) + a with explicit brackets, carry in sum (2 steps)

All answers are whole numbers from 0 to 999, shown and typed without separators, so
decimal-comma / thousands-separator conventions never matter. The two items of a pair
(k, k+1) have the same kinds in the same order with different numbers. The answer key is
computed by a small expression parser over the displayed tokens (not stored in the item).
"""
import statistics
import unicodedata
from fractions import Fraction

KINDS = ["add", "sub", "mul", "two"]
STEPS = {"add": 1, "sub": 1, "mul": 1, "two": 2}
DEADLINE_MS = 20000


def _problem(rng, kind):
    while True:
        if kind == "add":
            a, b = rng.randint(12, 79), rng.randint(12, 79)
            if a % 10 + b % 10 >= 10 and a + b < 100:
                return [str(a), "+", str(b)]
        elif kind == "sub":
            a, b = rng.randint(31, 98), rng.randint(12, 89)
            if a > b + 5 and a % 10 < b % 10:
                return [str(a), "-", str(b)]
        elif kind == "mul":
            a, b = rng.randint(12, 49), rng.randint(3, 9)
            if (a % 10) * b >= 10 and a % 10 != 0:
                return [str(a), "*", str(b)]
        else:
            b, c, a = rng.randint(3, 9), rng.randint(3, 9), rng.randint(12, 49)
            if (b * c) % 10 + a % 10 >= 10:
                return ["(", str(b), "*", str(c), ")", "+", str(a)]


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        order = KINDS[:]
        rng.shuffle(order)
        pair = []
        for _ in range(2):
            while True:
                probs = [{"kind": kind, "tokens": _problem(rng, kind)} for kind in order]
                if not pair or all(p["tokens"] != q["tokens"] for p, q in zip(probs, pair[0]["problems"])):
                    break
            pair.append({"problems": probs, "deadline_ms": DEADLINE_MS})
        items.extend(pair)
    return items[:n]


def evaluate(tokens):
    """Independent arithmetic key: recursive-descent parser with the usual precedence
    (brackets, then x and /, then + and -), exact fractions."""
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom():
        t = take()
        if t == "(":
            v = expr()
            if take() != ")":
                raise ValueError("bracket")
            return v
        return Fraction(int(t))

    def term():
        v = atom()
        while peek() in ("*", "/"):
            v = v * atom() if take() == "*" else v / atom()
        return v

    def expr():
        v = term()
        while peek() in ("+", "-"):
            v = v + term() if take() == "+" else v - term()
        return v

    v = expr()
    if pos != len(tokens):
        raise ValueError("trailing tokens")
    return v


def parse_int(s):
    """Typed answer -> int or None. Accepts any Unicode decimal digits and a leading
    minus; rejects anything else (no separators are ever needed)."""
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
    """response: [{"answer": "56" | null, "rt": ms | null, "timed_out": bool}] in problem order.
    A problem is correct when the typed whole number equals the parser's value and it was
    entered before the deadline. hit = at least 3 of the 4 problems correct.
    Omissions (nothing entered in time) count as errors and are reported separately."""
    probs = item.get("problems", []) if isinstance(item, dict) else []
    resp = response if isinstance(response, list) else []
    rows = []
    for k, p in enumerate(probs):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        key = evaluate(p["tokens"])
        given = None if r.get("timed_out") else parse_int(r.get("answer"))
        rt = r.get("rt") if isinstance(r.get("rt"), (int, float)) and not isinstance(r.get("rt"), bool) else None
        rows.append({"kind": p["kind"], "ok": given is not None and given == key, "rt": rt, "omit": given is None})
    n = len(rows) or 1
    n_ok = sum(r["ok"] for r in rows)
    rts = [r["rt"] for r in rows if r["ok"] and r["rt"]]
    return {"hit": bool(rows) and n_ok >= 3, "errors": len(rows) - n_ok,
            "metrics": {"accuracy": round(n_ok / n, 3),
                        "correct_by_kind": {r["kind"]: r["ok"] for r in rows},
                        "accuracy_1_step": _acc([r for r in rows if STEPS[r["kind"]] == 1]),
                        "accuracy_2_step": _acc([r for r in rows if STEPS[r["kind"]] == 2]),
                        "median_rt_correct": round(statistics.median(rts), 1) if rts else None,
                        "omissions": sum(r["omit"] for r in rows)}}


def _acc(rows):
    return round(sum(r["ok"] for r in rows) / len(rows), 3) if rows else None


def example_response(item, correct=True):
    out = []
    for p in item["problems"]:
        v = int(evaluate(p["tokens"]))
        out.append({"answer": str(v if correct else v + 10), "rt": 4000, "timed_out": False})
    return out
