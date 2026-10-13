// Backward spatial span: after Start, a 600 ms pause, then the squares in item.sequence
// light up one by one (500 ms lit, 500 ms gap). The squares stay disabled (and clicks are
// ignored) until the sequence is over; Start works once, so the sequence cannot be replayed.
// Then the person clicks/taps the squares in reverse order (keyboard: Tab + Enter/Space).
// The trial ends after as many clicks as squares were lit.
// Response: {clicks: [index...], click_rts: [ms], rt, interrupted}.
TaskViews["spatial_span_backward"] = function (ctx) {
  const ON = 500, SOA = 1000;
  const R = ctx.root;
  const blocks = [...R.querySelectorAll(".corsi-block")];
  const start = R.querySelector("#ss-start");
  const seq = ctx.item.sequence.map(Number);
  const clicks = [], clickRts = [];
  let phase = "ready", t0 = 0, interrupted = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = (t) => wait(Math.max(0, t - performance.now()));
  const onVis = () => { if (document.hidden && phase === "encode") interrupted = true; };
  document.addEventListener("visibilitychange", onVis);

  blocks.forEach((b) => b.addEventListener("click", () => {
    if (phase !== "recall") return;
    clicks.push(Number(b.dataset.i));
    clickRts.push(Math.round(performance.now() - t0));
    b.classList.add("picked");
    setTimeout(() => b.classList.remove("picked"), 180);
    if (clicks.length === seq.length) {
      phase = "done";
      blocks.forEach((x) => (x.disabled = true));
      document.removeEventListener("visibilitychange", onVis);
      ctx.status("");
      ctx.finish({ clicks, click_rts: clickRts, rt: clickRts[clickRts.length - 1], interrupted }, false);
    }
  }));

  start.addEventListener("click", async () => {
    if (phase !== "ready") return;
    phase = "encode";
    start.hidden = true;
    await wait(600);
    const base = performance.now();
    for (let i = 0; i < seq.length; i++) {
      await until(base + i * SOA);
      blocks[seq[i]].classList.add("lit");
      await until(base + i * SOA + ON);
      blocks[seq[i]].classList.remove("lit");
    }
    await until(base + seq.length * SOA);
    phase = "recall";
    blocks.forEach((b) => (b.disabled = false));
    ctx.status(ctx.text.go);
    t0 = performance.now();
  }, { once: true });
};
