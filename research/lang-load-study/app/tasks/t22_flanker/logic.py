"""Flanker (card 22): report the direction of the MIDDLE arrow, ignoring the four
around it. One trial is a short block of 16 displays, half congruent (>>>>>)
and half incongruent (>><>>), in shuffled order. Pairs of items (k, k+1) have the
same structure, so the L1 and L2 versions of a pair are equally hard."""

BLOCK = 16


def generate(rng, n, save_image):
    items = []
    for _ in range(n):
        displays = []
        for c in range(BLOCK):
            mid = rng.choice(["<", ">"])
            congruent = c % 2 == 0
            flank = mid if congruent else {"<": ">", ">": "<"}[mid]
            displays.append({"text": flank * 2 + mid + flank * 2, "answer": "left" if mid == "<" else "right",
                             "congruent": congruent})
        rng.shuffle(displays)
        items.append({"displays": displays})
    return items


def score(item, response):
    """response: [{"key": "left"|"right"|null, "rt": ms}] in display order."""
    resp = response if isinstance(response, list) else []
    rows = []
    for k, d in enumerate(item["displays"]):
        r = resp[k] if k < len(resp) and isinstance(resp[k], dict) else {}
        rows.append((d, r.get("key"), r.get("rt")))
    correct = [d["answer"] == key for d, key, _ in rows]
    acc = sum(correct) / len(rows)

    def mean_rt(cong):
        rts = [rt for (d, key, rt), ok in zip(rows, correct) if ok and d["congruent"] == cong and rt]
        return round(sum(rts) / len(rts), 1) if rts else None

    rt_c, rt_i = mean_rt(True), mean_rt(False)
    return {"hit": acc >= 0.75, "errors": len(rows) - sum(correct),
            "metrics": {"accuracy": round(acc, 3), "rt_congruent": rt_c, "rt_incongruent": rt_i,
                        "flanker_cost_ms": round(rt_i - rt_c, 1) if rt_c and rt_i else None,
                        "omissions": sum(1 for _, key, _ in rows if key is None)}}


def example_response(item, correct=True):
    flip = {"left": "right", "right": "left"}
    return [{"key": d["answer"] if correct else flip[d["answer"]], "rt": 500 + 40 * (not d["congruent"])}
            for d in item["displays"]]
