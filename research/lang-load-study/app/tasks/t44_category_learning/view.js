// Category learning: 16 training objects with feedback, then 8 new objects without.
// Answer with the left/right arrow keys or the two group buttons (5 s limit each).
// Response: {train: [{choice, rt}], transfer: [{choice, rt}]}; choice 0/1/null.
TaskViews["category_learning"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const svg = root.querySelector("#cl-obj"), fb = root.querySelector("#cl-fb");
  const prog = root.querySelector("#cl-prog");
  const btns = [...root.querySelectorAll("[data-cat]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"];
  const out = { train: [], transfer: [] };
  btns.forEach((b) => (b.disabled = true));

  function shapeMarkup(shape, attrs) {
    if (shape === 0) return `<circle cx="100" cy="100" r="70" ${attrs}/>`;
    if (shape === 1) return `<rect x="35" y="35" width="130" height="130" ${attrs}/>`;
    if (shape === 2) return `<polygon points="100,25 175,165 25,165" ${attrs}/>`;
    return `<polygon points="75,25 125,25 125,75 175,75 175,125 125,125 125,175 75,175 75,125 25,125 25,75 75,75" ${attrs}/>`;
  }

  function draw(f) {
    const [shape, color, pat] = f;
    const c = COLORS[color];
    let defs = "", paint = c;
    if (pat === 1) {
      defs = `<pattern id="cl-p" width="14" height="14" patternUnits="userSpaceOnUse"><rect width="14" height="14" fill="#fff"/><rect width="14" height="6" fill="${c}"/></pattern>`;
      paint = "url(#cl-p)";
    } else if (pat === 2) {
      defs = `<pattern id="cl-p" width="16" height="16" patternUnits="userSpaceOnUse"><rect width="16" height="16" fill="#fff"/><circle cx="8" cy="8" r="4" fill="${c}"/></pattern>`;
      paint = "url(#cl-p)";
    } else if (pat === 3) {
      paint = "#fff";
    }
    svg.innerHTML = `<defs>${defs}</defs>` + shapeMarkup(shape, `fill="${paint}" stroke="${c}" stroke-width="6"`);
  }

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
        resolve({ choice: v, rt: v === null ? null : Math.round(performance.now() - t0) });
      };
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done(0); }
        if (e.key === "ArrowRight") { e.preventDefault(); done(1); }
      };
      const onBtn = (e) => done(Number(e.currentTarget.dataset.cat));
      const timer = setTimeout(() => done(null), limit);
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  async function run(list, phase, feedback) {
    for (let k = 0; k < list.length; k++) {
      prog.textContent = fill(tx[phase + "_of"], { n: k + 1, total: list.length });
      svg.innerHTML = "";
      fb.textContent = "";
      fb.className = "cl-fb";
      await wait(400);
      draw(list[k].f);
      btns.forEach((b) => (b.disabled = false));
      const a = await answer(5000);
      btns.forEach((b) => (b.disabled = true));
      out[phase].push(a);
      if (feedback) {
        const cat = list[k].cat;
        if (a.choice === null) { fb.textContent = fill(tx.too_slow, { group: tx.groups[cat] }); fb.className = "cl-fb bad"; }
        else if (a.choice === cat) { fb.textContent = tx.correct; fb.className = "cl-fb good"; }
        else { fb.textContent = fill(tx.wrong, { group: tx.groups[cat] }); fb.className = "cl-fb bad"; }
        await wait(1100);
      }
    }
  }

  root.querySelector("#cl-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    await run(it.train, "train", true);
    svg.innerHTML = "";
    fb.className = "cl-fb";
    fb.textContent = tx.transfer_note;
    prog.textContent = "";
    await wait(2500);
    await run(it.transfer, "transfer", false);
    svg.innerHTML = "";
    fb.textContent = "";
    prog.textContent = "";
    ctx.finish(out, false);
  }, { once: true });
};
