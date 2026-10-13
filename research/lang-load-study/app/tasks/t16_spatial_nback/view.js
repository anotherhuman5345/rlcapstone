// Spatial n-back: after Start, a 1 s fixation, then one lit grid cell every 2000 ms
// (500 ms lit, 1500 ms dark). The stream is fixed-pace and cannot be restarted (Start works once).
// For each location the first answer inside its 2000 ms window counts: Left arrow / button =
// "Different" (nonmatch), Right arrow / button = "Same" (match). Later presses are ignored.
// Response: {responses: [{key, rt}] one per location (rt from onset), onsets, interrupted}.
TaskViews["spatial_nback"] = function (ctx) {
  const ON = 500, SOA = 2000;
  const R = ctx.root;
  const cells = [...R.querySelectorAll(".snb-cell")];
  const fix = R.querySelector("#snb-fix");
  const btns = [...R.querySelectorAll("[data-key]")];
  const start = R.querySelector("#snb-start");
  const locs = ctx.item.cells.map(Number);
  const out = locs.map(() => ({ key: null, rt: null }));
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
    fix.textContent = "+";
    await wait(1000);
    fix.textContent = "";
    const base = performance.now();
    for (let i = 0; i < locs.length; i++) {
      await until(base + i * SOA);
      cur = i;
      onset = performance.now();
      cells[locs[i]].classList.add("lit");
      onsets.push(Math.round(onset - base));
      await until(base + i * SOA + ON);
      cells[locs[i]].classList.remove("lit");
    }
    await until(base + locs.length * SOA);
    phase = "done";
    btns.forEach((b) => (b.disabled = true));
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    ctx.finish({ responses: out, onsets, interrupted }, false);
  }, { once: true });
};
