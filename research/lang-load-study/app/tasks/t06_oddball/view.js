// Visual oddball: 25 symbols, one every item.soa_ms (shown item.on_ms, then blank), scheduled
// with requestAnimationFrame from one start time. Press Space or the big button for the square
// only. A press belongs to the event whose observed onset was item.min_rt..item.max_rt ms
// earlier; only the first press per event counts, others go to "extra". The trial ends
// item.max_rt ms after the last onset. Response: {events: [{rt, late}], extra}.
TaskViews["oddball"] = function (ctx) {
  const it = ctx.item, NS = "http://www.w3.org/2000/svg";
  const svg = ctx.root.querySelector("#ob-stage");
  const btn = ctx.root.querySelector("#ob-press");
  const n = it.events.length;
  const onsets = new Array(n).fill(null);           // observed onsets (performance.now ms)
  const res = it.events.map(() => ({ rt: null, late: null }));
  let extra = 0, t0 = null, over = false;

  const sym = document.createElementNS(NS, "g");
  svg.appendChild(sym);
  const side = 56, rad = side / Math.sqrt(Math.PI);  // square and circle of equal area
  let current;
  function show(kind) {
    if (kind === current) return;   // redraw only when the symbol changes
    current = kind;
    while (sym.firstChild) sym.removeChild(sym.firstChild);
    if (!kind) return;
    const e = document.createElementNS(NS, kind === "square" ? "rect" : "circle");
    if (kind === "square") { e.setAttribute("x", 150 - side / 2); e.setAttribute("y", 100 - side / 2); e.setAttribute("width", side); e.setAttribute("height", side); }
    else { e.setAttribute("cx", 150); e.setAttribute("cy", 100); e.setAttribute("r", rad); }
    e.setAttribute("fill", it.colour);
    sym.appendChild(e);
  }
  function plus() {
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", 150); t.setAttribute("y", 110); t.setAttribute("text-anchor", "middle");
    t.setAttribute("font-size", 30); t.setAttribute("fill", "#5E6C78");
    t.textContent = "+";
    sym.appendChild(t);
  }

  function press() {
    if (over || t0 === null) return;
    const now = performance.now();
    for (let i = n - 1; i >= 0; i--) {
      if (onsets[i] === null) continue;
      const rt = now - onsets[i];
      if (rt >= it.min_rt && rt < it.max_rt) {
        if (res[i].rt === null) { res[i].rt = Math.round(rt); return; }
        break;
      }
      if (rt >= it.max_rt) break;
    }
    extra++;
  }
  const onKey = (e) => {
    if (e.key !== " " && e.code !== "Space") return;
    e.preventDefault();
    if (e.repeat) return;
    press();
  };
  const onBtn = (e) => { e.preventDefault(); press(); };

  function finishTrial() {
    if (over) return;
    over = true;
    document.removeEventListener("keydown", onKey);
    btn.removeEventListener("pointerdown", onBtn);
    btn.disabled = true;
    show(null);
    ctx.finish({ events: res, extra }, false);
  }

  function tick(now) {
    if (over) return;
    const el = now - t0;
    const i = Math.floor(el / it.soa_ms);
    if (i >= n) {
      if (el >= (n - 1) * it.soa_ms + it.max_rt) { finishTrial(); return; }
      show(null);
    } else {
      if (onsets[i] === null) {
        onsets[i] = now;
        res[i].late = Math.round(el - i * it.soa_ms);
      }
      show(el - i * it.soa_ms < it.on_ms ? it.events[i] : null);
    }
    requestAnimationFrame(tick);
  }

  function fixation() {
    current = "+";
    while (sym.firstChild) sym.removeChild(sym.firstChild);
    plus();
  }
  fixation();
  ctx.root.querySelector("#ob-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    e.currentTarget.blur();
    btn.disabled = false;
    // pointerdown (not click) so touch/mouse presses register at once; keyboard uses Space only.
    btn.addEventListener("pointerdown", onBtn);
    document.addEventListener("keydown", onKey);
    show(null);
    fixation();
    setTimeout(() => requestAnimationFrame((now) => { t0 = now; tick(now); }), 1000);
  }, { once: true });
};
