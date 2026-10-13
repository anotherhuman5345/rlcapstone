// Change blindness (flicker): 3 scenes. Scene A item.scene_ms, blank item.blank_ms, scene B,
// blank, ... (requestAnimationFrame timing) until the person clicks/taps the changed object or
// item.limit_ms passes. Keyboard: arrow keys move a crosshair (Shift = bigger steps), Enter or
// Space clicks at the crosshair; on-screen arrow buttons do the same. Every click is recorded
// as {x, y} in fractions of the scene size plus t (ms from flicker start); the server re-checks
// which click (if any) hit the changed object. Response per scene: {clicks: [...]}.
TaskViews["change_blindness"] = function (ctx) {
  const it = ctx.item, T = ctx.text, NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#cb-stage");
  const keysRow = ctx.root.querySelector("#cb-keys");
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fmt = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => (k in v ? v[k] : ""));

  function mk(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    (parent || svg).appendChild(e);
    return e;
  }
  function poly(n, r, start, inner) {
    const pts = [];
    for (let i = 0; i < n; i++) {
      const a = start + (i * 2 * Math.PI) / n;
      const rr = inner && i % 2 ? inner : r;
      pts.push((rr * Math.cos(a)).toFixed(1) + "," + (rr * Math.sin(a)).toFixed(1));
    }
    return pts.join(" ");
  }
  function shape(o, parent) {
    const g = mk("g", { transform: `translate(${o.x},${o.y}) rotate(${o.rot})` }, parent);
    const h = o.s / 2, a = { fill: o.c, stroke: "#2C3E50", "stroke-width": 2 };
    if (o.shape === "circle") mk("circle", { r: h, ...a }, g);
    else if (o.shape === "square") mk("rect", { x: -h * 0.85, y: -h * 0.85, width: h * 1.7, height: h * 1.7, ...a }, g);
    else if (o.shape === "triangle") mk("polygon", { points: poly(3, h, -Math.PI / 2), ...a }, g);
    else if (o.shape === "diamond") mk("polygon", { points: poly(4, h, -Math.PI / 2), ...a }, g);
    else if (o.shape === "star") mk("polygon", { points: poly(10, h, -Math.PI / 2, h * 0.45), ...a }, g);
    else mk("polygon", { points: poly(6, h, 0), ...a }, g);
  }
  // The changed object, computed the same way as logic.changed_object (used only to stop the flicker).
  function changedObject(sc) {
    const b = new Map(sc.b.map((o) => [o.id, o]));
    const d = sc.a.filter((o) => !b.has(o.id) || Object.keys(o).some((k) => o[k] !== b.get(o.id)[k]));
    return d.length === 1 ? d[0] : null;
  }
  function toSvg(e) {
    const m = svg.getScreenCTM();
    if (!m) return null;
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return { x: p.x, y: p.y };
  }

  function runScene(sc) {
    return new Promise((resolve) => {
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      mk("rect", { x: 0, y: 0, width: it.w, height: it.h, fill: sc.bg });
      const gA = mk("g", {}), gB = mk("g", {});
      sc.a.forEach((o) => shape(o, gA));
      sc.b.forEach((o) => shape(o, gB));
      const marks = mk("g", { "pointer-events": "none" });
      const cur = { x: it.w / 2, y: it.h / 2 };
      const cross = mk("g", { "pointer-events": "none", visibility: "hidden" });
      mk("circle", { r: 14, fill: "none", stroke: "#000", "stroke-width": 3 }, cross);
      mk("circle", { r: 14, fill: "none", stroke: "#fff", "stroke-width": 1.2 }, cross);
      mk("path", { d: "M-22 0H-8M8 0H22M0 -22V-8M0 8V22", stroke: "#000", "stroke-width": 3 }, cross);
      const moveCross = () => cross.setAttribute("transform", `translate(${cur.x},${cur.y})`);
      moveCross();
      gA.style.display = "none"; gB.style.display = "none";

      const tgt = changedObject(sc);
      const rad = tgt ? tgt.s * it.hit_scale + it.hit_pad : 0;
      const clicks = [];
      let t0 = null, over = false;
      const cycle = 2 * (it.scene_ms + it.blank_ms);

      function tick(now) {
        if (over) return;
        if (t0 === null) t0 = now;
        const el = now - t0;
        if (el >= it.limit_ms) { end(); return; }
        const ph = el % cycle;
        const showA = ph < it.scene_ms;
        const showB = ph >= it.scene_ms + it.blank_ms && ph < 2 * it.scene_ms + it.blank_ms;
        gA.style.display = showA ? "" : "none";
        gB.style.display = showB ? "" : "none";
        requestAnimationFrame(tick);
      }
      function clickAt(x, y) {
        if (over || t0 === null) return;
        const t = Math.round(performance.now() - t0);
        clicks.push({ x: +(x / it.w).toFixed(4), y: +(y / it.h).toFixed(4), t });
        const m = mk("circle", { cx: x, cy: y, r: 10, fill: "none", stroke: "#000", "stroke-width": 2 }, marks);
        setTimeout(() => m.remove(), 300);
        if (tgt && Math.hypot(x - tgt.x, y - tgt.y) <= rad) end();
      }
      const onPtr = (e) => { const p = toSvg(e); if (p) clickAt(p.x, p.y); };
      const step = (dx, dy, big) => {
        const d = big ? 60 : 20;
        cur.x = Math.max(0, Math.min(it.w, cur.x + dx * d));
        cur.y = Math.max(0, Math.min(it.h, cur.y + dy * d));
        cross.setAttribute("visibility", "visible");
        moveCross();
      };
      const onKey = (e) => {
        const dirs = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        if (dirs[e.key]) { e.preventDefault(); step(dirs[e.key][0], dirs[e.key][1], e.shiftKey); return; }
        if (e.repeat) return;
        // Enter/Space on a focused on-screen button is left to that button.
        if ((e.key === "Enter" || e.key === " ") && e.target.closest && e.target.closest("button")) return;
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); cross.setAttribute("visibility", "visible"); clickAt(cur.x, cur.y); }
      };
      const moveBtns = [...keysRow.querySelectorAll("[data-move]")];
      const pickBtn = keysRow.querySelector("#cb-pick");
      const onMove = (e) => { const [dx, dy] = e.currentTarget.dataset.move.split(",").map(Number); step(dx, dy, false); };
      const onPick = () => { cross.setAttribute("visibility", "visible"); clickAt(cur.x, cur.y); };
      function end() {
        if (over) return;
        over = true;
        svg.removeEventListener("pointerdown", onPtr);
        document.removeEventListener("keydown", onKey);
        moveBtns.forEach((b) => b.removeEventListener("click", onMove));
        pickBtn.removeEventListener("click", onPick);
        gA.style.display = "none"; gB.style.display = "none";
        cross.setAttribute("visibility", "hidden");
        resolve({ clicks });
      }
      svg.addEventListener("pointerdown", onPtr);
      document.addEventListener("keydown", onKey);
      moveBtns.forEach((b) => b.addEventListener("click", onMove));
      pickBtn.addEventListener("click", onPick);
      requestAnimationFrame(tick);
    });
  }

  ctx.root.querySelector("#cb-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    keysRow.hidden = false;
    for (let i = 0; i < it.scenes.length; i++) {
      ctx.status(fmt(T.scene, { n: i + 1, total: it.scenes.length }));
      out.push(await runScene(it.scenes[i]));
      ctx.status("");
      await wait(800);
    }
    keysRow.hidden = true;
    ctx.finish(out, false);
  }, { once: true });
};
