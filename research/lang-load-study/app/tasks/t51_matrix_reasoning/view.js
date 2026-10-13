// Matrix reasoning: 4 matrices; pick the cell that completes each one by clicking/tapping
// an option or pressing 1-4 (time limit item.limit_ms per matrix).
// Response: [{p, choice (option index or null), rt}] in matrix order.
TaskViews["matrix_reasoning"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const grid = root.querySelector("#mx-grid"), opts = root.querySelector("#mx-opts");
  const prog = root.querySelector("#mx-prog");
  const NS = "http://www.w3.org/2000/svg";
  const SHADES = ["#ffffff", "#9a9a9a", "#222222"];
  const SIZES = [11, 15, 19];
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const out = [];

  function shapeEl(kind, x, y, r, shade) {
    let el;
    if (kind === 0) {
      el = document.createElementNS(NS, "circle");
      el.setAttribute("cx", x); el.setAttribute("cy", y); el.setAttribute("r", r);
    } else if (kind === 1) {
      el = document.createElementNS(NS, "rect");
      el.setAttribute("x", x - r * 0.88); el.setAttribute("y", y - r * 0.88);
      el.setAttribute("width", r * 1.76); el.setAttribute("height", r * 1.76);
    } else {
      el = document.createElementNS(NS, "polygon");
      const pts = kind === 2
        ? [[x, y - r], [x + r * 0.95, y + r * 0.75], [x - r * 0.95, y + r * 0.75]]
        : [[x, y - r * 1.1], [x + r, y], [x, y + r * 1.1], [x - r, y]];
      el.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
    }
    el.setAttribute("fill", SHADES[shade]);
    el.setAttribute("stroke", "#222");
    el.setAttribute("stroke-width", "2.5");
    return el;
  }

  function cellSvg(c) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("aria-hidden", "true");
    const pos = c.count === 1 ? [[50, 50]] : c.count === 2 ? [[29, 50], [71, 50]] : [[50, 28], [28, 70], [72, 70]];
    pos.forEach(([x, y]) => svg.appendChild(shapeEl(c.shape, x, y, SIZES[c.size], c.shade)));
    return svg;
  }

  function show(pr) {
    grid.innerHTML = "";
    pr.cells.forEach((c) => {
      const d = document.createElement("div");
      d.appendChild(cellSvg(c));
      grid.appendChild(d);
    });
    const q = document.createElement("div");
    q.textContent = "?";
    grid.appendChild(q);
  }

  function ask(pr) {
    return new Promise((resolve) => {
      opts.innerHTML = "";
      const btns = pr.options.map((o, i) => {
        const b = document.createElement("button");
        b.type = "button";
        b.setAttribute("aria-label", fill(tx.option, { n: i + 1 }));
        b.appendChild(cellSvg(o));
        const k = document.createElement("span");
        k.className = "k";
        k.textContent = String(i + 1);
        b.appendChild(k);
        b.addEventListener("click", () => done(i));
        opts.appendChild(b);
        return b;
      });
      const t0 = performance.now();
      let settled = false;
      const timer = setTimeout(() => done(null), it.limit_ms);
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        const n = Number(e.key);
        if (Number.isInteger(n) && n >= 1 && n <= btns.length) { e.preventDefault(); done(n - 1); }
      };
      function done(i) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        resolve({ choice: i, rt: i === null ? null : Math.round(performance.now() - t0) });
      }
      document.addEventListener("keydown", onKey);
    });
  }

  root.querySelector("#mx-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    grid.hidden = false;
    for (let p = 0; p < it.problems.length; p++) {
      prog.textContent = fill(tx.matrix_of, { n: p + 1, total: it.problems.length });
      show(it.problems[p]);
      const a = await ask(it.problems[p]);
      out.push({ p, choice: a.choice, rt: a.rt });
    }
    grid.hidden = true;
    opts.innerHTML = "";
    prog.textContent = "";
    ctx.finish(out, false);
  }, { once: true });
};
