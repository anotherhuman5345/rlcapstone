"""Tone detection during learning (card 61), adapted to one short trial.

Main task: study 6 symbol-word pairs (5 s each, 30 s in all), then for each symbol pick
its word from the 6 studied words. Secondary task: during study, 5 short beeps
(1000 Hz, 150 ms) play on a fixed scripted schedule (Web Audio, scheduled ahead);
press Space or the Tone button as soon as a beep is heard.

Words come from text/<lang>.json "words" by index, so both languages show equivalent
material. Pairs (k, k+1) share the same tone gaps (in a different order) and have the
same structure; their words and symbols differ.
"""
from app.tasks import _guard as G

TIMING = "window"
N_ASSOC = 6
STUDY_MS = 5000
N_TONES = 5
N_WORDS = 48          # length of the "words" list in text/*.json
N_SYMBOLS = 24        # 8 shapes x 3 colours, drawn in view.js
TONE_MIN_RT, TONE_MAX_RT = 150, 2000   # a press in this window after onset detects the tone
WINDOW_MS = TONE_MAX_RT                # the tone response window (see TONE_MIN_RT/TONE_MAX_RT)
LIMIT_MS = 140000     # item limit_ms: view.js ends the recall test at p0 + it.limit_ms
TIME_SLACK_MS = 1000  # timer tolerance at the end of study / at the limit
MAX_PRESSES = 500
CEILING_MS = G.trial_ceiling(__file__)


def _item(rng, gaps, words, symbols):
    times, t = [], 0
    for g in gaps:
        t += g
        times.append(t)
    return {"pairs": [{"symbol": s, "word": w} for s, w in zip(symbols, words)],
            "study_ms": STUDY_MS, "limit_ms": LIMIT_MS, "tones_ms": times, "tone_hz": 1000, "tone_len_ms": 150,
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


def _presses(a, raw, study_end):
    """Valid press times (ms from study start): finite, >= 0, <= the ceiling and inside the
    study phase (the browser records presses only while studying). Bad entries are flagged
    and dropped; presses that go backwards or repeat exactly are flagged."""
    seq = a.stream(raw, "presses", cap=MAX_PRESSES)
    out, order = [], []
    for v in seq:
        st, t = a.time(v, field="presses", window=study_end, slack=TIME_SLACK_MS, floor=0, required=True)
        if st == G.TIMELY:
            out.append(t)
            order.append(t)
        elif st == G.LATE:
            a.malformed("press_after_study")
            order.append(t)
        else:
            order.append(None)
    a.monotonic(order, "presses")
    vals = [t for t in order if t is not None]
    if len(set(vals)) < len(vals):
        a.malformed("duplicate_presses")
    return sorted(set(out))


@G.safe
def score(item, response):
    """response: {"presses": [ms from study start, ...], "answers": [word index, one per
    answered test position, in item["test_order"] order], "test_rts": [ms from that
    symbol's onset, one per answer], "audio_ok": bool, "audio_latency_ms": ms (optional)}.
    Presses must be finite, >= 0, increasing and inside the 30 s study phase; malformed,
    duplicate or out-of-order presses are flagged (bad ones are not used).
    A tone is detected by the first unused valid press 150-2000 ms after its onset; other
    valid presses are false alarms. Recall: answers[k] must equal the word paired with
    symbol test_order[k] AND have a valid timely test_rts[k] (>= 100 ms, and the test still
    running: study + all answer times inside item limit_ms); an answer without a valid time
    never counts. Fewer answers than positions = the test timed out (missing ones are wrong).
    hit = at least 4 of 6 pairs recalled AND at least 3 of 5 tones detected
    (both parts of the dual task done reasonably)."""
    a = G.Audit(CEILING_MS)
    if not isinstance(response, dict):
        return a.junk(N_ASSOC + N_TONES)
    study_end = len(item["pairs"]) * item["study_ms"]
    limit = item.get("limit_ms", LIMIT_MS)
    presses = _presses(a, response.get("presses", G.MISSING), study_end)

    used, tone_rts = set(), []
    for onset in item["tones_ms"]:
        rt = None
        for k, p in enumerate(presses):
            if k not in used and onset + TONE_MIN_RT <= p <= onset + TONE_MAX_RT:
                used.add(k)
                rt = p - onset
                break
        a.record(G.TIMELY if rt is not None else G.ABSENT)
        tone_rts.append(rt)
    hits = sum(r is not None for r in tone_rts)
    fas = len(presses) - len(used)

    answers = a.stream(response.get("answers", G.MISSING), "answers", cap=N_ASSOC)
    rts = a.stream(response.get("test_rts", G.MISSING), "test_rts", cap=N_ASSOC)
    if len(rts) != len(answers):
        a.malformed("test_rts_answers_mismatch")
    options = set(item["options"])
    recall, ok_rts, elapsed = [], [], study_end
    for k, idx in enumerate(item["test_order"]):
        if k >= len(answers):
            recall.append(False)
            continue
        ans = a.choice(answers[k], options, "answer")
        if ans is None:
            a.malformed("missing_answer")
        st, rt = a.time(rts[k] if k < len(rts) else G.MISSING, field="test_rts",
                        window=limit - study_end, slack=TIME_SLACK_MS, required=True)
        if rt is not None:
            elapsed += rt
            if elapsed > limit + TIME_SLACK_MS and st == G.TIMELY:
                a.malformed("answer_after_limit")
                st = G.LATE
        ok = st == G.TIMELY and ans is not None and ans is not G.BAD and ans == item["pairs"][idx]["word"]
        recall.append(ok)
        if ok:
            ok_rts.append(rt)
    n_recall = sum(recall)
    det = [r for r in tone_rts if r is not None]
    latency = response.get("audio_latency_ms")
    if latency is not None and not (G.is_num(latency) and 0 <= latency <= 10000):
        a.malformed("invalid_audio_latency_ms")
        latency = None
    return a.finish(n_recall >= 4 and hits >= 3, (N_ASSOC - n_recall) + (N_TONES - hits) + fas, {
        "recall_correct": n_recall, "recall_accuracy": round(n_recall / N_ASSOC, 3),
        "recall_answered": min(len(answers), N_ASSOC),
        "recall_rt_mean": G.mean(ok_rts), "recall_rt_median": G.median(ok_rts),
        "tone_hits": hits, "tone_omissions": N_TONES - hits, "tone_false_alarms": fas,
        "tone_rt_mean": G.mean(det), "tone_rt_median": G.median(det),
        "tone_rts": tone_rts, "audio_ok": a.opt_bool(response, "audio_ok") is True,
        "audio_latency_ms": latency})


def example_response(item, correct=True):
    if correct:
        presses = [t + 450 for t in item["tones_ms"]]
        answers = [item["pairs"][i]["word"] for i in item["test_order"]]
    else:
        presses = []
        answers = [item["pairs"][(i + 1) % N_ASSOC]["word"] for i in item["test_order"]]
    return {"presses": presses, "answers": answers, "test_rts": [1500] * N_ASSOC, "audio_ok": True}
