"""Temporal-order memory (card 48): a sequence of 6 or 8 short events (phrases such as
"A dog barks") is shown one at a time (2 s each); then the events reappear as numbered
cards in a mixed order and the person taps them in the order they were shown.

Phrases come from text/<lang>.json "events" by index (same index = same event in every
language). The phrases are independent everyday events, so their order cannot be
inferred from meaning. Pairs (k, k+1) share the length (6 for even pairs, 8 for odd
pairs) and use disjoint phrases; the 64-phrase pool is reshuffled when it runs out.
The original order is stored in "events" (study order); "cards" is the shuffled display
order (positions into "events")."""
import json
from pathlib import Path

N_EVENTS = len(json.loads((Path(__file__).parent / "text" / "en.json").read_text(encoding="utf-8"))["events"])


class _Pool:
    def __init__(self, rng):
        self.rng, self.left = rng, []

    def take(self, k):
        if len(self.left) < k:
            self.left = list(range(N_EVENTS))
            self.rng.shuffle(self.left)
        got, self.left = self.left[:k], self.left[k:]
        return got


def generate(rng, n, save_image):
    pool = _Pool(rng)
    items = []
    for k in range(n):
        if k % 2 == 0:
            length = 6 if (k // 2) % 2 == 0 else 8
            block = pool.take(2 * length)
        events = block[(k % 2) * length:(k % 2 + 1) * length]
        cards = list(range(length))
        while cards == sorted(cards) or cards == sorted(cards, reverse=True):
            rng.shuffle(cards)
        items.append({"events": events, "cards": cards})
    return items


def score(item, response):
    """response: {"order": [study position of each card tapped, first to last], "rt": ms}.
    Truth is 0, 1, ..., n-1 (study order). Pairwise accuracy = share of all n(n-1)/2 event
    pairs whose relative order is right (an event left out makes its pairs wrong).
    hit = every event placed AND pairwise-order accuracy >= 0.8.
    errors = events not in their exact position (missing ones included)."""
    n = len(item["events"])
    resp = response if isinstance(response, dict) else {}
    raw = resp.get("order") if isinstance(resp.get("order"), list) else []
    order = []
    for p in raw:
        if isinstance(p, int) and not isinstance(p, bool) and 0 <= p < n and p not in order:
            order.append(p)
    pos = {e: i for i, e in enumerate(order)}
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    right = sum(1 for a, b in pairs if a in pos and b in pos and pos[a] < pos[b])
    pairwise = right / len(pairs)
    exact_pos = sum(1 for e, i in pos.items() if e == i)
    disp = [abs(i - e) for e, i in pos.items()]
    complete = len(order) == n
    rt = resp.get("rt")
    return {"hit": complete and pairwise >= 0.8, "errors": n - exact_pos,
            "metrics": {"length": n, "exact_order": complete and exact_pos == n,
                        "pairwise_accuracy": round(pairwise, 3), "positions_correct": exact_pos,
                        "mean_displacement": round(sum(disp) / len(disp), 3) if disp else None,
                        "placed": len(order),
                        "first_event_first": bool(order) and order[0] == 0,
                        "rt": rt if isinstance(rt, (int, float)) and not isinstance(rt, bool) else None}}


def example_response(item, correct=True):
    n = len(item["events"])
    return {"order": list(range(n)) if correct else list(range(n))[::-1], "rt": 9000}
