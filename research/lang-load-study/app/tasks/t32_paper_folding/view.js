// Paper folding: after Start, shows the fold sequence and four opened sheets.
// Pick a sheet by click/tap or digit keys 1-4. Response: {choice: 0-3 | null, rt}.
TaskViews["paper_folding"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const N = 8, S = 15, PANEL = 170;
  const item = ctx.item;
  const steps = ctx.root.querySelector("#pf-steps");
  const opts = ctx.root.querySelector("#pf-opts");
  const body = ctx.root.querySelector("#pf-body");
  let t0 = 0, done = false, timer = null;

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  // Folded part before each fold and after the last (same rule as logic.py).
  function regions(folds) {
    let r = [0, 0, N, N];
    const out = [r];
    for (const f of folds) {
      const [x0, y0, x1, y1] = r, mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
      r = { L: [mx, y0, x1, y1], R: [x0, y0, mx, y1], T: [x0, my, x1, y1], B: [x0, y0, x1, my] }[f];
      out.push(r);
    }
    return out;
  }
  function rect(g, r, attrs) {
    return el("rect", Object.assign({ x: r[0] * S, y: r[1] * S, width: (r[2] - r[0]) * S, height: (r[3] - r[1]) * S }, attrs), g);
  }

  function drawSteps() {
    const regs = regions(item.folds);
    const total = item.folds.length + 1;
    steps.setAttribute("viewBox", `0 0 ${total * PANEL} 170`);
    steps.setAttribute("width", total * PANEL);
    const defs = el("defs", {}, steps);
    const mk = el("marker", { id: "pf-head", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, defs);
    el("path", { d: "M0 0L10 5L0 10z", fill: "#1F6E8C" }, mk);
    for (let i = 0; i < total; i++) {
      const g = el("g", { transform: `translate(${i * PANEL + 25} 25)` }, steps);
      rect(g, [0, 0, N, N], { fill: "none", stroke: "#C7D0D8", "stroke-dasharray": "3 3" });
      const r = regs[i];
      rect(g, r, { fill: "#FFFDF5", stroke: "#1D2731", "stroke-width": 2 });
      if (i < item.folds.length) {
        const f = item.folds[i], next = regs[i + 1];
        const [x0, y0, x1, y1] = r, mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
        const flap = { L: [x0, y0, mx, y1], R: [mx, y0, x1, y1], T: [x0, y0, x1, my], B: [x0, my, x1, y1] }[f];
        rect(g, flap, { fill: "#C9DCEA", stroke: "none" });
        rect(g, r, { fill: "none", stroke: "#1D2731", "stroke-width": 2 });
        const vertical = f === "L" || f === "R";
        if (vertical) el("line", { x1: mx * S, y1: (y0 - 0.4) * S, x2: mx * S, y2: (y1 + 0.4) * S, stroke: "#1F6E8C", "stroke-width": 2.5, "stroke-dasharray": "6 4" }, g);
        else el("line", { x1: (x0 - 0.4) * S, y1: my * S, x2: (x1 + 0.4) * S, y2: my * S, stroke: "#1F6E8C", "stroke-width": 2.5, "stroke-dasharray": "6 4" }, g);
        const fc = [(flap[0] + flap[2]) / 2 * S, (flap[1] + flap[3]) / 2 * S];
        const tc = [(next[0] + next[2]) / 2 * S, (next[1] + next[3]) / 2 * S];
        const bend = vertical ? [0, -Math.min(2.5, (y1 - y0) / 2) * S] : [-Math.min(2.5, (x1 - x0) / 2) * S, 0];
        const cx = (fc[0] + tc[0]) / 2 + bend[0], cy = (fc[1] + tc[1]) / 2 + bend[1];
        el("path", { d: `M${fc[0]} ${fc[1]}Q${cx} ${cy} ${tc[0]} ${tc[1]}`, fill: "none", stroke: "#1F6E8C", "stroke-width": 2.5, "marker-end": "url(#pf-head)" }, g);
      } else {
        el("circle", { cx: (item.hole[0] + 0.5) * S, cy: (item.hole[1] + 0.5) * S, r: S * 0.32, fill: "#1D2731" }, g);
      }
      if (i < total - 1) el("text", { x: (i + 1) * PANEL - 12, y: 92, "font-size": 22, fill: "#5E6C78", "text-anchor": "middle" }, steps).textContent = "→";
    }
  }

  function drawOptions() {
    item.options.forEach((cells, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pf-opt";
      b.dataset.choice = i;
      const svg = el("svg", { viewBox: "-6 -6 132 132", "aria-hidden": "true" }, b);
      for (let k = 1; k < N; k++) {
        el("line", { x1: k * S, y1: 0, x2: k * S, y2: N * S, stroke: "#EEF1F4" }, svg);
        el("line", { x1: 0, y1: k * S, x2: N * S, y2: k * S, stroke: "#EEF1F4" }, svg);
      }
      el("rect", { x: 0, y: 0, width: N * S, height: N * S, fill: "none", stroke: "#1D2731", "stroke-width": 2 }, svg);
      for (const [x, y] of cells) el("circle", { cx: (x + 0.5) * S, cy: (y + 0.5) * S, r: S * 0.32, fill: "#1D2731" }, svg);
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

  ctx.root.querySelector("#pf-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    drawSteps();
    drawOptions();
    body.hidden = false;
    t0 = performance.now();
    document.addEventListener("keydown", onKey);
    timer = setTimeout(() => end({ choice: null, rt: null }, true), 75000);
  }, { once: true });
};
