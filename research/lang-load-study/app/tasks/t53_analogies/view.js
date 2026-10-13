// Visual analogies: A -> B, C -> ?; pick the option (1-4) that changes C the way A changed
// into B. Figures are drawn from polygon points computed on the server. Answer by click/tap
// or keys 1-4. Response: [{choice: option index 0-3, rt}] in problem order; finish() once.
TaskViews["analogies"] = function (ctx) {
  const T = ctx.text, probs = ctx.item.problems || [];
  const $ = (s) => ctx.root.querySelector(s);
  const NS = "http://www.w3.org/2000/svg";
  const btns = [...ctx.root.querySelectorAll("[data-opt]")];
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const out = [];
  btns.forEach((b) => (b.disabled = true));

  function draw(svg, fig) {
    svg.textContent = "";
    if (!fig) {
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", 160); t.setAttribute("y", 75); t.setAttribute("text-anchor", "middle");
      t.setAttribute("font-size", 40); t.setAttribute("fill", "#5E6C78"); t.textContent = "?";
      svg.appendChild(t);
      return;
    }
    const n = fig.count;
    for (let i = 0; i < n; i++) {
      const cx = 160 + (i - (n - 1) / 2) * 100, cy = 60;
      const poly = document.createElementNS(NS, "polygon");
      poly.setAttribute("points", fig.pts.map(([x, y]) => (cx + x * 48).toFixed(1) + "," + (cy + y * 48).toFixed(1)).join(" "));
      poly.setAttribute("fill", fig.fill ? "#1D2731" : "#FFFFFF");
      poly.setAttribute("stroke", "#1D2731");
      poly.setAttribute("stroke-width", 3);
      poly.setAttribute("stroke-linejoin", "round");
      svg.appendChild(poly);
    }
  }

  function answer() {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (choice) => { cleanup(); resolve({ choice, rt: Math.round(performance.now() - t0) }); };
      const onKey = (e) => {
        if (e.repeat) return;
        const i = "1234".indexOf(e.key);
        if (i >= 0 && e.key.length === 1) { e.preventDefault(); done(i); }
      };
      const onBtn = (e) => done(Number(e.currentTarget.dataset.opt));
      function cleanup() { document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  $("#an-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    $("#an-stem").classList.remove("an-hidden");
    $("#an-opts").classList.remove("an-hidden");
    for (let i = 0; i < probs.length; i++) {
      const p = probs[i];
      ctx.status(fmt(T.progress, { i: i + 1, n: probs.length }));
      draw($("#an-a"), p.a); draw($("#an-b"), p.b); draw($("#an-c"), p.c); draw($("#an-q"), null);
      btns.forEach((b, k) => draw(b.querySelector("svg"), p.options[k]));
      btns.forEach((b) => (b.disabled = false));
      out.push(await answer());
      btns.forEach((b) => (b.disabled = true));
    }
    $("#an-stem").classList.add("an-hidden");
    $("#an-opts").classList.add("an-hidden");
    ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
