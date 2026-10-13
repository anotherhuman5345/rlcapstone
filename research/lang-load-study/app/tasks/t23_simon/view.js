// Simon: 24 displays; fixation 500 ms, then a colored circle on the left or right for up
// to 2000 ms. Answer by color with the arrow keys or the two buttons (each button shows
// its color). Responses in display order: {key: "left"|"right"|null, rt: ms from onset}.
TaskViews["simon"] = function (ctx) {
  const fix = ctx.root.querySelector("#sm-fix");
  const dots = { left: ctx.root.querySelector("#sm-left"), right: ctx.root.querySelector("#sm-right") };
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const palette = ctx.item.palette;
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (key) => { cleanup(); resolve({ key, rt: key ? Math.round(performance.now() - t0) : null }); };
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

  function hide() { for (const s of ["left", "right"]) dots[s].style.visibility = "hidden"; }

  ctx.root.querySelector("#sm-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    btns.forEach((b) => (b.disabled = false));
    for (const d of ctx.item.displays) {
      hide();
      fix.textContent = "+";
      await wait(500);
      fix.textContent = "";
      dots[d.side].style.background = palette[d.color];
      dots[d.side].style.visibility = "visible";
      out.push(await answer(2000));
    }
    hide();
    fix.textContent = "";
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
