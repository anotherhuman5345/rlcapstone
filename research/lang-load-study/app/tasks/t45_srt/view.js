// Serial reaction time: one of four boxes lights up; press its key (D F J K by physical
// position, or 1-4) or tap/click the box. 2 s limit per target, 250 ms between targets.
// Response: [{key: 0-3 or null, rt}] in target order (first press only).
TaskViews["srt"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const boxes = [...root.querySelectorAll("[data-pos]")];
  const prog = root.querySelector("#srt-prog");
  const CODES = { KeyD: 0, KeyF: 1, KeyJ: 2, KeyK: 3 };
  const DIGITS = { "1": 0, "2": 1, "3": 2, "4": 3 };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const out = [];

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      let settled = false;
      const done = (pos) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        boxes.forEach((b) => b.removeEventListener("pointerdown", onPtr));
        resolve({ key: pos, rt: pos === null ? null : Math.round(performance.now() - t0) });
      };
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        let pos = CODES[e.code];
        if (pos === undefined) pos = DIGITS[e.key];
        if (pos !== undefined) { e.preventDefault(); done(pos); }
      };
      const onPtr = (e) => { e.preventDefault(); done(Number(e.currentTarget.dataset.pos)); };
      const timer = setTimeout(() => done(null), limit);
      document.addEventListener("keydown", onKey);
      boxes.forEach((b) => b.addEventListener("pointerdown", onPtr));
    });
  }

  root.querySelector("#srt-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    await wait(800);
    for (let k = 0; k < it.targets.length; k++) {
      prog.textContent = fill(tx.progress, { n: k + 1, total: it.targets.length });
      const box = boxes[it.targets[k]];
      box.classList.add("lit");
      const a = await answer(2000);
      box.classList.remove("lit");
      out.push(a);
      await wait(250);
    }
    prog.textContent = "";
    ctx.finish(out, false);
  }, { once: true });
};
