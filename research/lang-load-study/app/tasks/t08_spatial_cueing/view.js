// Spatial cueing: 20 events. Each: 300 ms blank interval, 500 ms fixation cross, arrow cue,
// then after the cue-target interval (200 ms) a dot in the left or right box, which stays up
// to 1500 ms or until the first left/right answer. The cue stays visible with the target.
// Presses before target onset are counted as "early" and do not answer the event.
// Response: {events: [{key, rt, early}], interruptions} in event order.
TaskViews["spatial_cueing"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const fix = $("#sc-fix"), cue = $("#sc-cue"), target = $("#sc-target");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const cti = ctx.item.cti_ms || 200, limit = ctx.item.limit_ms || 1500;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const show = (el, on) => el.setAttribute("visibility", on ? "visible" : "hidden");
  let interruptions = 0, finished = false;
  const onVis = () => { if (document.hidden) interruptions++; };
  btns.forEach((b) => (b.disabled = true));

  // One input handler for the whole block; `sink` decides what a press means right now.
  let sink = null;
  const press = (key) => { if (sink) sink(key); };
  const onKey = (e) => {
    if (e.repeat) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); press("left"); }
    else if (e.key === "ArrowRight") { e.preventDefault(); press("right"); }
  };
  const onBtn = (e) => { e.preventDefault(); press(e.currentTarget.dataset.key); };

  function answer() {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const timer = setTimeout(() => { sink = null; resolve({ key: null, rt: null }); }, limit);
      sink = (key) => { clearTimeout(timer); sink = null; resolve({ key, rt: Math.round(performance.now() - t0) }); };
    });
  }

  $("#sc-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    btns.forEach((b) => { b.disabled = false; b.addEventListener("pointerdown", onBtn); b.addEventListener("keydown", (k) => { if (k.key === "Enter" || k.key === " ") { k.preventDefault(); if (!k.repeat) press(b.dataset.key); } }); });
    const out = [];
    for (const ev of ctx.item.events) {
      show(fix, false); show(cue, false); show(target, false);
      await wait(300);
      let early = 0;
      sink = () => { early++; };
      show(fix, true);
      await wait(500);
      show(fix, false);
      cue.setAttribute("transform", ev.cue === "left" ? "rotate(180 450 150)" : "");
      show(cue, true);
      await wait(cti);
      target.setAttribute("cx", ev.target === "left" ? 150 : 750);
      show(target, true);
      const r = await answer();
      r.early = early;
      out.push(r);
    }
    sink = null;
    show(cue, false); show(target, false); show(fix, true);
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    btns.forEach((b) => (b.disabled = true));
    if (!finished) { finished = true; ctx.finish({ events: out, interruptions }, false); }
  }, { once: true });
};
