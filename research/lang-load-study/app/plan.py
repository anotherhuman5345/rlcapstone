"""Build each participant's trial list.

Order (the same for everyone):
  1. Surprise trial, first of all, before anything mentions animals: find a
     small ring on a scan; an unannounced gorilla is also in the image.
  2. One practice trial per task (comfortable language, never scored).
  3. ROUNDS identical rounds. Each round has, per task (search scene, scan,
     dice board, Corsi blocks, reading passage), the same number of L1 and L2
     items (config.ROUND_MIX), shuffled together. Because every
     round has the same mix, a change across rounds can only come from time on
     task (fatigue or practice), not from a change in the task.

Counterbalancing (index c, rotated within each group):
  - c % 2 decides which half of the images gets the L1 clue, so no image is
    always seen in the same language.
  - (c // 2) % 2 decides the surprise clue language, so half of each group
    meets the gorilla with an L1 clue and half with an L2 clue.
  - Which images land in which round is shuffled per participant, so image
    difficulty is not tied to time.
"""
import json
import random

from .config import MANIFEST, ROUND_MIX, ROUNDS


def load_manifest(path=MANIFEST):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_plan(participant_id: str, counterbalance: int, l1: str, l2: str,
               manifest: dict | None = None, mix: dict | None = None, rounds: int = ROUNDS,
               available: set | None = None):
    """available: tasks that can run for this person (reading needs passages in both
    of their languages); tasks outside it are left out of every round."""
    manifest = manifest or load_manifest()
    mix = {t: n for t, n in (mix or ROUND_MIX).items() if available is None or t in available}
    rng = random.Random(participant_id)
    lang_swap = counterbalance % 2
    surprise_l2 = (counterbalance // 2) % 2

    def trial(task, img_id, lang_is_l1, practice=False, rnd=None):
        return {"task": task, "image_id": img_id, "clue_lang": l1 if lang_is_l1 else l2,
                "condition": "L1" if lang_is_l1 else "L2", "practice": practice, "round": rnd}

    images = manifest["images"]
    surprise = next(i for i in images if i["task"] == "surprise")
    plan = [trial("surprise", surprise["id"], not surprise_l2)]

    by_round = [[] for _ in range(rounds)]
    for task, per_round in mix.items():
        if per_round % 2:
            raise ValueError(f"ROUND_MIX for {task} must be even (half L1, half L2).")
        needed = per_round * rounds
        items = [i for i in images if i["task"] == task]
        practice = [i for i in items if i.get("practice")]
        scored = sorted((i for i in items if not i.get("practice")), key=lambda i: i["id"])
        if len(scored) < needed:
            raise ValueError(f"Need {needed} {task} items, found {len(scored)}. "
                             "Run the stimulus generator.")
        if practice:
            plan.append(trial(task, practice[0]["id"], True, practice=True))
        # Pair items (0,1), (2,3), ...: one of each pair gets L1, the other L2.
        scored = scored[:needed]
        pairs = [(scored[k], scored[k + 1]) for k in range(0, needed, 2)]
        rng.shuffle(pairs)
        for r in range(rounds):
            for a, b in pairs[r * per_round // 2:(r + 1) * per_round // 2]:
                by_round[r].append(trial(task, a["id"], not lang_swap, rnd=r + 1))
                by_round[r].append(trial(task, b["id"], bool(lang_swap), rnd=r + 1))
    for r in by_round:
        rng.shuffle(r)
        plan.extend(r)
    return plan
