// Maze: after Start the maze appears; every move attempt (arrow key, arrow button, or tap
// on a neighbouring cell) is logged with its time, including bumps into walls. Reaching
// the exit ends the trial; after 120 s the moves so far are sent as timed out.
// Response: {moves: [{d: "U"|"R"|"D"|"L", t: ms since Start}], reached}.
TaskViews["maze"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const item = ctx.item, n = item.size;
  const board = ctx.root.querySelector("#mz-board");
  const btns = [...ctx.root.querySelectorAll("[data-d]")];
  const DIRS = { U: [-1, 0, 1], R: [0, 1, 2], D: [1, 0, 4], L: [0, -1, 8] };
  const KEYS = { ArrowUp: "U", ArrowRight: "R", ArrowDown: "D", ArrowLeft: "L" };
  const PAD = 20, C = 400 / n;
  const moves = [];
  let pos = item.start.slice(), t0 = 0, done = false, timer = null, dot = null, trail = null;
  const visited = [pos.slice()];
  btns.forEach((b) => (b.disabled = true));

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const cx = (c) => PAD + (c + 0.5) * C, cy = (r) => PAD + (r + 0.5) * C;

  function draw() {
    el("rect", { x: PAD + item.exit[1] * C + 2, y: PAD + item.exit[0] * C + 2, width: C - 4, height: C - 4, fill: "#BFE3C6" }, board);
    el("rect", { x: PAD + item.start[1] * C + 2, y: PAD + item.start[0] * C + 2, width: C - 4, height: C - 4, fill: "#E3ECF3" }, board);
    let d = "";
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const o = item.open[r * n + c], x = PAD + c * C, y = PAD + r * C;
        if (!(o & 1)) d += `M${x} ${y}h${C}`;
        if (!(o & 8)) d += `M${x} ${y}v${C}`;
        if (r === n - 1 && !(o & 4)) d += `M${x} ${y + C}h${C}`;
        if (c === n - 1 && !(o & 2)) d += `M${x + C} ${y}v${C}`;
      }
    }
    el("path", { d, stroke: "#1D2731", "stroke-width": 3, "stroke-linecap": "square", fill: "none" }, board);
    trail = el("polyline", { fill: "none", stroke: "#9AB8CF", "stroke-width": Math.max(3, C / 6), "stroke-linejoin": "round", "stroke-linecap": "round" }, board);
    dot = el("circle", { r: C * 0.32, fill: "#1F6E8C" }, board);
    // Transparent cells on top catch taps on neighbouring squares.
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const hit = el("rect", { x: PAD + c * C, y: PAD + r * C, width: C, height: C, fill: "transparent" }, board);
        hit.addEventListener("click", () => {
          const dr = r - pos[0], dc = c - pos[1];
          const d = Object.keys(DIRS).find((k) => DIRS[k][0] === dr && DIRS[k][1] === dc);
          if (d) move(d);
        });
      }
    }
    place();
  }
  function place() {
    dot.setAttribute("cx", cx(pos[1]));
    dot.setAttribute("cy", cy(pos[0]));
    trail.setAttribute("points", visited.map(([r, c]) => `${cx(c)},${cy(r)}`).join(" "));
  }

  function move(d) {
    if (done) return;
    moves.push({ d, t: Math.round(performance.now() - t0) });
    const [dr, dc, bit] = DIRS[d];
    if (item.open[pos[0] * n + pos[1]] & bit) {
      pos = [pos[0] + dr, pos[1] + dc];
      visited.push(pos.slice());
      place();
    }
    if (pos[0] === item.exit[0] && pos[1] === item.exit[1]) end(false);
  }
  function onKey(e) {
    if (e.repeat || !KEYS[e.key]) return;
    e.preventDefault();
    move(KEYS[e.key]);
  }
  function onBtn(e) { move(e.currentTarget.dataset.d); }
  function end(timedOut) {
    if (done) return;
    done = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", onKey);
    btns.forEach((b) => { b.removeEventListener("click", onBtn); b.disabled = true; });
    const reached = pos[0] === item.exit[0] && pos[1] === item.exit[1];
    ctx.finish({ moves, reached }, timedOut);
  }

  ctx.root.querySelector("#mz-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    draw();
    board.style.visibility = "visible";
    btns.forEach((b) => { b.disabled = false; b.addEventListener("click", onBtn); });
    document.addEventListener("keydown", onKey);
    t0 = performance.now();
    timer = setTimeout(() => end(true), 120000);
  }, { once: true });
};
