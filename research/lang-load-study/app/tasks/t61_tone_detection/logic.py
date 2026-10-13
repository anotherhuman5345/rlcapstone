"""Tone detection during learning (card 61), adapted to one short trial.

Main task: study 6 symbol-word pairs (5 s each, 30 s in all), then for each symbol pick
its word from the 6 studied words. Secondary task: during study, 5 short beeps
(1000 Hz, 150 ms) play on a fixed scripted schedule (Web Audio, scheduled ahead);
press Space or the Tone button as soon as a beep is heard.

Words come from text/<lang>.json "words" by index, so both languages show equivalent
material. Pairs (k, k+1) share the same tone gaps (in a different order) and have the
same structure; their words and symbols differ.
"""

N_ASSOC = 6
STUDY_MS = 5000
N_TONES = 5
N_WORDS = 48          # length of the "words" list in text/*.json
N_SYMBOLS = 24        # 8 shapes x 3 colours, drawn in view.js
TONE_MIN_RT, TONE_MAX_RT = 150, 2000   # a press in this window after onset detects the tone


def _item(rng, gaps, words, symbols):
    times, t = [], 0
    for g in gaps:
        t += g
        times.append(t)
    return {"pairs": [{"symbol": s, "word": w} for s, w in zip(symbols, words)],
            "study_ms": STUDY_MS, "limit_ms": 140000, "tones_ms": times, "tone_hz": 1000, "tone_len_ms": 150,
            "test_order": rng.sample(range(N_ASSOC), N_ASSOC),
            "options": rng.sample(words, N_ASSOC)}


def generate(rng, n, save_image):
    items = []
    while len(items) < n:
        # 5 gaps of 3.5-5.5 s: the last tone is at most 27.5 s, so its response window ends
        # before the 30 s study phase does.
        gaps = [rng.randint(35, 55) * 100 for _ in range(N_TONES)]
        words = rng.sample(range(N_WORDS), 2 * N_ASSOC)
        symbols = rng.sample(range(N_SYMBOLS), 2 * N_ASSOC)
        for m in range(2):
            g = gaps[:] if m == 0 else rng.sample(gaps, len(gaps))
            items.append(_item(rng, g, words[m * N_ASSOC:(m + 1) * N_ASSOC],
                               symbols[m * N_ASSOC:(m + 1) * N_ASSOC]))
    return items[:n]


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def score(item, response):
    """response: {"presses": [ms from study start, ...], "answers": [word index or null,
    one per test position, in item["test_order"] order], "test_rts": [ms, ...],
    "audio_ok": bool}.
    A tone is detected by the first unused press 150-2000 ms after its onset; other
    presses are false alarms. Recall: answers[k] must equal the word paired with symbol
    test_order[k].
    hit = at least 4 of 6 pairs recalled AND at least 3 of 5 tones detected
    (both parts of the dual task done reasonably)."""
    miss = {"hit": False, "errors": N_ASSOC + N_TONES, "metrics": {}}
    if not isinstance(response, dict):
        return miss
    raw = response.get("presses")
    presses = sorted(p for p in map(_num, raw) if p is not None) if isinstance(raw, list) else []
    answers = response.get("answers") if isinstance(response.get("answers"), list) else []
    rts = response.get("test_rts") if isinstance(response.get("test_rts"), list) else []

    used, tone_rts = set(), []
    for onset in item["tones_ms"]:
        rt = None
        for k, p in enumerate(presses):
            if k not in used and onset + TONE_MIN_RT <= p <= onset + TONE_MAX_RT:
                used.add(k)
                rt = p - onset
                break
        tone_rts.append(rt)
    hits = sum(r is not None for r in tone_rts)
    fas = len(presses) - len(used)

    recall = []
    for k, idx in enumerate(item["test_order"]):
        a = answers[k] if k < len(answers) else None
        recall.append(a == item["pairs"][idx]["word"] and not isinstance(a, bool))
    n_recall = sum(recall)
    ok_rts = [_num(rts[k]) for k in range(min(len(rts), N_ASSOC)) if recall[k] and _num(rts[k])]
    det = [r for r in tone_rts if r is not None]
    return {"hit": n_recall >= 4 and hits >= 3,
            "errors": (N_ASSOC - n_recall) + (N_TONES - hits) + fas,
            "metrics": {"recall_correct": n_recall, "recall_accuracy": round(n_recall / N_ASSOC, 3),
                        "recall_rt_mean": round(sum(ok_rts) / len(ok_rts), 1) if ok_rts else None,
                        "tone_hits": hits, "tone_omissions": N_TONES - hits, "tone_false_alarms": fas,
                        "tone_rt_mean": round(sum(det) / len(det), 1) if det else None,
                        "tone_rts": tone_rts, "audio_ok": response.get("audio_ok") is True}}


def example_response(item, correct=True):
    if correct:
        presses = [t + 450 for t in item["tones_ms"]]
        answers = [item["pairs"][i]["word"] for i in item["test_order"]]
    else:
        presses = []
        answers = [item["pairs"][(i + 1) % N_ASSOC]["word"] for i in item["test_order"]]
    return {"presses": presses, "answers": answers, "test_rts": [1500] * N_ASSOC, "audio_ok": True}
