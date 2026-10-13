"""Form completion (card 68), adapted to one trial = one original form.

A fictional reference record (invented names and numbers, no real personal data) is
shown next to an empty 9-field form and 3 exception rules. Exactly 2 of the 3 rules
apply to this record; the third is a lure that must NOT be applied. The participant
copies the record into the form, applying the rules, and presses Submit.

The gold form is computed in score() from the record and the rule list by an
independent rule engine (gold_form); generation only controls which rule conditions
are true. Rule texts, field labels, month/plan/contact names come from the text file.
Pairs (k, k+1) share the rule set and which rules apply; record values differ.
"""
import re

RULES = 5                 # text "rules": 0 junior, 1 amount cap, 2 no phone, 3 short postcode, 4 capitals
JUNIOR_YEAR = 2008
FIELDS = ["family", "given", "member", "birth", "postcode", "phone", "plan", "contact", "amount"]
RULE_FIELD = {0: "plan", 1: "amount", 2: "contact", 3: "postcode", 4: "family"}
CONS, VOW = "bdfgklmnprstvz", "aeou"   # no i/I, so case rules are identical in Turkish and English


def _name(rng, syll, tail):
    s = "".join(rng.choice(CONS) + rng.choice(VOW) for _ in range(syll))
    if tail:
        s += rng.choice("lmnrs")
    return s.capitalize()


def _digits(rng, k):
    return str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(k - 1))


def _record(rng, rules, on):
    trig = lambda r: r in on              # noqa: E731
    member = _digits(rng, 5)
    member += "7" if trig(4) else str(rng.choice([0, 1, 2, 3, 4, 5, 6, 8, 9]))
    year = rng.randint(JUNIOR_YEAR, JUNIOR_YEAR + 4) if trig(0) else rng.randint(1950, 2003)
    return {"family": _name(rng, 2, True), "given": _name(rng, 2, rng.random() < 0.5),
            "member": member, "birth": [rng.randint(1, 28), rng.randint(1, 12), year],
            "postcode": _digits(rng, 4 if trig(3) else 5),
            "phone": None if trig(2) else _digits(rng, 4) + " " + "".join(str(rng.randint(0, 9)) for _ in range(4)),
            "plan": rng.randint(0, 1),
            "contact": rng.randint(0, 1) if trig(2) else rng.randint(0, 2),
            "amount": rng.randint(52, 99) * 10 if trig(1) else rng.randint(5, 48) * 10}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        rules = rng.sample(range(RULES), 3)
        on = rng.sample(rules, 2)
        for _ in range(2):
            items.append({"record": _record(rng, rules, on), "rules": rng.sample(rules, 3),
                          "junior_year": JUNIOR_YEAR, "limit_ms": 230000})
    return items[:n]


def gold_form(record, rules, junior_year):
    """Independent rule engine: the correctly completed form for this record and rule list,
    plus the set of fields where a rule changed the copied value."""
    g = {"family": record["family"], "given": record["given"], "member": record["member"],
         "birth": list(record["birth"]), "postcode": record["postcode"],
         "phone": re.sub(r"\D", "", record["phone"] or ""), "plan": record["plan"],
         "contact": record["contact"], "amount": record["amount"]}
    changed = set()
    if 0 in rules and record["birth"][2] >= junior_year:
        g["plan"] = 2
        changed.add("plan")
    if 1 in rules and record["amount"] > 500:
        g["amount"] = 500
        changed.add("amount")
    if 2 in rules and not record["phone"]:
        g["contact"] = 2
        changed.add("contact")
    if 3 in rules and len(record["postcode"]) == 4:
        g["postcode"] = "0" + record["postcode"]
        changed.add("postcode")
    if 4 in rules and record["member"].endswith("7"):
        g["family"] = record["family"].upper()
        changed.add("family")
    return g, changed


def _text(v):
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else None


