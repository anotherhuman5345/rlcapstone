// Sliding tiles: click a tile next to the gap, or press an arrow key / arrow button to move a tile
// into the gap in that direction. Every press is recorded (as the tile it targets, 0 = none);
// the server replays them. finish() is called once: solved, "give up", or the item's time limit.
TaskViews["sliding_tile"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root, N = it.size || 3;
  const board = root.querySelector(".sl-board"), info = root.querySelector(".sl-info");
  const work = root.querySelector(".sl-work");
  let state = it.start.slice(), t0 = 0, firstMove = null, moves = 0;
  let done = false, locked = false, limitTimer = null;
  const events = [];
  const now = () => Math.round(performance.now() - t0);

  function draw(container, st, interactive) {
    container.innerHTML = "";
    st.forEach((tile) => {
      let el;
      if (tile === 0) { el = document.createElement("div"); el.className = "sl-cell sl-gap"; }
      else {
        el = document.createElement(interactive ? "button" : "div");
        el.className = "sl-cell";
        el.textContent = String(tile);
        if (interactive) { el.type = "button"; el.dataset.tile = tile; el.addEventListener("click", () => press(tile)); }
      }
      container.append(el);
    });
  }
  function render(focusTile) {
    draw(work, state, true);
    info.textContent = tx.moves_label + " " + moves;
    if (focusTile) { const b = work.querySelector(`[data-tile="${focusTile}"]`); if (b) b.focus(); }
  }
  const adjacent = (tile) => {
    const z = state.indexOf(0), t = state.indexOf(tile);
    return Math.abs(Math.floor(z / N) - Math.floor(t / N)) + Math.abs((z % N) - (t % N)) === 1;
  };
  const solved = () => state.every((v, i) => v === it.goal[i]);
  function end(timedOut, gaveUp) {
    if (done) return;
    done = true;
    clearTimeout(limitTimer);
    document.removeEventListener("keydown", onKey);
    root.querySelectorAll("button").forEach((b) => (b.disabled = true));
    ctx.finish({ events, first_move_ms: firstMove, rt_ms: now(), gave_up: !!gaveUp }, !!timedOut);
  }
  function press(tile, keepFocus) {
    if (done || locked) return;
    const ev = { tile, t: now() };
    events.push(ev);
    if (firstMove === null) firstMove = ev.t;   // first attempt, legal or not
    if (!tile || !adjacent(tile)) { ctx.status(tx.illegal); return; }
    const z = state.indexOf(0), t = state.indexOf(tile);
    state[z] = tile; state[t] = 0; moves += 1; ctx.status("");
    render(keepFocus ? null : tile);
    if (solved()) { ctx.status(tx.solved); locked = true; setTimeout(() => end(false, false), 400); }
  }
  // An arrow moves the tile that sits on the opposite side of the gap in that direction.
  function tileFor(dir) {
    const z = state.indexOf(0), r = Math.floor(z / N), c = z % N;
    const from = { ArrowUp: [r + 1, c], ArrowDown: [r - 1, c], ArrowLeft: [r, c + 1], ArrowRight: [r, c - 1] }[dir];
    if (!from || from[0] < 0 || from[0] >= N || from[1] < 0 || from[1] >= N) return 0;
    return state[from[0] * N + from[1]];
  }
  function onKey(e) {
    if (e.repeat || done || locked) return;
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) { e.preventDefault(); press(tileFor(e.key), true); }
  }

  draw(root.querySelector(".sl-target"), it.goal, false);
  root.querySelectorAll("[data-dir]").forEach((b) => b.addEventListener("click", () => press(tileFor(b.dataset.dir), true)));
  root.querySelector(".sl-reset").addEventListener("click", () => {
    if (done || locked) return;
    events.push({ reset: true, t: now() });
    state = it.start.slice(); moves = 0; ctx.status(""); render();
  });
  root.querySelector(".sl-giveup").addEventListener("click", () => { if (!locked) end(false, true); });
  root.querySelector(".sl-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    board.hidden = false;
    t0 = performance.now();
    render();
    document.addEventListener("keydown", onKey);
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
  }, { once: true });
};
