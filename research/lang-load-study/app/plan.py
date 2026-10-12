"""Build each participant's trial list.

Design:
  - Between people: group (high school student, radiologist, ...).
  - Within each person: clue language (L1 = most comfortable, L2 = less).
  - Within each person: task (search scene, scan with planted monkey).

Counterbalancing so that no image is always seen in the same language:
  - Within a task, images are split into two halves. Counterbalance index c
    decides which half gets the L1 clue (c % 2) and which task comes first
    ((c // 2) % 2). Indices are assigned in rotation WITHIN each group, so
    every group is balanced on its own.
  - Trial order inside a block is shuffled with a per-participant seed.
"""
import json
import random

from .config import MANIFEST, TRIALS_PER_TASK


def load_manifest(path=MANIFEST):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_plan(participant_id: str, counterbalance: int, l1: str, l2: str,
               manifest: dict | None = None, n_per_task: int = TRIALS_PER_TASK):
    manifest = manifest or load_manifest()
    rng = random.Random(participant_id)
    lang_swap = counterbalance % 2
    scan_first = (counterbalance // 2) % 2

    blocks = {}
    for task in ("search", "scan"):
        items = [i for i in manifest["images"] if i["task"] == task]
        practice = [i for i in items if i.get("practice")]
        scored = sorted((i for i in items if not i.get("practice")), key=lambda i: i["id"])
        if len(scored) < n_per_task:
            raise ValueError(f"Need {n_per_task} {task} images, found {len(scored)}. Run the stimulus generators.")
        scored = scored[:n_per_task]

        trials = []
        for k, img in enumerate(scored):
            gets_l1 = (k % 2 == 0) != bool(lang_swap)
            lang = l1 if gets_l1 else l2
            trials.append({"task": task, "image_id": img["id"], "clue_lang": lang,
                           "condition": "L1" if gets_l1 else "L2", "practice": False})
        rng.shuffle(trials)
        if practice:
            # Practice is always in the comfortable language and never scored.
            trials.insert(0, {"task": task, "image_id": practice[0]["id"], "clue_lang": l1,
                              "condition": "L1", "practice": True})
        blocks[task] = trials

    order = ("scan", "search") if scan_first else ("search", "scan")
    return blocks[order[0]] + blocks[order[1]]