def _int(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip().replace(" ", "")
        m = re.fullmatch(r"(\d+)(?:[.,]0+)?", s)
        return int(m.group(1)) if m else None
    return None


def _field_ok(name, value, gold):
    if name in ("family", "given"):
        return _text(value) == gold                          # exact copy, case included
    if name in ("member", "postcode"):
        return isinstance(value, str) and value.replace(" ", "").strip() == gold
    if name == "phone":
        return isinstance(value, str) and not re.search(r"[^\d\s\-()]", value) and re.sub(r"\D", "", value) == gold
    if name == "birth":
        m = re.fullmatch(r"\s*(\d{1,2})\s*[./\-]\s*(\d{1,2})\s*[./\-]\s*(\d{4})\s*", value) if isinstance(value, str) else None
        return bool(m) and [int(x) for x in m.groups()] == gold
    return _int(value) == gold                               # plan, contact, amount


def score(item, response):
    """response: {"fields": {family, given, member, birth, postcode, phone: str;
    plan, contact: option index or null; amount: str}, "time_ms": ms, "help_views": int,
    "autofill_events": int, "paste_events": int}.
    Text is compared after trimming and collapsing spaces; names must match exactly
    (case included, because one rule concerns capitals); numbers by their digits; the date
    as day.month.year (dots, slashes or dashes).
    exception errors = wrong fields among those a triggered rule changes; over-applied =
    the lure rule's effect was applied although its condition was false.
    hit = no exception errors AND at most 1 other field wrong."""
    miss = {"hit": False, "errors": len(FIELDS), "metrics": {}}
    if not isinstance(response, dict) or not isinstance(response.get("fields"), dict):
        return miss
    f = response["fields"]
    rec = item["record"]
    gold, changed = gold_form(rec, item["rules"], item["junior_year"])
    wrong = [k for k in FIELDS if not _field_ok(k, f.get(k), gold[k])]
    exc_err = [k for k in wrong if k in changed]
    other = [k for k in wrong if k not in changed]
    lure_rules = [r for r in item["rules"] if RULE_FIELD[r] not in changed]
    over = 0
    for r in lure_rules:
        k = RULE_FIELD[r]
        v = f.get(k)
        if r == 0 and _int(v) == 2 or r == 1 and _int(v) == 500 or r == 2 and _int(v) == 2 != rec["contact"] \
                or r == 3 and isinstance(v, str) and v.strip() == "0" + rec["postcode"] \
                or r == 4 and isinstance(v, str) and _text(v) == rec["family"].upper():
            over += 1
    num = lambda k: int(response[k]) if isinstance(response.get(k), (int, float)) and not isinstance(response.get(k), bool) else None  # noqa: E731
    return {"hit": not exc_err and len(other) <= 1,
            "errors": len(wrong),
            "metrics": {"fields_correct": len(FIELDS) - len(wrong), "fields_total": len(FIELDS),
                        "exception_errors": len(exc_err), "exceptions_total": len(changed),
                        "other_errors": len(other), "wrong_fields": wrong, "over_applied_rules": over,
                        "time_ms": num("time_ms"), "help_views": num("help_views"),
                        "autofill_events": num("autofill_events"), "paste_events": num("paste_events")}}


def example_response(item, correct=True):
    gold, changed = gold_form(item["record"], item["rules"], item["junior_year"])
    d, m, y = gold["birth"]
    fields = {"family": gold["family"], "given": gold["given"], "member": gold["member"],
              "birth": f"{d:02d}.{m:02d}.{y}", "postcode": gold["postcode"], "phone": gold["phone"],
              "plan": gold["plan"], "contact": gold["contact"], "amount": str(gold["amount"])}
    if not correct:   # copy the record as-is, ignoring every exception rule
        rec = item["record"]
        fields.update({"family": rec["family"], "postcode": rec["postcode"], "plan": rec["plan"],
                       "contact": rec["contact"], "amount": str(rec["amount"])})
    return {"fields": fields, "time_ms": 60000, "help_views": 0, "autofill_events": 0, "paste_events": 0}
