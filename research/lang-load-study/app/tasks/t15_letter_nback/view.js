// Letter n-back: after Start, a 1 s fixation, then one letter every 2000 ms (500 ms shown,
// 1500 ms blank). The stream is fixed-pace and cannot be restarted (Start works once).
// For each letter the first answer inside its 2000 ms window counts: Left arrow / button =
// "Different" (nonmatch), Right arrow / button = "Same" (match). Later presses are ignored.
// Response: {responses: [{key, rt}] one per letter (rt from letter onset), onsets, interrupted}.
TaskViews["letter_nback"] = function (ctx) {
  const ON = 500, SOA = 2000;
  const R = ctx.root;
  const show = R.querySelector("#lnb-show");
  const btns = [...R.querySelectorAll("[data-key]")];
  const start = R.querySelector("#lnb-start");
  const letters = ctx.item.letters.map(String);
  const out = letters.map(() => ({ key: null, rt: null }));
  const onsets = [];
  let phase = "ready", cur = -1, onset = 0, interrupted = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = (t) => wait(Math.max(0, t - performance.now()));
  btns.forEach((b) => (b.disabled = true));

  function respond(key) {
    if (phase !== "run" || cur < 0 || out[cur].key !== null) return;
    out[cur] = { key, rt: Math.round(performance.now() - onset) };
    const b = btns.find((x) => x.dataset.key === key);
    b.classList.add("pressed");
    setTimeout(() => b.classList.remove("pressed"), 150);
  }
  function onKey(e) {
    if (e.repeat || phase !== "run") return;
    if (e.key === "ArrowLeft") { e.preventDefault(); respond("nonmatch"); }
    else if (e.key === "ArrowRight") { e.preventDefault(); respond("match"); }
  }
  const onVis = () => { if (document.hidden && phase === "run") interrupted = true; };
  btns.forEach((b) => b.addEventListener("click", () => respond(b.dataset.key)));
  document.addEventListener("keydown", onKey);
  document.addEventListener("visibilitychange", onVis);

  start.addEventListener("click", async () => {
    if (phase !== "ready") return;
    phase = "run";
    start.hidden = true;
    btns.forEach((b) => (b.disabled = false));
    show.textContent = "+";
    await wait(1000);
    show.textContent = "";
    const base = performance.now();
    for (let i = 0; i < letters.length; i++) {
      await until(base + i * SOA);
      cur = i;
      onset = performance.now();
      show.textContent = letters[i];
      onsets.push(Math.round(onset - base));
      await until(base + i * SOA + ON);
      show.textContent = "";
    }
    await until(base + letters.length * SOA);
    phase = "done";
    btns.forEach((b) => (b.disabled = true));
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    ctx.finish({ responses: out, onsets, interrupted }, false);
  }, { once: true });
};
