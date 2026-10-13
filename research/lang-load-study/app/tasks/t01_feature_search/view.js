// Feature search: 12 displays. Each: 500 ms fixation, then the circles until a response
// (max item.limit_ms), then 500 ms blank. Click the orange circle (or press → / "present"),
// or press ← / "absent". Responses are sent in display order (see logic.score).
TaskViews["feature_search"] = function (ctx) {
  const it = ctx.item, NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#fs-stage");
  const btns = [...ctx.root.querySelectorAll("[data-choice]")];
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function add(tag, attrs) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    svg.appendChild(e);
    return e;
  }
  function clear() { while (svg.firstChild) svg.removeChild(svg.firstChild); }
  function fixation() {
    clear();
    add("text", { x: it.w / 2, y: it.h / 2 + 12, "text-anchor": "middle", "font-size": 40, fill: "#1D2731" }).textContent = "+";
  }
  function draw(d) {
    clear();
    d.objects.forEach((o, i) => {
      add("circle", { cx: o.x, cy: o.y, r: it.r, fill: o.c });
      // Invisible hitbox (radius item.hit_r) so touch is forgiving; the same radius is documented in logic.py.
      add("circle", { cx: o.x, cy: o.y, r: it.hit_r, fill: "transparent", "data-i": i, style: "cursor:pointer" });
    });
  }
  function toSvg(e) {
    const m = svg.getScreenCTM();
    if (!m) return { x: null, y: null };
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return { x: +(p.x / it.w).toFixed(4), y: +(p.y / it.h).toFixed(4) };
  }

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      let settled = false;
      const done = (choice, obj, via, pt) => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve({ choice, obj, via, x: pt ? pt.x : null, y: pt ? pt.y : null,
                  rt: choice ? Math.round(performance.now() - t0) : null });
      };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("absent", null, "key"); }
        if (e.key === "ArrowRight") { e.preventDefault(); done("present", null, "key"); }
      };
      const onBtn = (e) => done(e.currentTarget.dataset.choice, null, "button");
      const onSvg = (e) => {
        const hit = e.target.closest && e.target.closest("[data-i]");
        if (!hit) return; // clicks on the empty background are ignored
        done("present", Number(hit.getAttribute("data-i")), "pointer", toSvg(e));
      };
      const timer = setTimeout(() => done(null, null, null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        btns.forEach((b) => b.removeEventListener("click", onBtn));
        svg.removeEventListener("pointerdown", onSvg);
      }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
      svg.addEventListener("pointerdown", onSvg);
    });
  }

  ctx.root.querySelector("#fs-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btns.forEach((b) => (b.disabled = false));
    for (const d of it.displays) {
      fixation();
      await wait(500);
      draw(d);
      out.push(await answer(it.limit_ms));
      clear();
      await wait(500);
    }
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
