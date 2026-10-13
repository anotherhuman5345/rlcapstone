"""Document reconciliation (card 65): an order (table A) and a delivery note (table B)
list the same 6 order lines in the same order, keyed by a 4-digit line number. Some cells
of B differ from A. The person clicks / taps (or tabs to and presses Enter/Space on) every
cell of B that does not match A, then presses Done.

Fields: product (an index into the text file's "products" list, so both languages show
equivalent names), quantity (whole number), date (shown as day + month NAME + year, so
day/month order can never be confused). Mismatch types: product (another product),
quantity (digits swapped or changed), date (day shifted 1-3 days or month moved by one).
Each item has one mismatch of each type plus, for half of the pairs, a 4th of a random
type; at most one mismatch per row. Both items of a pair (k, k+1) have the same number
and types of mismatches, in different rows with different content.

Answer key (oracle, in score()): table A and table B are compared cell by cell; the
mismatch coordinates are [row, field]. The generator's own list is not used.
"""
FIELDS = ["product", "qty", "date"]
ROWS = 6
N_PRODUCTS = 16


def _row(rng, used_codes):
    while True:
        code = rng.randint(1000, 9999)
        if code not in used_codes:
            used_codes.add(code)
            break
    return {"code": code, "product": rng.randrange(N_PRODUCTS), "qty": rng.randint(12, 96),
            "date": [2026, rng.randint(1, 12), rng.randint(4, 25)]}


def _alter(rng, row, field):
    new = dict(row)
    if field == "product":
        new["product"] = rng.choice([p for p in range(N_PRODUCTS) if p != row["product"]])
    elif field == "qty":
        q = row["qty"]
        swapped = int(str(q)[::-1])
        new["qty"] = swapped if swapped != q and q % 10 != 0 else q + rng.choice([-9, -1, 1, 9])
    else:
        y, m, d = row["date"]
        if rng.random() < 0.5:
            new["date"] = [y, m, d + rng.choice([-3, -2, -1, 1, 2, 3])]
        else:
            new["date"] = [y, m % 12 + 1 if rng.random() < 0.5 else (m - 2) % 12 + 1, d]
    return new


def _item(rng, types):
    used = set()
    a = [_row(rng, used) for _ in range(ROWS)]
    # no two rows with the same product, so a changed product is always visibly different
    while len({r["product"] for r in a}) < ROWS:
        a = [_row(rng, used) for _ in range(ROWS)]
    b = [dict(r) for r in a]
    rows = rng.sample(range(ROWS), len(types))
    for r, f in zip(rows, types):
        b[r] = _alter(rng, a[r], f)
    return {"order": a, "delivery": b, "fields": FIELDS}


def generate(rng, n, save_image):
    items = []
    for k in range(0, n, 2):
        types = FIELDS[:] + ([rng.choice(FIELDS)] if rng.random() < 0.5 else [])
        for _ in range(2):
            items.append(_item(rng, types))
    return items[:n]


def mismatches(item):
    """Oracle: every [row, field] where the two documents differ."""
    out = set()
    for i, (ra, rb) in enumerate(zip(item["order"], item["delivery"])):
        for f in FIELDS:
            if ra[f] != rb[f]:
                out.add((i, f))
    return out


def score(item, response):
    """response: {"marks": [[row, field], ...] (cells of table B marked as mismatching),
    "rt": ms from Start to Done}. hit = every mismatch marked and at most 1 false mark.
    metrics: found / missed mismatches (overall and by field), false marks, time."""
    if not isinstance(item, dict) or "order" not in item:
        return {"hit": False, "errors": 0, "metrics": {}}
    truth = mismatches(item)
    resp = response if isinstance(response, dict) else {}
    marks = set()
    raw = resp.get("marks")
    for m in raw if isinstance(raw, list) else []:
        if (isinstance(m, (list, tuple)) and len(m) == 2 and isinstance(m[0], int) and not isinstance(m[0], bool)
                and 0 <= m[0] < len(item["order"]) and m[1] in FIELDS):
            marks.add((m[0], m[1]))
    found, missed, false = truth & marks, truth - marks, marks - truth
    rt = resp.get("rt") if isinstance(resp.get("rt"), (int, float)) and not isinstance(resp.get("rt"), bool) else None
    responded = isinstance(raw, list)
    return {"hit": responded and not missed and len(false) <= 1, "errors": len(missed) + len(false),
            "metrics": {"mismatches": len(truth), "found": len(found), "missed": len(missed),
                        "false_marks": len(false),
                        "found_by_field": {f: sum(1 for c in found if c[1] == f) for f in FIELDS},
                        "missed_by_field": {f: sum(1 for c in missed if c[1] == f) for f in FIELDS},
                        "mismatch_cells": sorted([list(c) for c in truth]),
                        "time_ms": rt}}


def example_response(item, correct=True):
    truth = sorted(mismatches(item))
    if correct:
        marks = [list(c) for c in truth]
    else:
        marks = [list(c) for c in truth[1:]] + [[r, f] for r in range(len(item["order"])) for f in FIELDS
                                                if (r, f) not in set(truth)][:2]
    return {"marks": marks, "rt": 50000}
