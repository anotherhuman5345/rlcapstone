// Conditional reasoning: part 1 (one rule, 4 shapes), part 2 (two rules, 4 shapes).
// Rule sentences are assembled from phrases in the text file. Answer with the buttons or
// the Left (follows) / Right (breaks) arrow keys. Response: [{choice, rt}] for the 8 shapes;
// finish() is called once after the last shape.
TaskViews["conditional_reasoning"] = function (ctx) {
  const T = ctx.text, parts = ctx.item.parts || [];
  const $ = (s) => ctx.root.querySelector(s);
  const rulesEl = $("#cr-rules"), qEl = $("#cr-q"), card = $("#cr-card");
  const btns = [...ctx.root.querySelectorAll("[data-choice]")];
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const NS = "http://www.w3.org/2000/svg";
  const COLORS = { red: "#C62828", blue: "#1565C0" };
  const out = [];
  btns.forEach((b) => (b.disabled = true));

  const phrase = (kind, lit) => T[kind + (lit.neg ? "_not_" : "_") + lit.attr + "_" + lit.val];
  function sentence(rule) { return fmt(T.rule_pattern, { if: phrase("if", rule.p), then: phrase("then", rule.q) }); }

  function draw(obj) {
    card.textContent = "";
    const frame = document.createElementNS(NS, "rect");
    Object.entries({ x: 2, y: 2, width: 196, height: 196, rx: 8, fill: "#fff", stroke: "#C7D0D8", "stroke-width": 2 }).forEach(([k, v]) => frame.setAttribute(k, v));
    card.appendChild(frame);
    const big = obj.size === "big";
    let el;
    if (obj.shape === "circle") {
      el = document.createElementNS(NS, "circle");
      el.setAttribute("cx", 100); el.setAttribute("cy", 100); el.setAttribute("r", big ? 80 : 32);
    } else {
      const s = big ? 150 : 60;
      el = document.createElementNS(NS, "rect");
      el.setAttribute("x", 100 - s / 2); el.setAttribute("y", 100 - s / 2); el.setAttribute("width", s); el.setAttribute("height", s);
    }
    el.setAttribute("fill", COLORS[obj.color]);
    card.appendChild(el);
  }

  function answer() {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (choice) => { cleanup(); resolve({ choice, rt: Math.round(performance.now() - t0) }); };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("follows"); }
        else if (e.key === "ArrowRight") { e.preventDefault(); done("breaks"); }
      };
      const onBtn = (e) => done(e.currentTarget.dataset.choice);
      function cleanup() { document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  $("#cr-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    let shown = 0;
    const total = parts.reduce((a, p) => a + p.cases.length, 0);
    for (const part of parts) {
      rulesEl.textContent = "";
      for (const r of part.rules) { const p = document.createElement("p"); p.textContent = sentence(r); rulesEl.appendChild(p); }
      qEl.textContent = part.rules.length > 1 ? T.question_two : T.question_one;
      for (const c of part.cases) {
        card.textContent = "";
        await wait(300);
        draw(c.obj);
        shown += 1;
        ctx.status(fmt(T.progress, { i: shown, n: total }));
        btns.forEach((b) => (b.disabled = false));
        out.push(await answer());
        btns.forEach((b) => (b.disabled = true));
      }
    }
    card.textContent = ""; rulesEl.textContent = ""; qEl.textContent = " "; ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
