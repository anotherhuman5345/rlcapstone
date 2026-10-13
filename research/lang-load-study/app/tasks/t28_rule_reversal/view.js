// Rule reversal: pick one of two figures (click/tap, or arrow keys). Feedback for 700 ms
// after every pick. After item.criterion correct picks in a row the correct figure
// switches (item.reversals times); the trial ends after the last phase reaches criterion
// or after item.max_trials picks. A pick not made within item.window_ms is an omission.
// Responses: [{choice: "left"|"right"|null, rt: ms, rule: figure index active before the pick}].
TaskViews["rule_reversal"] = function (ctx) {
  const it = ctx.item;
  const fb = ctx.root.querySelector("#rr-fb");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const side = { left: btns.find((b) => b.dataset.key === "left"), right: btns.find((b) => b.dataset.key === "right") };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function figure(name, color) {
    const s = { triangle: '<polygon points="50,8 94,88 6,88"/>',
      circle: '<circle cx="50" cy="50" r="42"/>',
      square: '<rect x="12" y="12" width="76" height="76"/>',
      star: '<polygon points="50,5 61,38 96,38 68,58 79,92 50,72 21,92 32,58 4,38 39,38"/>',
      diamond: '<polygon points="50,4 94,50 50,96 6,50"/>',
      cross: '<polygon points="36,6 64,6 64,36 94,36 94,64 64,64 64,94 36,94 36,64 6,64 6,36 36,36"/>' }[name];
    return `<svg viewBox="0 0 100 100" aria-hidden="true"><g fill="${color}" stroke="#222" stroke-width="2">${s}</g></svg>`;
  }

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ choice: key, rt: key ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("left"); }
        if (e.key === "ArrowRight") { e.preventDefault(); done("right"); }
      };
      const onBtn = (e) => done(e.currentTarget.dataset.key);
      const timer = setTimeout(() => done(null), limit);
      function cleanup() { clearTimeout(timer); document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  ctx.root.querySelector("#rr-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const out = [];
    let rule = it.first, streak = 0, revs = 0, done = false;
    for (let t = 0; t < it.max_trials && !done; t++) {
      const figLeft = it.left[t];
      side.left.innerHTML = figure(it.figures[figLeft], it.colors[figLeft]);
      side.right.innerHTML = figure(it.figures[1 - figLeft], it.colors[1 - figLeft]);
      fb.textContent = ""; fb.className = "fb";
      btns.forEach((b) => (b.disabled = false));
      const r = await answer(it.window_ms);
      btns.forEach((b) => (b.disabled = true));
      out.push({ choice: r.choice, rt: r.rt, rule });
      const chosen = r.choice === "left" ? figLeft : r.choice === "right" ? 1 - figLeft : null;
      const ok = chosen === rule;
      fb.textContent = r.choice === null ? ctx.text.too_slow : ok ? ctx.text.correct : ctx.text.wrong;
      fb.className = "fb " + (ok ? "good" : "bad");
      streak = ok ? streak + 1 : 0;
      if (streak >= it.criterion) {
        if (revs < it.reversals) { rule = 1 - rule; revs += 1; streak = 0; } else { done = true; }
      }
      await wait(700);
      side.left.innerHTML = ""; side.right.innerHTML = "";
      fb.textContent = ""; fb.className = "fb";
      await wait(250);
    }
    ctx.finish(out, false);
  }, { once: true });
};
