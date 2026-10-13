// Stroop: 24 displays; fixation 500 ms, then the word in colored ink for up to 2000 ms.
// Answer with keys 1-4 or the four color buttons. The word comes from ctx.text.words
// (the trial's language); the ink from item.palette. Responses are in display order:
// {key: palette index | null, rt: ms from word onset}.
TaskViews["stroop"] = function (ctx) {
  const disp = ctx.root.querySelector("#st-display");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const words = ctx.text.words;
  const palette = ctx.item.palette;
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ key, rt: key === null ? null : Math.round(performance.now() - t0) }); };
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

  ctx.root.querySelector("#st-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btns.forEach((b) => (b.disabled = false));
    for (const d of ctx.item.displays) {
      disp.style.color = "";
      disp.textContent = "+";
      await wait(500);
      disp.style.color = palette[d.ink];
      disp.textContent = words[d.word];
      out.push(await answer(2000));
    }
    disp.style.color = "";
    disp.textContent = "";
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
