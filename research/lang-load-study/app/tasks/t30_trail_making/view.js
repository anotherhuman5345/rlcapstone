// Trail making: the board appears on Start; click/tap (or Tab + Enter/Space) the circles
// in order. The next correct label comes from item.condition (same rule as logic.py);
// a correct click turns the circle green and draws a line, a wrong one flashes red.
// Ends when every node is connected, or at item.limit_ms (then finish(..., true)).
// Response: {clicks: [{node: index in item.nodes, t: ms since Start}], finished: bool}.
TaskViews["trail_making"] = function (ctx) {
  const it = ctx.item;
  const board = ctx.root.querySelector("#tm-board");
  const lines = ctx.root.querySelector("#tm-lines");
  const btns = [...ctx.root.querySelectorAll("[data-node]")];
  const LETTERS = ["J", "K", "L", "M", "N", "O"];
  const n = it.nodes.length;
  const labels = [];
  for (let i = 0; i < n; i++) {
    labels.push(it.condition === "numbers" ? String(i + 1) : i % 2 === 0 ? String(i / 2 + 1) : LETTERS[(i - 1) / 2]);
  }
  const order = labels.map((lab) => it.nodes.findIndex((d) => d.label === lab));
  const clicks = [];
  let ptr = 0, t0 = 0, over = false, deadline = null;

  function end(timedOut) {
    if (over) return;
    over = true;
    clearTimeout(deadline);
    btns.forEach((b) => (b.disabled = true));
    ctx.status("");
    ctx.finish({ clicks, finished: ptr === n }, timedOut);
  }

  function line(a, b) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
    el.setAttribute("x1", it.nodes[a].x * 1200); el.setAttribute("y1", it.nodes[a].y * 800);
    el.setAttribute("x2", it.nodes[b].x * 1200); el.setAttribute("y2", it.nodes[b].y * 800);
    lines.appendChild(el);
  }

  btns.forEach((b) => b.addEventListener("click", (e) => {
    if (over || !t0) return;
    const node = Number(e.currentTarget.dataset.node);
    if (ptr > 0 && node === order[ptr - 1]) return;  // repeat on the node just connected: ignored
    clicks.push({ node, t: Math.round(performance.now() - t0) });
    if (node === order[ptr]) {
      b.classList.add("done");
      if (ptr > 0) line(order[ptr - 1], node);
      ptr += 1;
      if (ptr === n) end(false);
    } else {
      b.classList.add("bad");
      setTimeout(() => b.classList.remove("bad"), 300);
    }
  }));

  ctx.root.querySelector("#tm-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    board.hidden = false;
    t0 = performance.now();
    deadline = setTimeout(() => end(true), it.limit_ms);
    ctx.status(ctx.text.go);
  }, { once: true });
};
