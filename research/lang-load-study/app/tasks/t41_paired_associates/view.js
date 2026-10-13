// Paired-associate learning: 2 cycles of (study 6 pairs: 2500 ms each + 500 ms blank;
// test 6 symbols: pick the word, up to 6000 ms each, 400 ms blank after).
// Answer by clicking/tapping an option or pressing its number key (1-8).
// Response: {cycles: [[{choice: word index|null, rt}, ...in test order], ...]}.
TaskViews["paired_associates"] = function (ctx) {
  const tx = ctx.text, item = ctx.item;
  const $ = (s) => ctx.root.querySelector(s);
  const symEl = $("#pa-sym"), wordEl = $("#pa-word"), phase = $("#pa-phase"), optsEl = $("#pa-opts");
  const opts = [...optsEl.querySelectorAll("[data-choice]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const keyOk = (e) => !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey && !(e.target.closest && e.target.closest("form"));
  const NS = "http://www.w3.org/2000/svg";
  const fill = (tpl, c) => tpl.split("{c}").join(String(c));

  function drawSymbol(pts) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("aria-hidden", "true");
    const xy = (p) => [18 + p[0] * 32, 18 + p[1] * 32];
    const line = document.createElementNS(NS, "polyline");
    line.setAttribute("points", pts.map((p) => xy(p).join(",")).join(" "));
    line.setAttribute("fill", "none");
    line.setAttribute("stroke", "currentColor");
    line.setAttribute("stroke-width", "7");
    line.setAttribute("stroke-linecap", "round");
    line.setAttribute("stroke-linejoin", "round");
    const dot = document.createElementNS(NS, "circle");
    const [cx, cy] = xy(pts[0]);
    dot.setAttribute("cx", cx); dot.setAttribute("cy", cy); dot.setAttribute("r", "8");
    dot.setAttribute("fill", "currentColor");
    svg.append(line, dot);
    symEl.replaceChildren(svg);
  }

  function choose(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (choice) => { cleanup(); resolve({ choice, rt: choice === null ? null : Math.round(performance.now() - t0) }); };
      const onKey = (e) => {
        if (!keyOk(e)) return;
        const k = parseInt(e.key, 10);
        if (k >= 1 && k <= opts.length) { e.preventDefault(); done(parseInt(opts[k - 1].dataset.choice, 10)); }
      };
      const onBtn = (e) => { e.currentTarget.blur(); done(parseInt(e.currentTarget.dataset.choice, 10)); };
      const timer = setTimeout(() => done(null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        opts.forEach((b) => b.removeEventListener("click", onBtn));
      }
      document.addEventListener("keydown", onKey);
      opts.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  $("#pa-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const cycles = [];
    for (let c = 0; c < item.test_orders.length; c++) {
      phase.textContent = fill(tx.phase_study, c + 1);
      for (const s of item.study_orders[c]) {
        drawSymbol(item.symbols[s]);
        wordEl.textContent = tx.words[item.words[s]];
        await wait(2500);
        symEl.replaceChildren();
        wordEl.textContent = "";
        await wait(500);
      }
      phase.textContent = fill(tx.phase_test, c + 1);
      optsEl.hidden = false;
      const rows = [];
      for (const s of item.test_orders[c]) {
        drawSymbol(item.symbols[s]);
        rows.push(await choose(6000));
        symEl.replaceChildren();
        await wait(400);
      }
      optsEl.hidden = true;
      cycles.push(rows);
    }
    phase.textContent = "";
    ctx.finish({ cycles }, false);
  }, { once: true });
};
