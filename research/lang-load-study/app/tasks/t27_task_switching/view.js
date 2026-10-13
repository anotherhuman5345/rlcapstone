// Cued task switching: 25 events. Each: 500 ms blank, the cue word alone for item csi
// (200 or 800 ms), then the stimulus under the cue for up to 2000 ms. Keys pressed before
// stimulus onset are ignored. Arrow keys or the two buttons. Responses per event:
// {key: "left"|"right"|null, rt: ms from stimulus onset}.
TaskViews["task_switching"] = function (ctx) {
  const cue = ctx.root.querySelector("#ts-cue");
  const stim = ctx.root.querySelector("#ts-stim");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const palette = ctx.item.palette;
  const cueWord = { color: ctx.text.cue_color, shape: ctx.text.cue_shape };
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

  ctx.root.querySelector("#ts-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    for (const ev of ctx.item.events) {
      cue.textContent = "";
      stim.style.visibility = "hidden";
      btns.forEach((b) => (b.disabled = true));
      await wait(500);
      cue.textContent = cueWord[ev.task];
      await wait(ev.csi);
      stim.style.background = palette[ev.color];
      stim.style.borderRadius = ev.shape === "circle" ? "50%" : "0";
      stim.style.visibility = "visible";
      btns.forEach((b) => (b.disabled = false));
      out.push(await answer(2000));
    }
    cue.textContent = "";
    stim.style.visibility = "hidden";
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
