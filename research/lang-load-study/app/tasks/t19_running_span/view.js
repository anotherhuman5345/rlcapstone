// Running span: k is shown before Start. After Start, a 1 s fixation, then one letter per
// second (750 ms shown, 250 ms blank) until the stream stops without warning (no counter,
// no progress cue). Start works once and the letters are never shown again; the keypad and
// keys are dead while the stream plays. Then the person fills k slots with the on-screen
// keypad or the keyboard (letters, "?" for a forgotten letter, Backspace, Enter) and presses OK.
// Response: {answer: "KMT" (k chars), rt, first_rt, edits, onsets, interrupted}.
TaskViews["running_span"] = function (ctx) {
  const ON = 750, SOA = 1000;
  const R = ctx.root;
  const show = R.querySelector("#rs-show"), recall = R.querySelector("#rs-recall");
  const slots = [...R.querySelectorAll(".rs-slot")];
  const keyBtns = [...R.querySelectorAll("[data-c]")];
  const del = R.querySelector("#rs-del"), ok = R.querySelector("#rs-ok"), start = R.querySelector("#rs-start");
  const stream = String(ctx.item.letters);
  const k = Number(ctx.item.k);
  const allowed = new Set(keyBtns.map((b) => b.dataset.c));
  const onsets = [];
  let phase = "ready", typed = "", t0 = 0, firstRt = null, edits = 0, interrupted = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = (t) => wait(Math.max(0, t - performance.now()));

  function render() {
    slots.forEach((s, i) => { s.textContent = typed[i] || ""; s.classList.toggle("next", i === typed.length); });
    const live = phase === "recall";
    keyBtns.forEach((b) => (b.disabled = !live || typed.length >= k));
    del.disabled = !live || typed.length === 0;
    ok.disabled = !live || typed.length !== k;
  }
  function press(c) {
    if (phase !== "recall" || typed.length >= k || !allowed.has(c)) return;
    if (firstRt === null) firstRt = Math.round(performance.now() - t0);
    typed += c;
    render();
  }
  function back() {
    if (phase !== "recall" || !typed) return;
    typed = typed.slice(0, -1);
    edits += 1;
    render();
  }
  function submit() {
    if (phase !== "recall" || typed.length !== k) return;
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
    // toUpperCase is locale-independent: Turkish "i"/"ı" become "I", which is not a choice.
    const c = e.key.length === 1 ? e.key.toUpperCase() : "";
    if (allowed.has(c)) { e.preventDefault(); press(c); }
    else if (e.key === "Backspace" || e.key === "Delete") { e.preventDefault(); back(); }
    else if (e.key === "Enter") { e.preventDefault(); submit(); }
  }
  function onVis() { if (document.hidden && phase === "encode") interrupted = true; }

  keyBtns.forEach((b) => b.addEventListener("click", () => press(b.dataset.c)));
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
    for (let i = 0; i < stream.length; i++) {
      await until(base + i * SOA);
      show.textContent = stream[i];
      onsets.push(Math.round(performance.now() - base));
      await until(base + i * SOA + ON);
      show.textContent = "";
    }
    await until(base + stream.length * SOA);
    phase = "recall";
    recall.hidden = false;
    t0 = performance.now();
    render();
  }, { once: true });
};
