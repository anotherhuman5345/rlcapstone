// Dashboard monitoring: a requestAnimationFrame loop sets each bar from the scripted formula
// (time-based). A press = pointerdown on a gauge, a keyboard click on a focused gauge
// (click with detail 0), or keys 1-4. Every press is logged with ms from start; a brief
// neutral outline acknowledges it (same for right and wrong presses).
// Response: {presses: [{g, t}], frame_gaps}.
TaskViews["dashboard_monitoring"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item;
  const btns = [...ctx.root.querySelectorAll(".gauge")];
  const fills = btns.map((b) => b.querySelector(".fill"));
  const presses = [];
  let running = false, ended = false, t0 = 0, raf = 0, last = 0, frameGaps = 0;

  function value(g, tms) {
    const [base, f1, p1, f2, p2] = it.wobble[g], t = tms / 1000;
    let v = base + 7 * Math.sin(2 * Math.PI * f1 * t + p1) + 3 * Math.sin(2 * Math.PI * f2 * t + p2);
    for (const e of it.events) {
      if (e.g !== g) continue;
      const rel = tms - e.t;
      if (rel < 0 || rel > e.dur) continue;
      const env = Math.min(1, rel / e.ramp, (e.dur - rel) / e.ramp);
      v = (1 - env) * v + env * e.level;
    }
    return Math.max(0, Math.min(100, v));
  }
  function draw(tms) { fills.forEach((f, g) => { f.style.height = value(g, tms).toFixed(1) + "%"; }); }

  function press(g) {
    if (!running || ended) return;
    presses.push({ g, t: Math.round(performance.now() - t0) });
    const b = btns[g];
    b.classList.add("ack");
    setTimeout(() => b.classList.remove("ack"), 200);
  }
  btns.forEach((b, g) => {
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); press(g); });
    b.addEventListener("click", (e) => { if (e.detail === 0) press(g); });
  });
  const onKey = (e) => {
    if (e.repeat) return;
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= btns.length) { e.preventDefault(); press(n - 1); }
  };

  function frame(now) {
    if (ended) return;
    if (now - last > 50) frameGaps += 1;
    last = now;
    const t = now - t0;
    if (t >= it.duration_ms) { end(); return; }
    draw(t);
    raf = requestAnimationFrame(frame);
  }

  draw(0);
  $("#db-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    running = true;
    document.addEventListener("keydown", onKey);
    t0 = last = performance.now();
    raf = requestAnimationFrame(frame);
  }, { once: true });

  function end() {
    if (ended) return;
    ended = true;
    running = false;
    cancelAnimationFrame(raf);
    document.removeEventListener("keydown", onKey);
    ctx.finish({ presses, frame_gaps: frameGaps }, false);
  }
};
