// Prospective memory: 30 displays; each = 300 ms fixation, then the number for up to
// 1500 ms (the first valid response ends it). Left arrow / Odd, right arrow / Even,
// space bar / Special. Framed numbers are the cues that call for Special.
// Response: [{key: "odd"|"even"|"special"|null, rt}] in display order.
TaskViews["prospective_memory"] = function (ctx) {
  const num = ctx.root.querySelector("#pm-num");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const keyOk = (e) => !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey && !(e.target.closest && e.target.closest("form"));
  const KEYS = { ArrowLeft: "odd", ArrowRight: "even", " ": "special" };
  btns.forEach((b) => (b.disabled = true));

  // Swallow the space bar for the whole trial so it never "clicks" a focused button.
  const blockSpace = (e) => { if (e.key === " " && !(e.target.closest && e.target.closest("form"))) e.preventDefault(); };

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ key, rt: key ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => { if (keyOk(e) && KEYS[e.key]) { e.preventDefault(); done(KEYS[e.key]); } };
      const onBtn = (e) => { e.currentTarget.blur(); done(e.currentTarget.dataset.key); };
      const timer = setTimeout(() => done(null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        btns.forEach((b) => b.removeEventListener("click", onBtn));
      }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  ctx.root.querySelector("#pm-start").addEventListener("click", async (e) => {
    e.currentTarget.blur();
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", blockSpace);
    btns.forEach((b) => (b.disabled = false));
    const out = [];
    for (const d of ctx.item.displays) {
      num.classList.remove("cue");
      num.textContent = "+";
      await wait(300);
      num.textContent = String(d.number);
      num.classList.toggle("cue", !!d.cue);
      out.push(await answer(1500));
    }
    num.classList.remove("cue");
    num.textContent = "";
    btns.forEach((b) => (b.disabled = true));
    document.removeEventListener("keydown", blockSpace);
    ctx.finish(out, false);
  }, { once: true });
};
