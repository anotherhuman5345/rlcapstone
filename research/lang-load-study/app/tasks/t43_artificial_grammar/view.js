// Artificial grammar: study 10 letter strings (fixed time), then classify 12 new strings
// with the left/right arrow keys or the two buttons (8 s limit each).
// Response: [{i, legal (true/false/null), rt}] in test order.
TaskViews["artificial_grammar"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const list = root.querySelector("#agl-list"), count = root.querySelector("#agl-count");
  const str = root.querySelector("#agl-str"), row = root.querySelector("#agl-btns");
  const btns = [...row.querySelectorAll("[data-legal]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const out = [];

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      let settled = false;
      const done = (v) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        btns.forEach((b) => b.removeEventListener("click", onBtn));
        resolve({ legal: v, rt: v === null ? null : Math.round(performance.now() - t0) });
      };
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done(true); }
        if (e.key === "ArrowRight") { e.preventDefault(); done(false); }
      };
      const onBtn = (e) => done(e.currentTarget.dataset.legal === "1");
      const timer = setTimeout(() => done(null), limit);
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  root.querySelector("#agl-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    // Study phase: all strings together for a fixed time, with a countdown.
    list.hidden = false;
    it.study.forEach((s) => {
      const d = document.createElement("div");
      d.textContent = s;
      list.appendChild(d);
    });
    const tEnd = performance.now() + it.study_ms;
    while (performance.now() < tEnd) {
      count.textContent = fill(tx.study_left, { s: Math.ceil((tEnd - performance.now()) / 1000) });
      await wait(Math.min(250, Math.max(0, tEnd - performance.now())));
    }
    list.hidden = true;
    list.innerHTML = "";
    row.hidden = false;
    // Test phase.
    for (let i = 0; i < it.test.length; i++) {
      count.textContent = fill(tx.test_of, { n: i + 1, total: it.test.length });
      str.textContent = "+";
      await wait(400);
      str.textContent = it.test[i];
      const a = await answer(8000);
      out.push({ i, legal: a.legal, rt: a.rt });
    }
    str.textContent = "";
    count.textContent = "";
    row.hidden = true;
    ctx.finish(out, false);
  }, { once: true });
};
