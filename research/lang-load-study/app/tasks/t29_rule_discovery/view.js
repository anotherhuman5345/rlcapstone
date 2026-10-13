// Rule discovery: sort each card onto one of four reference cards (click/tap or keys 1-4).
// Feedback for 800 ms after each sort. After item.criterion correct sorts in a row the
// rule moves to the next in item.rules (unannounced); ends when all rules are found or
// after item.max_trials sorts. No answer within item.window_ms = omission.
// Responses: [{choice: 0-3 | null, rt: ms, rule: active rule before the sort}].
TaskViews["rule_discovery"] = function (ctx) {
  const it = ctx.item;
  const FEATURE = { color: 0, shape: 1, count: 2 };
  const target = ctx.root.querySelector("#rd-target");
  const fb = ctx.root.querySelector("#rd-fb");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  function glyph(name, cx, cy, r) {
    const pts = (arr) => arr.map(([x, y]) => `${(cx + x * r).toFixed(1)},${(cy + y * r).toFixed(1)}`).join(" ");
    if (name === "circle") return `<circle cx="${cx}" cy="${cy}" r="${r * 0.9}"/>`;
    if (name === "triangle") return `<polygon points="${pts([[0, -1], [0.95, 0.8], [-0.95, 0.8]])}"/>`;
    if (name === "cross") return `<polygon points="${pts([[-0.3, -1], [0.3, -1], [0.3, -0.3], [1, -0.3], [1, 0.3], [0.3, 0.3], [0.3, 1], [-0.3, 1], [-0.3, 0.3], [-1, 0.3], [-1, -0.3], [-0.3, -0.3]])}"/>`;
    const star = [];
    for (let k = 0; k < 10; k++) {
      const a = -Math.PI / 2 + (k * Math.PI) / 5, rr = k % 2 ? 0.42 : 1;
      star.push([Math.cos(a) * rr, Math.sin(a) * rr]);
    }
    return `<polygon points="${pts(star)}"/>`;
  }
  const SPOTS = [[[50, 50]], [[50, 28], [50, 72]], [[50, 25], [27, 72], [73, 72]], [[28, 28], [72, 28], [28, 72], [72, 72]]];
  function card(color, shape, count) {
    const r = count === 1 ? 24 : 17;
    const g = SPOTS[count - 1].map(([x, y]) => glyph(it.shapes[shape], x, y, r)).join("");
    return `<svg viewBox="0 0 100 100" aria-hidden="true"><g fill="${it.colors[color]}" stroke="#222" stroke-width="1.5">${g}</g></svg>`;
  }
  btns.forEach((b, i) => { b.querySelector(".pic").innerHTML = card(i, i, i + 1); b.disabled = true; });

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ choice: key, rt: key === null ? null : Math.round(performance.now() - t0) }); };
      const onKey = (e) => {
        if (e.repeat) return;
        const k = ["1", "2", "3", "4"].indexOf(e.key);
        if (k >= 0) { e.preventDefault(); done(k); }
      };
      const onBtn = (e) => done(Number(e.currentTarget.dataset.key));
      const timer = setTimeout(() => done(null), limit);
      function cleanup() { clearTimeout(timer); document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  ctx.root.querySelector("#rd-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const out = [];
    let phase = 0, streak = 0;
    for (let t = 0; t < it.max_trials && phase < it.rules.length; t++) {
      const c = it.cards[t];
      const rule = it.rules[phase];
      target.innerHTML = card(c[0], c[1], c[2] + 1);
      fb.textContent = ""; fb.className = "fb";
      btns.forEach((b) => (b.disabled = false));
      const r = await answer(it.window_ms);
      btns.forEach((b) => (b.disabled = true));
      out.push({ choice: r.choice, rt: r.rt, rule });
      const ok = r.choice === c[FEATURE[rule]];
      fb.textContent = r.choice === null ? ctx.text.too_slow : ok ? ctx.text.correct : ctx.text.wrong;
      fb.className = "fb " + (ok ? "good" : "bad");
      streak = ok ? streak + 1 : 0;
      if (streak >= it.criterion) { phase += 1; streak = 0; }
      await wait(800);
      target.innerHTML = "";
      fb.textContent = ""; fb.className = "fb";
      await wait(250);
    }
    ctx.finish(out, false);
  }, { once: true });
};
