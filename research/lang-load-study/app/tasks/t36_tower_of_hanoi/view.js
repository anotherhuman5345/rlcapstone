// Tower of Hanoi: click (or press 1-3 for) the peg to take the top disk from, then the peg to put it on.
// Illegal attempts are blocked on screen but recorded; the server replays every event.
// finish() is called once: when solved, on "give up", or when the item's time limit runs out.
TaskViews["tower_of_hanoi"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const COLORS = ["#f2c94c", "#56a3d9", "#e0735a", "#7cc47f", "#b38ad9"];
  const pegsEl = root.querySelector(".hn-pegs"), info = root.querySelector(".hn-info");
  const board = root.querySelector(".hn-board");
  let state = it.start.slice(), sel = null, t0 = 0, firstMove = null, done = false, locked = false, limitTimer = null, moves = 0;
  const events = [];
  const now = () => Math.round(performance.now() - t0);
  const pegs = [];

  function tops() {
    const t = [null, null, null];
    for (let d = state.length - 1; d >= 0; d--) t[state[d]] = d;
    return t;
  }
  function render() {
    pegs.forEach((p, i) => {
      p.querySelectorAll(".hn-disk").forEach((n) => n.remove());
      const lab = p.querySelector(".hn-lab");
      for (let d = state.length - 1; d >= 0; d--) {
        if (state[d] !== i) continue;
        const disk = document.createElement("div");
        disk.className = "hn-disk" + (sel === i && tops()[i] === d ? " lift" : "");
        disk.style.width = (34 + 22 * d) + "%";
        disk.style.background = COLORS[d % COLORS.length];
        p.insertBefore(disk, lab);
      }
      p.classList.toggle("sel", sel === i);
      p.setAttribute("aria-pressed", sel === i ? "true" : "false");
    });
    info.textContent = tx.moves_label + " " + moves;
  }
  function solved() { return state.every((p, d) => p === it.goal[d]); }
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
    const t = tops();
    if (sel === null) {
      if (t[i] === null) { ctx.status(tx.empty_peg); return; }
      sel = i; ctx.status(""); render(); return;
    }
    if (sel === i) { sel = null; render(); return; }
    const a = sel, ev = { from: a, to: i, t: now() };
    events.push(ev);
    sel = null;
    if (firstMove === null) firstMove = ev.t;   // first attempt, legal or not
    if (t[i] !== null && t[i] < t[a]) { ctx.status(tx.illegal); render(); return; }
    state[t[a]] = i; moves += 1; ctx.status(""); render();
    if (solved()) { ctx.status(tx.solved); locked = true; setTimeout(() => end(false, false), 400); }
  }
  function onKey(e) {
    if (e.repeat || done || locked) return;
    const k = ["1", "2", "3"].indexOf(e.key);
    if (k >= 0) { e.preventDefault(); pick(k); }
    else if (e.key === "Escape" && sel !== null) { sel = null; render(); }
  }

  for (let i = 0; i < 3; i++) {
    const p = document.createElement("button");
    p.type = "button"; p.className = "hn-peg" + (it.goal.every((g) => g === i) ? " goal" : "");
    const lab = document.createElement("span");
    lab.className = "hn-lab";
    lab.append(String(i + 1));
    const g = document.createElement("span");
    g.className = "hn-goal";
    g.textContent = p.classList.contains("goal") ? tx.target : "";
    lab.append(g);
    p.append(lab);
    p.addEventListener("click", () => pick(i));
    pegsEl.append(p); pegs.push(p);
  }

  root.querySelector(".hn-reset").addEventListener("click", () => {
    if (done || locked) return;
    events.push({ reset: true, t: now() });
    state = it.start.slice(); sel = null; moves = 0; ctx.status(""); render();
  });
  root.querySelector(".hn-giveup").addEventListener("click", () => { if (!locked) end(false, true); });
  root.querySelector(".hn-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    board.hidden = false;
    t0 = performance.now();
    render();
    document.addEventListener("keydown", onKey);
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
    pegs[0].focus();
  }, { once: true });
};
