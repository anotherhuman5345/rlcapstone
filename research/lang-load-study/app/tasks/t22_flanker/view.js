// Flanker: 16 displays; each shows for up to 1500 ms after a 500 ms fixation.
// Answer with the arrow keys or the two buttons. Responses are sent in display order.
TaskViews["flanker"] = function (ctx) {
  const disp = ctx.root.querySelector("#fl-display");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ key, rt: key ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => { if (e.repeat) return; if (e.key === "ArrowLeft") done("left"); if (e.key === "ArrowRight") done("right"); };
      const onBtn = (e) => done(e.currentTarget.dataset.key);
      const timer = setTimeout(() => done(null), limit);
      function cleanup() { clearTimeout(timer); document.removeEventListener("keydown", onKey); btns.forEach((b) => b.removeEventListener("click", onBtn)); }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  ctx.root.querySelector("#fl-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btns.forEach((b) => (b.disabled = false));
    for (const d of ctx.item.displays) {
      disp.textContent = "+";
      await wait(500);
      disp.textContent = d.text;
      out.push(await answer(1500));
    }
    disp.textContent = "";
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
