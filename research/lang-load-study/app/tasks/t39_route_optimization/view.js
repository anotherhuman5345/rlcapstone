// Route optimization: after Start, tap stops (or type their numbers) in visiting order;
// Undo / Backspace removes the last one, Clear empties the route, Done / Enter sends it
// (only once every stop is chosen). After 100 s the route so far is sent as timed out.
// Response: {order: [0-based stop indices], undos, plan_ms, rt}.
TaskViews["route_optimization"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const item = ctx.item, n = item.stops.length;
  const map = ctx.root.querySelector("#ro-map");
  const undoB = ctx.root.querySelector("#ro-undo");
  const clearB = ctx.root.querySelector("#ro-clear");
  const doneB = ctx.root.querySelector("#ro-done");
  const OFF = 20;
  const order = [];
  let undos = 0, planMs = null, t0 = 0, done = false, timer = null, line = null, back = null;
  const marks = [];
  [undoB, clearB, doneB].forEach((b) => (b.disabled = true));

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const P = (p) => [p[0] + OFF, p[1] + OFF];

  function draw() {
    line = el("polyline", { fill: "none", stroke: "#1F6E8C", "stroke-width": 8, "stroke-linejoin": "round" }, map);
    back = el("line", { stroke: "#1F6E8C", "stroke-width": 8, "stroke-dasharray": "18 14", visibility: "hidden" }, map);
    const [dx, dy] = P(item.depot);
    el("rect", { x: dx - 30, y: dy - 30, width: 60, height: 60, rx: 6, fill: "#1D2731" }, map);
    item.stops.forEach((s, i) => {
      const [x, y] = P(s);
      const g = el("g", { style: "cursor:pointer" }, map);
      const c = el("circle", { cx: x, cy: y, r: 36, fill: "#FFFFFF", stroke: "#1D2731", "stroke-width": 5 }, g);
      el("text", { x, y: y + 13, "text-anchor": "middle", "font-size": 38, "font-weight": 700, fill: "#1D2731" }, g).textContent = String(i + 1);
      el("circle", { cx: x, cy: y, r: 60, fill: "transparent" }, g); // larger touch target
      g.addEventListener("click", () => add(i));
      marks.push(c);
    });
    update();
  }
  function update() {
    const pts = [P(item.depot), ...order.map((i) => P(item.stops[i]))];
    line.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
    const complete = order.length === n;
    if (complete) {
      const [a, b] = [pts[pts.length - 1], pts[0]];
      back.setAttribute("x1", a[0]); back.setAttribute("y1", a[1]);
      back.setAttribute("x2", b[0]); back.setAttribute("y2", b[1]);
    }
    back.setAttribute("visibility", complete ? "visible" : "hidden");
    marks.forEach((c, i) => c.setAttribute("fill", order.includes(i) ? "#C9DCEA" : "#FFFFFF"));
    undoB.disabled = clearB.disabled = order.length === 0;
    doneB.disabled = !complete;
  }

  function add(i) {
    if (done || order.includes(i)) return;
    if (planMs === null) planMs = Math.round(performance.now() - t0);
    order.push(i);
    update();
  }
  function undo() { if (!done && order.length) { order.pop(); undos += 1; update(); } }
  function clear() { if (!done && order.length) { order.length = 0; undos += 1; update(); } }
  function onKey(e) {
    if (e.repeat) return;
    const k = Number(e.key);
    if (e.key.length === 1 && Number.isInteger(k) && k >= 1 && k <= n) { e.preventDefault(); add(k - 1); }
    else if (e.key === "Backspace") { e.preventDefault(); undo(); }
    else if (e.key === "Enter" && order.length === n) { e.preventDefault(); end(false); }
  }
  function end(timedOut) {
    if (done) return;
    done = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", onKey);
    [undoB, clearB, doneB].forEach((b) => (b.disabled = true));
    ctx.finish({ order: order.slice(), undos, plan_ms: planMs, rt: Math.round(performance.now() - t0) }, timedOut);
  }

  undoB.addEventListener("click", undo);
  clearB.addEventListener("click", clear);
  doneB.addEventListener("click", () => { if (order.length === n) end(false); });
  ctx.root.querySelector("#ro-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none"; // the site CSS gives buttons display:inline-block, which beats [hidden]
    draw();
    map.style.visibility = "visible";
    document.addEventListener("keydown", onKey);
    t0 = performance.now();
    timer = setTimeout(() => end(true), 100000);
  }, { once: true });
};
