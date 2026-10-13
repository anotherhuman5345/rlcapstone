// Go/no-go: 40 shapes on a fixed schedule anchored to one start time: onset k at
// start + k*1000 ms, shape visible 500 ms, then a fixation cross. Presses never move
// the schedule. A press belongs to the shape whose 1000 ms window it falls in; the first
// press gives rt (from the recorded onset), later ones count as "extra". Only Space and
// the Press button count; auto-repeat is ignored.
// Response: {events: [{rt, extra, lag}], interruptions, max_lag_ms}, one entry per shape.
TaskViews["go_nogo"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const fix = $("#gn-fix"), btn = $("#gn-press");
  const shapes = { circle: $("#gn-circle"), triangle: $("#gn-triangle") };
  const cycle = ctx.item.cycle_ms || 1000, showMs = ctx.item.show_ms || 500;
  const until = (t) => new Promise((r) => setTimeout(r, Math.max(0, t - performance.now())));
  const vis = (el, on) => el.setAttribute("visibility", on ? "visible" : "hidden");
  let interruptions = 0, finished = false, current = -1, onsets = [];
  const events = ctx.item.shapes.map(() => ({ rt: null, extra: 0, lag: null }));
  const onVis = () => { if (document.hidden) interruptions++; };

  function press() {
    if (current < 0) return;
    const now = performance.now(), ev = events[current];
    if (ev.rt === null) ev.rt = Math.round(now - onsets[current]);
    else ev.extra++;
  }
  const onKey = (e) => {
    if (e.key !== " ") return;
    e.preventDefault();
    if (!e.repeat) press();
  };
  btn.addEventListener("pointerdown", (e) => { e.preventDefault(); press(); });
  btn.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault(); e.stopPropagation();
    if (!e.repeat) press();
  });

  $("#gn-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btn.disabled = false;
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    const start = performance.now() + 1000;
    for (let k = 0; k < ctx.item.shapes.length; k++) {
      const due = start + k * cycle;
      await until(due);
      vis(fix, false);
      vis(shapes[ctx.item.shapes[k]], true);
      onsets[k] = performance.now();
      events[k].lag = Math.round(onsets[k] - due);
      current = k;
      await until(due + showMs);
      vis(shapes[ctx.item.shapes[k]], false);
      vis(fix, true);
    }
    await until(start + ctx.item.shapes.length * cycle);
    current = -1;
    btn.disabled = true;
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    const maxLag = Math.max(0, ...events.map((ev) => ev.lag || 0));
    if (!finished) { finished = true; ctx.finish({ events, interruptions, max_lag_ms: maxLag }, false); }
  }, { once: true });
};
