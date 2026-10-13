// Change detection: 12 events. Each: 500 ms fixation, study array item.study_ms, blank
// item.blank_ms (timed with requestAnimationFrame), then the test array until a response
// (max item.limit_ms), then 500 ms blank. ← / "Same", → / "Different".
// Response per event: {key: "same"|"different"|null, rt, study_ms_observed}.
TaskViews["change_detection"] = function (ctx) {
  const it = ctx.item, NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#cd-stage");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function clear() { while (svg.firstChild) svg.removeChild(svg.firstChild); }
  function add(tag, attrs) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    svg.appendChild(e);
    return e;
  }
  function fixation() {
    clear();
    add("text", { x: it.w / 2, y: it.h / 2 + 12, "text-anchor": "middle", "font-size": 40, fill: "#1D2731" }).textContent = "+";
  }
  function draw(arr) {
    clear();
    const s = it.size;
    arr.forEach((o) => add("rect", { x: o.x - s / 2, y: o.y - s / 2, width: s, height: s, fill: o.c, stroke: "#1D2731", "stroke-width": 1 }));
  }
  // Show something, then resolve after `ms` measured from the first frame it was painted in.
  function frameShow(drawFn, ms) {
    return new Promise((resolve) => {
      requestAnimationFrame((t0) => {
        drawFn();
        const tick = (now) => { if (now - t0 >= ms - 8) resolve(now - t0); else requestAnimationFrame(tick); };
        requestAnimationFrame(tick);
      });
    });
  }

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      let settled = false;
      const done = (key) => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve({ key, rt: key ? Math.round(performance.now() - t0) : null });
      };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("same"); }
        if (e.key === "ArrowRight") { e.preventDefault(); done("different"); }
      };
      const onBtn = (e) => done(e.currentTarget.dataset.key);
      const timer = setTimeout(() => done(null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        btns.forEach((b) => b.removeEventListener("click", onBtn));
      }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  ctx.root.querySelector("#cd-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    for (const ev of it.events) {
      fixation();
      await wait(500);
      const shown = await frameShow(() => draw(ev.study), it.study_ms);
      await frameShow(clear, it.blank_ms);
      draw(ev.test);
      btns.forEach((b) => (b.disabled = false));
      const r = await answer(it.limit_ms);
      btns.forEach((b) => (b.disabled = true));
      r.study_ms_observed = Math.round(shown);
      out.push(r);
      clear();
      await wait(500);
    }
    ctx.finish(out, false);
  }, { once: true });
};
