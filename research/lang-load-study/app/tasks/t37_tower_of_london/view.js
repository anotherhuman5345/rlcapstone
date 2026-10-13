// Tower of London style: click (or press 1-3 for) the peg to take the top ball from, then the peg to put it on.
// Pegs hold 3, 2 and 1 balls. Blocked attempts are recorded; the server replays every event.
// finish() is called once: when solved, on "give up", or when the item's time limit runs out.
TaskViews["tower_of_london"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const BALL = [["#c8423b", "▲"], ["#2f74b5", "■"], ["#3c9a4a", "●"]];
  const caps = it.caps || [3, 2, 1];
  const board = root.querySelector(".tl-board"), info = root.querySelector(".tl-info");
  const copy = (s) => s.map((p) => p.slice());
  let state = copy(it.start), sel = null, t0 = 0, firstMove = null, moves = 0;
  let done = false, locked = false, limitTimer = null;
  const events = [];
  const now = () => Math.round(performance.now() - t0);

  function ball(b, lift) {
    const el = document.createElement("div");
    el.className = "tl-ball" + (lift ? " lift" : "");
    el.style.background = BALL[b][0];
    el.textContent = BALL[b][1];
    return el;
  }
  function drawPegs(container, st, interactive) {
    container.innerHTML = "";
    const els = [];
    for (let i = 0; i < 3; i++) {
      const p = document.createElement(interactive ? "button" : "div");
      p.className = "tl-peg" + (interactive && sel === i ? " sel" : "");
      const lab = document.createElement("span");
      lab.className = "tl-lab"; lab.textContent = String(i + 1);
      p.append(lab);
      for (let k = 0; k < caps[i]; k++) {
        const slot = document.createElement("div");
        slot.className = "tl-slot";
        if (k < st[i].length) slot.append(ball(st[i][k], interactive && sel === i && k === st[i].length - 1));
        p.append(slot);
      }
      if (interactive) {
        p.type = "button";
        p.setAttribute("aria-pressed", sel === i ? "true" : "false");
        p.addEventListener("click", () => pick(i));
      }
      container.append(p); els.push(p);
    }
    return els;
  }
  let pegEls = [];
  function render(focusIdx) {
    pegEls = drawPegs(root.querySelector(".tl-work"), state, true);
    info.textContent = tx.moves_label + " " + moves;
    if (focusIdx !== undefined && pegEls[focusIdx]) pegEls[focusIdx].focus();
  }
  const solved = () => state.every((p, i) => p.length === it.goal[i].length && p.every((b, k) => b === it.goal[i][k]));
  function end(timedOut, gaveUp) {
    if (done) return;
    done = true;
    clearTimeout(limitTimer);
    document.removeEventListener("keydown", onKey);
    root.querySelectorAll("button").forEach((b) => (b.disabled = true));
    ctx.finish({ events, first_move_ms: firstMove, rt_ms: now(), gave_up: !!gaveUp }, !!timedOut);
  }
  function pick(i) {
    if (done || locked) return;
    if (sel === null) {
      if (!state[i].length) { ctx.status(tx.empty_peg); return; }
      sel = i; ctx.status(""); render(i); return;
    }
    if (sel === i) { sel = null; render(i); return; }
    const a = sel, ev = { from: a, to: i, t: now() };
    events.push(ev);
    sel = null;
    if (firstMove === null) firstMove = ev.t;   // first attempt, legal or not
    if (state[i].length >= caps[i]) { ctx.status(tx.full_peg); render(i); return; }
    state[i].push(state[a].pop()); moves += 1; ctx.status(""); render(i);
    if (solved()) { ctx.status(tx.solved); locked = true; setTimeout(() => end(false, false), 400); }
  }
  function onKey(e) {
    if (e.repeat || done || locked) return;
    const k = ["1", "2", "3"].indexOf(e.key);
    if (k >= 0) { e.preventDefault(); pick(k); }
    else if (e.key === "Escape" && sel !== null) { sel = null; render(); }
  }

  drawPegs(root.querySelector(".tl-target"), it.goal, false);
  root.querySelector(".tl-reset").addEventListener("click", () => {
    if (done || locked) return;
    events.push({ reset: true, t: now() });
    state = copy(it.start); sel = null; moves = 0; ctx.status(""); render();
  });
  root.querySelector(".tl-giveup").addEventListener("click", () => { if (!locked) end(false, true); });
  root.querySelector(".tl-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    board.hidden = false;
    t0 = performance.now();
    render(0);
    document.addEventListener("keydown", onKey);
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
  }, { once: true });
};
