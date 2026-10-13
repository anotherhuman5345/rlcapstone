// Mental rotation: 8 displays. Each shows a fixation cross for 400 ms, then two shapes
// until the answer (at most 7 s). Left arrow / "Same" button, right arrow / "Mirror" button.
// Responses are sent in display order: [{key: "same"|"mirror"|null, rt}].
TaskViews["mental_rotation"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#mr-stage");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const out = [];
  const CELL = 34;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function clear() { while (svg.firstChild) svg.removeChild(svg.firstChild); }
  function fixation() {
    clear();
    el("path", { d: "M310 150h20M320 140v20", stroke: "#1D2731", "stroke-width": 3 }, svg);
  }
  function shape(cells, cx, cy, rot) {
    const mx = cells.reduce((s, p) => s + p[0] + 0.5, 0) / cells.length;
    const my = cells.reduce((s, p) => s + p[1] + 0.5, 0) / cells.length;
    const g = el("g", { transform: `translate(${cx} ${cy}) rotate(${rot})` }, svg);
    for (const [x, y] of cells) {
      el("rect", { x: (x - mx) * CELL, y: (y - my) * CELL, width: CELL, height: CELL,
                   fill: "#4A6A86", stroke: "#1D2731", "stroke-width": 2 }, g);
    }
  }
  function show(d) {
    clear();
    el("line", { x1: 320, y1: 30, x2: 320, y2: 270, stroke: "#C7D0D8", "stroke-width": 2 }, svg);
    shape(d.left, 160, 150, d.rot_left);
    shape(d.right, 480, 150, d.rot_right);
  }

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ key, rt: key ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("same"); }
        else if (e.key === "ArrowRight") { e.preventDefault(); done("mirror"); }
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

  ctx.root.querySelector("#mr-start").addEventListener("click", async (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    btns.forEach((b) => (b.disabled = false));
    for (const d of ctx.item.displays) {
      fixation();
      await wait(400);
      show(d);
      out.push(await answer(7000));
    }
    clear();
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
