// Cube-net matching: after Start, shows the cube (three faces, drawn from its corner) and
// four nets. Pick a net by click/tap or digit keys 1-4. Response: {choice: 0-3 | null, rt}.
// Marks are drawn in a unit square (x right, y down, "up" = towards y = 0); logic.py's
// "up" vector says where that top edge points on the cube.
TaskViews["cube_nets"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const item = ctx.item;
  const cubeSvg = ctx.root.querySelector("#cn-cube");
  const opts = ctx.root.querySelector("#cn-opts");
  const body = ctx.root.querySelector("#cn-body");
  let t0 = 0, done = false, timer = null;
  const COLORS = ["#C0392B", "#1F6E8C", "#2E8B57", "#8E44AD", "#D68910", "#34495E"];

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  // Six original marks, none looks the same after a quarter turn.
  function mark(g, id) {
    const fill = COLORS[id % COLORS.length];
    const poly = (pts) => el("polygon", { points: pts.map((p) => p.join(",")).join(" "), fill }, g);
    if (id === 0) poly([[0.5, 0.12], [0.82, 0.48], [0.62, 0.48], [0.62, 0.86], [0.38, 0.86], [0.38, 0.48], [0.18, 0.48]]);
    else if (id === 1) { el("circle", { cx: 0.28, cy: 0.28, r: 0.15, fill }, g); }
    else if (id === 2) { poly([[0.18, 0.16], [0.82, 0.16], [0.82, 0.34], [0.59, 0.34], [0.59, 0.84], [0.41, 0.84], [0.41, 0.34], [0.18, 0.34]]); }
    else if (id === 3) poly([[0.12, 0.12], [0.88, 0.12], [0.88, 0.48], [0.12, 0.48]]);
    else if (id === 4) { poly([[0.24, 0.12], [0.36, 0.12], [0.36, 0.88], [0.24, 0.88]]); poly([[0.36, 0.12], [0.82, 0.28], [0.36, 0.44]]); }
    else poly([[0.2, 0.14], [0.38, 0.14], [0.38, 0.66], [0.82, 0.66], [0.82, 0.86], [0.2, 0.86]]);
  }
  function face(g) {
    el("rect", { x: 0, y: 0, width: 1, height: 1, fill: "#FFFFFF", stroke: "#1D2731", "stroke-width": 2, "vector-effect": "non-scaling-stroke" }, g);
  }

  // Corner view from (1,-1,1): screen x = v·R, screen y = -(v·U).
  const R = [1 / Math.SQRT2, 1 / Math.SQRT2, 0];
  const U = [-1 / Math.sqrt(6), 1 / Math.sqrt(6), 2 / Math.sqrt(6)];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const proj = (v, s) => [dot(v, R) * s, -dot(v, U) * s];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  function drawCube() {
    const s = 120;
    for (const [n, id, up] of item.view) {
      const right = cross(up, n);
      const down = up.map((x) => -x);
      const origin = [0, 1, 2].map((i) => 0.5 * n[i] - 0.5 * right[i] + 0.5 * up[i]);
      const [a, b] = proj(right, s), [c, d] = proj(down, s), [e, f] = proj(origin, s);
      const g = el("g", { transform: `matrix(${a} ${b} ${c} ${d} ${e} ${f})` }, cubeSvg);
      face(g);
      mark(g, id);
    }
  }

  function drawOptions() {
    const CELL = 34;
    item.options.forEach((net, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cn-opt";
      const cols = Math.max(...net.map((c) => c[0])) + 1, rows = Math.max(...net.map((c) => c[1])) + 1;
      const w = 5 * CELL + 12, h = w; // fits 4x3, 3x4, 5x2 and 2x5 nets
      const ox = (w - cols * CELL) / 2, oy = (h - rows * CELL) / 2;
      const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" }, b);
      for (const [col, row, id, r] of net) {
        const g = el("g", { transform: `translate(${ox + col * CELL} ${oy + row * CELL}) scale(${CELL}) rotate(${90 * r} 0.5 0.5)` }, svg);
        face(g);
        mark(g, id);
      }
      const lab = document.createElement("span");
      lab.textContent = String(i + 1);
      b.appendChild(lab);
      b.addEventListener("click", () => pick(i));
      opts.appendChild(b);
    });
  }

  function onKey(e) {
    if (e.repeat) return;
    const k = Number(e.key);
    if (Number.isInteger(k) && k >= 1 && k <= item.options.length) { e.preventDefault(); pick(k - 1); }
  }
  function pick(i) { end({ choice: i, rt: Math.round(performance.now() - t0) }, false); }
  function end(resp, timedOut) {
    if (done) return;
    done = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", onKey);
    opts.querySelectorAll("button").forEach((b) => (b.disabled = true));
    ctx.finish(resp, timedOut);
  }

  ctx.root.querySelector("#cn-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    drawCube();
    drawOptions();
    body.hidden = false;
    t0 = performance.now();
    document.addEventListener("keydown", onKey);
    timer = setTimeout(() => end({ choice: null, rt: null }, true), 100000);
  }, { once: true });
};
