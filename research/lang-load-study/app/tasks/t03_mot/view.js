// Multiple-object tracking: 3 rounds. Each round: targets shown in orange for item.cue_ms,
// all grey for 500 ms, then item.motion_ms of motion (positions interpolated from the stored
// 20 Hz key frames by elapsed time, so speed is the same at any refresh rate), then the person
// selects exactly k circles (click/tap, or number keys 1-8 once numbers appear) and presses
// Done (or Enter). Response per round: {selected: [ids], rt}.
TaskViews["mot"] = function (ctx) {
  const it = ctx.item, T = ctx.text, NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#mot-stage");
  const doneBtn = ctx.root.querySelector("#mot-done");
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const GREY = "#B8C4CE", ORANGE = "#F39C12", PICK = "#5DADE2";
  const fmt = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => (k in v ? v[k] : ""));

  function mk(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    (parent || svg).appendChild(e);
    return e;
  }
  // One <g> per object ID; IDs never change, so selection maps straight to the stored targets.
  const objs = [];
  for (let i = 0; i < it.n; i++) {
    const g = mk("g", { "data-i": i, style: "cursor:pointer" });
    const c = mk("circle", { cx: 0, cy: 0, r: it.r, fill: GREY }, g);
    const hit = mk("circle", { cx: 0, cy: 0, r: it.r + 8, fill: "transparent" }, g);
    const lab = mk("text", { x: 0, y: 7, "text-anchor": "middle", "font-size": 20, "font-weight": 700, fill: "#1D2731" }, g);
    objs.push({ g, c, hit, lab });
  }
  svg.style.visibility = "hidden";
  function place(frame) {
    objs.forEach((o, i) => o.g.setAttribute("transform", `translate(${frame[2 * i]},${frame[2 * i + 1]})`));
  }
  function colour(fn) { objs.forEach((o, i) => o.c.setAttribute("fill", fn(i))); }
  function labels(on) { objs.forEach((o, i) => (o.lab.textContent = on ? String(i + 1) : "")); }

  function animate(frames) {
    return new Promise((resolve) => {
      const t0 = performance.now(), last = frames.length - 1;
      function tick(now) {
        const f = Math.min(((now - t0) / 1000) * it.hz, last);
        const a = Math.floor(f), b = Math.min(a + 1, last), u = f - a;
        const fa = frames[a], fb = frames[b];
        place(fa.map((v, j) => v + (fb[j] - v) * u));
        if (f >= last) resolve(); else requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  function select(k) {
    return new Promise((resolve) => {
      const chosen = new Set();
      const t0 = performance.now();
      labels(true);
      ctx.status(fmt(T.pick, { k }));
      const refresh = () => {
        colour((i) => (chosen.has(i) ? PICK : GREY));
        doneBtn.disabled = chosen.size !== k;
      };
      const toggle = (i) => {
        if (chosen.has(i)) chosen.delete(i);
        else if (chosen.size < k) chosen.add(i);
        refresh();
      };
      const onPtr = (e) => {
        const g = e.target.closest && e.target.closest("[data-i]");
        if (g) toggle(Number(g.getAttribute("data-i")));
      };
      const onKey = (e) => {
        if (e.repeat) return;
        const d = Number(e.key);
        if (Number.isInteger(d) && d >= 1 && d <= it.n) toggle(d - 1);
        if (e.key === "Enter" && chosen.size === k) { e.preventDefault(); finishRound(); }
      };
      const finishRound = () => {
        svg.removeEventListener("pointerdown", onPtr);
        document.removeEventListener("keydown", onKey);
        doneBtn.removeEventListener("click", finishRound);
        doneBtn.disabled = true;
        labels(false);
        ctx.status("");
        resolve({ selected: [...chosen].sort((a, b) => a - b), rt: Math.round(performance.now() - t0) });
      };
      svg.addEventListener("pointerdown", onPtr);
      document.addEventListener("keydown", onKey);
      doneBtn.addEventListener("click", finishRound);
      refresh();
    });
  }

  ctx.root.querySelector("#mot-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    svg.style.visibility = "visible";
    for (let r = 0; r < it.rounds.length; r++) {
      const rd = it.rounds[r], tg = new Set(rd.targets);
      ctx.status(fmt(T.round, { n: r + 1, total: it.rounds.length, k: rd.k }));
      place(rd.frames[0]);
      colour((i) => (tg.has(i) ? ORANGE : GREY));
      await wait(it.cue_ms);
      colour(() => GREY);
      ctx.status(T.track);
      await wait(500);
      await animate(rd.frames);
      out.push(await select(rd.k));
      colour(() => GREY);
      await wait(600);
    }
    svg.style.visibility = "hidden";
    ctx.finish(out, false);
  }, { once: true });
};
