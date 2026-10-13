// Packing: choose a piece (click it or press its number), turn it with "Turn" (or R), then click
// (or press Enter on) the board cell where the piece's dot should go. Clicking a placed piece
// with nothing chosen takes it back. Arrow keys move between board cells. Every placement
// attempt and removal is recorded; the server replays them. Geometry matches logic.py:
// one turn = 90 degrees clockwise, (r, c) -> (c, -r), shift to 0, sort row-major; anchor = first cell.
// finish() is called once: board full, "give up", or the item's time limit.
TaskViews["packing"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root, R = it.rows, C = it.cols;
  const COLORS = ["#f2c94c", "#56a3d9", "#e0735a", "#7cc47f", "#b38ad9", "#f29bc0"];
  const boardEl = root.querySelector(".pk-board"), tray = root.querySelector(".pk-tray");
  const rot = it.pieces.map(() => 0), where = it.pieces.map(() => null);
  const occ = Array.from({ length: R }, () => Array(C).fill(-1));
  let sel = null, t0 = 0, firstMove = null, done = false, locked = false, limitTimer = null, hover = null;
  const events = [];
  const now = () => Math.round(performance.now() - t0);
  const cells = [], pieceBtns = [];

  function shape(i) {
    let s = it.pieces[i].map(([r, c]) => [r, c]);
    for (let k = 0; k < rot[i] % 4; k++) s = s.map(([r, c]) => [c, -r]);
    const r0 = Math.min(...s.map((p) => p[0])), c0 = Math.min(...s.map((p) => p[1]));
    s = s.map(([r, c]) => [r - r0, c - c0]);
    s.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return s;
  }
  function footprint(i, row, col) {
    const s = shape(i), [ar, ac] = s[0];
    return s.map(([r, c]) => [row + r - ar, col + c - ac]);
  }
  const fits = (fp) => fp.every(([r, c]) => r >= 0 && r < R && c >= 0 && c < C && occ[r][c] === -1);

  function drawTray() {
    pieceBtns.forEach((b, i) => {
      const s = shape(i), h = Math.max(...s.map((p) => p[0])) + 1, w = Math.max(...s.map((p) => p[1])) + 1;
      const mini = b.querySelector(".pk-mini");
      mini.innerHTML = "";
      mini.style.gridTemplateColumns = `repeat(${w}, 1.2rem)`;
      for (let r = 0; r < h; r++) for (let c = 0; c < w; c++) {
        const k = s.findIndex((p) => p[0] === r && p[1] === c);
        const sq = document.createElement("span");
        if (k >= 0) { sq.style.background = COLORS[i % COLORS.length]; if (k === 0) sq.className = "anchor"; }
        mini.append(sq);
      }
      b.classList.toggle("sel", sel === i);
      b.classList.toggle("used", where[i] !== null);
      b.setAttribute("aria-pressed", sel === i ? "true" : "false");
    });
  }
  function drawBoard() {
    const fp = sel !== null && hover ? footprint(sel, hover[0], hover[1]) : [];
    const good = fp.length && fits(fp);
    for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
      const el = cells[r][c], p = occ[r][c];
      el.style.background = p >= 0 ? COLORS[p % COLORS.length] : "";
      const inFp = fp.some(([fr, fc]) => fr === r && fc === c);
      el.classList.toggle("ok", inFp && good);
      el.classList.toggle("bad", inFp && !good);
    }
  }
  function render() { drawTray(); drawBoard(); }
  function end(timedOut, gaveUp) {
    if (done) return;
    done = true;
    clearTimeout(limitTimer);
    document.removeEventListener("keydown", onKey);
    root.querySelectorAll("button").forEach((b) => (b.disabled = true));
    ctx.finish({ events, first_move_ms: firstMove, rt_ms: now(), gave_up: !!gaveUp }, !!timedOut);
  }
  function choose(i) {
    if (done || locked || i < 0 || i >= it.pieces.length || where[i] !== null) return;
    sel = sel === i ? null : i; ctx.status(""); render();
  }
  function rotate() {
    if (done || locked) return;
    if (sel === null) { ctx.status(tx.choose_first); return; }
    rot[sel] = (rot[sel] + 1) % 4; render();
  }
  function cellAction(r, c) {
    if (done || locked) return;
    if (sel === null) {
      const p = occ[r][c];
      if (p < 0) { ctx.status(tx.choose_first); return; }
      events.push({ op: "remove", piece: p, t: now() });
      where[p].forEach(([rr, cc]) => (occ[rr][cc] = -1));
      where[p] = null; sel = p; ctx.status(""); render(); return;
    }
    const fp = footprint(sel, r, c);
    const ev = { op: "place", piece: sel, rot: rot[sel], row: r, col: c, t: now() };
    events.push(ev);
    if (firstMove === null) firstMove = ev.t;
    if (!fits(fp)) { ctx.status(tx.no_fit); render(); return; }
    fp.forEach(([rr, cc]) => (occ[rr][cc] = sel));
    where[sel] = fp; sel = null; ctx.status(""); render();
    if (where.every((w) => w !== null)) { ctx.status(tx.solved); locked = true; setTimeout(() => end(false, false), 400); }
  }
  function onKey(e) {
    if (e.repeat || done || locked) return;
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= it.pieces.length) { e.preventDefault(); choose(n - 1); return; }
    if (e.key === "r" || e.key === "R") { e.preventDefault(); rotate(); return; }
    if (e.key === "Escape") { sel = null; render(); return; }
    const a = document.activeElement;
    if (a && a.dataset && a.dataset.r !== undefined && e.key.startsWith("Arrow")) {
      e.preventDefault();
      let r = +a.dataset.r, c = +a.dataset.c;
      if (e.key === "ArrowUp") r = Math.max(0, r - 1);
      if (e.key === "ArrowDown") r = Math.min(R - 1, r + 1);
      if (e.key === "ArrowLeft") c = Math.max(0, c - 1);
      if (e.key === "ArrowRight") c = Math.min(C - 1, c + 1);
      cells[r][c].focus();
    }
  }

  boardEl.style.gridTemplateColumns = `repeat(${C}, auto)`;
  for (let r = 0; r < R; r++) {
    cells.push([]);
    for (let c = 0; c < C; c++) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "pk-cell"; b.dataset.r = r; b.dataset.c = c;
      b.setAttribute("aria-label", `${r + 1},${c + 1}`);
      b.addEventListener("click", () => cellAction(r, c));
      const enter = () => { hover = [r, c]; drawBoard(); };
      b.addEventListener("mouseenter", enter);
      b.addEventListener("focus", enter);
      b.addEventListener("mouseleave", () => { hover = null; drawBoard(); });
      boardEl.append(b); cells[r].push(b);
    }
  }
  it.pieces.forEach((_, i) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "pk-piece";
    const mini = document.createElement("div"); mini.className = "pk-mini";
    const lab = document.createElement("span"); lab.textContent = String(i + 1);
    b.append(mini, lab);
    b.addEventListener("click", () => choose(i));
    tray.append(b); pieceBtns.push(b);
  });
  root.querySelector(".pk-rotate").addEventListener("click", rotate);
  root.querySelector(".pk-giveup").addEventListener("click", () => { if (!locked) end(false, true); });
  root.querySelector(".pk-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    root.querySelector(".pk-area").hidden = false;
    t0 = performance.now();
    render();
    document.addEventListener("keydown", onKey);
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
  }, { once: true });
};
