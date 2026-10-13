// SART: 45 digits on a fixed schedule anchored to one start time: onset k at
// start + k*1150 ms; digit visible 250 ms, then the mask (circled cross) 900 ms.
// Presses never move the schedule. A press belongs to the digit whose 1150 ms window it
// falls in (windows aligned to onsets); the first gives rt from the recorded onset, later
// ones count as "extra". Only Space and the Press button count; auto-repeat is ignored.
// Response: {events: [{rt, extra, lag}], interruptions, max_lag_ms}, one entry per digit.
TaskViews["sart"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const digitEl = $("#sa-digit"), mask = $("#sa-mask"), btn = $("#sa-press");
  const showMs = ctx.item.show_ms || 250, cycle = showMs + (ctx.item.mask_ms || 900);
  const until = (t) => new Promise((r) => setTimeout(r, Math.max(0, t - performance.now())));
  const vis = (el, on) => el.setAttribute("visibility", on ? "visible" : "hidden");
  const list = ctx.item.digits;
  let interruptions = 0, finished = false, current = -1;
  const onsets = [];
  const events = list.map(() => ({ rt: null, extra: 0, lag: null }));
  const onVis = () => { if (document.hidden) interruptions++; };

  function press() {
    if (current < 0) return;
    const ev = events[current];
    if (ev.rt === null) ev.rt = Math.round(performance.now() - onsets[current]);
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

  $("#sa-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btn.disabled = false;
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    const start = performance.now() + 1000;
    for (let k = 0; k < list.length; k++) {
      const due = start + k * cycle;
      await until(due);
      vis(mask, false);
      digitEl.textContent = String(list[k].digit);
      digitEl.setAttribute("font-size", list[k].size);
      vis(digitEl, true);
      onsets[k] = performance.now();
      events[k].lag = Math.round(onsets[k] - due);
      current = k;
      await until(due + showMs);
      vis(digitEl, false);
      vis(mask, true);
    }
    await until(start + list.length * cycle);
    current = -1;
    vis(mask, false);
    btn.disabled = true;
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    const maxLag = Math.max(0, ...events.map((ev) => ev.lag || 0));
    if (!finished) { finished = true; ctx.finish({ events, interruptions, max_lag_ms: maxLag }, false); }
  }, { once: true });
};
