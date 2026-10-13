// Visual crowding: 16 flashes. Each: 400 ms blank interval, 700 ms fixation cross, then a
// target T with four flanking T's for 150 ms (the cross stays on), then the answer window
// (up to 4000 ms, unspeeded) with the arrow keys or the four buttons. Presses during the
// flash are ignored. The observed flash duration (rAF-to-rAF estimate) is sent per event.
// Response: {events: [{answer, rt, flash_ms}], interruptions} in event order.
TaskViews["crowding"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s) => ctx.root.querySelector(s);
  const flash = $("#cr-flash"), fix = $("#cr-fix");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const geo = ctx.item.geometry, flashMs = ctx.item.flash_ms || 150, limit = ctx.item.limit_ms || 4000;
  const DEG = { up: 0, right: 90, down: 180, left: 270 };
  const KEYS = { ArrowUp: "up", ArrowRight: "right", ArrowDown: "down", ArrowLeft: "left" };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const frame = () => new Promise((r) => requestAnimationFrame(r));
  let interruptions = 0, finished = false, sink = null;
  const onVis = () => { if (document.hidden) interruptions++; };
  btns.forEach((b) => (b.disabled = true));

  function tShape(x, y, orient) {
    const g = document.createElementNS(NS, "g");
    g.setAttribute("transform", `translate(${x} ${y}) rotate(${DEG[orient]})`);
    g.setAttribute("fill", "#1d2731");
    const h = geo.symbol / 2, w = geo.symbol / 5;
    for (const [rx, ry, rw, rh] of [[-h, -h, geo.symbol, w], [-w / 2, -h, w, geo.symbol]]) {
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", rx); r.setAttribute("y", ry); r.setAttribute("width", rw); r.setAttribute("height", rh);
      g.appendChild(r);
    }
    return g;
  }

  const press = (key) => { if (sink) sink(key); };
  const onKey = (e) => {
    if (e.repeat || !KEYS[e.key]) return;
    e.preventDefault();
    press(KEYS[e.key]);
  };
  const onBtn = (e) => { e.preventDefault(); press(e.currentTarget.dataset.key); };
  const onBtnKey = (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    if (!e.repeat) press(e.currentTarget.dataset.key);
  };

  function answer() {
    return new Promise((resolve) => {
      const t0 = performance.now();
      btns.forEach((b) => (b.disabled = false));
      const end = (val) => { clearTimeout(timer); sink = null; btns.forEach((b) => (b.disabled = true)); resolve(val); };
      const timer = setTimeout(() => end({ answer: null, rt: null }), limit);
      sink = (key) => end({ answer: key, rt: Math.round(performance.now() - t0) });
    });
  }

  $("#cr-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    btns.forEach((b) => { b.addEventListener("pointerdown", onBtn); b.addEventListener("keydown", onBtnKey); });
    const out = [];
    for (const ev of ctx.item.events) {
      fix.setAttribute("visibility", "hidden");
      await wait(400);
      fix.setAttribute("visibility", "visible");
      await wait(700);
      const cx = 500 + (ev.side === "left" ? -1 : 1) * geo.ecc[ev.ecc], cy = 200, s = geo.spacing[ev.spacing];
      const spots = [[cx, cy - s], [cx + s, cy], [cx, cy + s], [cx - s, cy]];
      flash.replaceChildren(tShape(cx, cy, ev.target), ...spots.map(([x, y], i) => tShape(x, y, ev.flankers[i])));
      const on = await frame();
      await wait(Math.max(0, flashMs - 8));
      flash.replaceChildren();
      const off = await frame();
      const r = await answer();
      r.flash_ms = Math.round(off - on);
      out.push(r);
    }
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    if (!finished) { finished = true; ctx.finish({ events: out, interruptions }, false); }
  }, { once: true });
};
