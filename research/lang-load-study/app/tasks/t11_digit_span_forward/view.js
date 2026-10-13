// Digit span: after Start, a 1 s fixation, then one digit per second (750 ms shown,
// 250 ms blank). The digits are never shown again (Start works once; the keypad and keys
// are dead until the last digit is gone). Then the person types the digits with the
// on-screen keypad or the keyboard (0-9, Backspace, Enter) and presses OK.
// Response: {answer: "0583" (string), rt, first_rt, edits, onsets, interrupted}.
TaskViews["digit_span_forward"] = function (ctx) {
  const ON = 750, SOA = 1000, MAX = 20;
  const R = ctx.root;
  const show = R.querySelector("#ds-show"), recall = R.querySelector("#ds-recall"), entry = R.querySelector("#ds-entry");
  const digitBtns = [...R.querySelectorAll("[data-d]")];
  const del = R.querySelector("#ds-del"), ok = R.querySelector("#ds-ok"), start = R.querySelector("#ds-start");
  const seq = String(ctx.item.digits);
  const onsets = [];
  let phase = "ready", typed = "", t0 = 0, firstRt = null, edits = 0, interrupted = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = (t) => wait(Math.max(0, t - performance.now()));

  function render() {
    entry.textContent = typed;
    const live = phase === "recall";
    digitBtns.forEach((b) => (b.disabled = !live || typed.length >= MAX));
    del.disabled = !live || typed.length === 0;
    ok.disabled = !live || typed.length === 0;
  }
  function press(d) {
    if (phase !== "recall" || typed.length >= MAX) return;
    if (firstRt === null) firstRt = Math.round(performance.now() - t0);
    typed += d;
    render();
  }
  function back() {
    if (phase !== "recall" || !typed) return;
    typed = typed.slice(0, -1);
    edits += 1;
    render();
  }
  function submit() {
    if (phase !== "recall" || !typed) return;
    phase = "done";
    render();
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    ctx.finish({ answer: typed, rt: Math.round(performance.now() - t0), first_rt: firstRt,
                 edits, onsets, interrupted }, false);
  }
  function onKey(e) {
    if (e.repeat || phase !== "recall") return;
    // Enter always means OK; preventDefault stops it from also re-clicking a focused keypad button.
    if (/^[0-9]$/.test(e.key)) { e.preventDefault(); press(e.key); }
    else if (e.key === "Backspace" || e.key === "Delete") { e.preventDefault(); back(); }
    else if (e.key === "Enter") { e.preventDefault(); submit(); }
  }
  function onVis() { if (document.hidden && phase === "encode") interrupted = true; }

  digitBtns.forEach((b) => b.addEventListener("click", () => press(b.dataset.d)));
  del.addEventListener("click", back);
  ok.addEventListener("click", submit);
  document.addEventListener("keydown", onKey);
  document.addEventListener("visibilitychange", onVis);
  render();

  start.addEventListener("click", async () => {
    if (phase !== "ready") return;
    phase = "encode";
    start.hidden = true;
    show.textContent = "+";
    await wait(800);
    show.textContent = "";
    await wait(200);
    const base = performance.now();
    for (let i = 0; i < seq.length; i++) {
      await until(base + i * SOA);
      show.textContent = seq[i];
      onsets.push(Math.round(performance.now() - base));
      await until(base + i * SOA + ON);
      show.textContent = "";
    }
    await until(base + seq.length * SOA);
    phase = "recall";
    recall.hidden = false;
    t0 = performance.now();
    render();
  }, { once: true });
};
