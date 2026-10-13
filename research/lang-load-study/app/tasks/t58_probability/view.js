// Probability reasoning: 4 comparisons, one at a time. Each event is described in words
// (templates from the text file) and drawn (balls in a bag / two dice) with the same numbers.
// Answer with the buttons or keys 1 (A), 2 (equally likely), 3 (B).
// Response: [{choice: "a"|"b"|"equal", rt}] in order; finish() is called once at the end.
TaskViews["probability"] = function (ctx) {
  const T = ctx.text, comps = ctx.item.comparisons || [];
  const $ = (s) => ctx.root.querySelector(s);
  const btns = [...ctx.root.querySelectorAll("[data-choice]")];
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const NS = "http://www.w3.org/2000/svg";
  const RED = "#C62828", BLUE = "#1565C0";
  const out = [];
  btns.forEach((b) => (b.disabled = true));

  function el(tag, attrs, parent, txt) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (txt != null) e.textContent = txt;
    parent.appendChild(e);
    return e;
  }
  function describe(ev, label) {
    if (ev.kind === "dice_sum") return fmt(T.ev_dice, { s: ev.total });
    const tpl = ev.kind === "bag1" ? T.ev_bag1 : ev.replace ? T.ev_bag2_replace : T.ev_bag2_keep;
    return fmt(tpl, { L: label, r: ev.red, b: ev.blue });
  }
  function draw(svg, ev) {
    svg.textContent = "";
    if (ev.kind === "dice_sum") {
      for (const x of [12, 112]) {
        el("rect", { x, y: 45, width: 70, height: 70, rx: 12, fill: "#fff", stroke: "#1D2731", "stroke-width": 3 }, svg);
        el("text", { x: x + 35, y: 92, "text-anchor": "middle", "font-size": 34, fill: "#5E6C78" }, svg, "?");
      }
      el("text", { x: 97, y: 92, "text-anchor": "middle", "font-size": 30 }, svg, "+");
      el("text", { x: 226, y: 92, "text-anchor": "middle", "font-size": 30, "font-weight": 700 }, svg, "= " + ev.total);
      return;
    }
    el("rect", { x: 20, y: 20, width: 170, height: 140, rx: 22, fill: "#F4F6F8", stroke: "#1D2731", "stroke-width": 3 }, svg);
    const n = ev.red + ev.blue, cols = 4;
    for (let i = 0; i < n; i++) {
      const cx = 48 + (i % cols) * 38, cy = 45 + Math.floor(i / cols) * 36;
      el("circle", { cx, cy, r: 14, fill: i < ev.red ? RED : BLUE, stroke: "#fff", "stroke-width": 2 }, svg);
    }
    if (ev.kind === "bag2") {
      // two draws: "put back" shows a looping arrow into the bag; "keep out" an arrow out of it
      if (ev.replace) {
        el("path", { d: "M200 60 C245 60 245 120 200 120", fill: "none", stroke: "#1D2731", "stroke-width": 3 }, svg);
        el("path", { d: "M200 120 l10 -8 l0 16 z", fill: "#1D2731" }, svg);
      } else {
        el("path", { d: "M195 90 L245 90", stroke: "#1D2731", "stroke-width": 3 }, svg);
        el("path", { d: "M248 90 l-10 -8 l0 16 z", fill: "#1D2731" }, svg);
      }
      el("text", { x: 225, y: 150, "text-anchor": "middle", "font-size": 22, "font-weight": 700 }, svg, "×2");
    }
  }

  function answer() {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const map = { "1": "a", "2": "equal", "3": "b" };
      const done = (choice) => { cleanup(); resolve({ choice, rt: Math.round(performance.now() - t0) }); };
      const onKey = (e) => { if (e.repeat) return; if (map[e.key]) { e.preventDefault(); done(map[e.key]); } };
      const onBtn = (e) => done(e.currentTarget.dataset.choice);
      function cleanup() { document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  $("#pr-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    $("#pr-opts").hidden = false;
    for (let i = 0; i < comps.length; i++) {
      const c = comps[i];
      ctx.status(fmt(T.progress, { i: i + 1, n: comps.length }));
      $("#pr-q").textContent = T.question;
      $("#pr-text-a").textContent = describe(c.a, T.label_a);
      $("#pr-text-b").textContent = describe(c.b, T.label_b);
      draw($("#pr-svg-a"), c.a);
      draw($("#pr-svg-b"), c.b);
      btns.forEach((b) => (b.disabled = false));
      out.push(await answer());
      btns.forEach((b) => (b.disabled = true));
    }
    $("#pr-opts").hidden = true; $("#pr-q").textContent = " "; ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
