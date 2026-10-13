// Perspective taking: one map, four questions. Each question stays up to 20 s; answer with
// the arrow keys (up = ahead, right, down = behind, left) or the four buttons.
// Responses in question order: [{dir: "ahead"|"right"|"behind"|"left"|null, rt}].
TaskViews["perspective_taking"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const item = ctx.item;
  const map = ctx.root.querySelector("#pt-map");
  const qbox = ctx.root.querySelector("#pt-q");
  const btns = [...ctx.root.querySelectorAll("[data-dir]")];
  const slots = ["at", "face", "to"].map((k) => ctx.root.querySelector("#pt-" + k));
  const KEYS = { ArrowUp: "ahead", ArrowRight: "right", ArrowDown: "behind", ArrowLeft: "left" };
  const COLORS = ["#C0392B", "#1F6E8C", "#2E8B57", "#D68910", "#8E44AD", "#34495E"];
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  btns.forEach((b) => (b.disabled = true));

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  // Landmark symbol i, centred at 0,0, about 32 px across.
  function icon(parent, i, x, y) {
    const g = el("g", { transform: `translate(${x} ${y})` }, parent);
    const a = { fill: COLORS[i], stroke: "#1D2731", "stroke-width": 2 };
    const star = (n, r1, r2) => Array.from({ length: 2 * n }, (_, k) => {
      const ang = Math.PI * k / n - Math.PI / 2, r = k % 2 ? r2 : r1;
      return `${(r * Math.cos(ang)).toFixed(1)},${(r * Math.sin(ang)).toFixed(1)}`;
    }).join(" ");
    const reg = (n, r) => Array.from({ length: n }, (_, k) => {
      const ang = 2 * Math.PI * k / n - Math.PI / 2;
      return `${(r * Math.cos(ang)).toFixed(1)},${(r * Math.sin(ang)).toFixed(1)}`;
    }).join(" ");
    if (i === 0) el("circle", Object.assign({ r: 14 }, a), g);
    else if (i === 1) el("polygon", Object.assign({ points: reg(3, 17) }, a), g);
    else if (i === 2) el("rect", Object.assign({ x: -13, y: -13, width: 26, height: 26 }, a), g);
    else if (i === 3) el("polygon", Object.assign({ points: star(5, 17, 7.5) }, a), g);
    else if (i === 4) el("polygon", Object.assign({ points: "0,-17 13,0 0,17 -13,0" }, a), g);
    else el("polygon", Object.assign({ points: reg(6, 15) }, a), g);
    return g;
  }
  function drawMap() {
    for (let k = 1; k < 10; k++) {
      el("line", { x1: k * 46, y1: 0, x2: k * 46, y2: 460, stroke: "#E6E0D2" }, map);
      el("line", { x1: 0, y1: k * 46, x2: 460, y2: k * 46, stroke: "#E6E0D2" }, map);
    }
    item.landmarks.forEach(([x, y], i) => icon(map, i, 20 + x * 420, 20 + y * 420));
  }
  function showQuestion(q) {
    [q.at, q.face, q.to].forEach((id, k) => {
      while (slots[k].firstChild) slots[k].removeChild(slots[k].firstChild);
      icon(slots[k], id, 0, 0);
    });
  }

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (dir) => { cleanup(); resolve({ dir, rt: dir ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => { if (e.repeat || !KEYS[e.key]) return; e.preventDefault(); done(KEYS[e.key]); };
      const onBtn = (e) => done(e.currentTarget.dataset.dir);
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

  ctx.root.querySelector("#pt-start").addEventListener("click", async (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    drawMap();
    qbox.hidden = false;
    for (const q of item.questions) {
      btns.forEach((b) => (b.disabled = true));
      slots.forEach((s) => { while (s.firstChild) s.removeChild(s.firstChild); });
      await wait(400);
      showQuestion(q);
      btns.forEach((b) => (b.disabled = false));
      out.push(await answer(20000));
    }
    btns.forEach((b) => (b.disabled = true));
    ctx.finish(out, false);
  }, { once: true });
};
