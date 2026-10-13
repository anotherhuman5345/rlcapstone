// Novel interface learning: 3 goals on a made-up device. The browser runs the same state
// machine as logic.step() to show the lamps; the server replays the presses independently.
// Controls: click/tap, Tab+Enter, or keys 1-6 (screen position). Goal 1 shows a legend;
// goals 2-3 do not. A goal ends on a confirm outside edit mode, or after max_actions presses.
// Response: {goals: [{actions: [function id], times: [ms from goal start]}]}.
TaskViews["novel_interface"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, tx = ctx.text;
  const LEFT = 0, RIGHT = 1, EDIT = 2, CYCLE = 3, CLEAR = 4, OK = 5;
  const COLORS = ["#4a5560", "#d64541", "#f2c94c", "#3b82d6"];
  const S = 'fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"';
  const GLYPHS = [
    '<circle cx="20" cy="20" r="14" ' + S + '/><circle cx="20" cy="20" r="6" ' + S + "/>",
    '<polyline points="6,28 13,12 20,28 27,12 34,28" ' + S + "/>",
    '<g fill="currentColor"><circle cx="10" cy="30" r="3.5"/><circle cx="20" cy="20" r="3.5"/><circle cx="30" cy="10" r="3.5"/></g>',
    '<polygon points="10,8 30,8 10,32 30,32" ' + S + "/>",
    '<rect x="8" y="8" width="24" height="24" ' + S + '/><line x1="8" y1="32" x2="32" y2="8" ' + S + "/>",
    '<path d="M5 20 Q12.5 6 20 20 T35 20" ' + S + "/>",
    '<circle cx="20" cy="20" r="14" ' + S + '/><path d="M20 6 A14 14 0 0 1 20 34 Z" fill="currentColor"/>',
    '<line x1="8" y1="12" x2="32" y2="12" ' + S + '/><line x1="8" y1="20" x2="24" y2="20" ' + S + '/><line x1="8" y1="28" x2="16" y2="28" ' + S + "/>",
    '<polygon points="20,7 33,31 7,31" ' + S + '/><circle cx="20" cy="23" r="3" fill="currentColor"/>',
    '<rect x="5" y="14" width="12" height="12" ' + S + '/><circle cx="28" cy="20" r="6" ' + S + "/>",
  ];
  const svg = (g) => '<svg viewBox="0 0 40 40" aria-hidden="true">' + GLYPHS[g] + "</svg>";

  const lampEls = [...ctx.root.querySelectorAll(".lamp")];
  const markEls = [...ctx.root.querySelectorAll(".nif-mark")];
  const out = { goals: [] };
  let gi = -1, state = null, rec = null, goalT0 = 0, active = false, ended = false;
  const timers = [];

  // Controls in screen order; each position has a glyph and a hidden function.
  const ctrls = $("#ni-ctrls");
  it.funcs.forEach((f, pos) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "ctrl";
    b.innerHTML = svg(it.glyphs[pos]) + '<span class="n">' + (pos + 1) + "</span>";
    b.addEventListener("click", () => press(pos));
    ctrls.appendChild(b);
  });
  const legend = $("#ni-legend-list");
  it.funcs.forEach((f, pos) => {
    const li = document.createElement("li");
    li.innerHTML = svg(it.glyphs[pos]);
    li.appendChild(document.createTextNode(tx.funcs[f]));
    legend.appendChild(li);
  });

  function step(s, a) {   // mirror of logic.step
    const c = s.colors.slice();
    if (a === LEFT && !s.edit) return [{ ...s, cur: (s.cur + 2) % 3 }, false];
    if (a === RIGHT && !s.edit) return [{ ...s, cur: (s.cur + 1) % 3 }, false];
    if (a === EDIT) return [{ ...s, edit: !s.edit }, false];
    if (a === CYCLE && s.edit) { c[s.cur] = (c[s.cur] + 1) % 4; return [{ ...s, colors: c }, false]; }
    if (a === CLEAR) return [{ ...s, colors: [0, 0, 0] }, false];
    if (a === OK && !s.edit) return [s, true];
    return [s, false];
  }
  function render() {
    lampEls.forEach((el, k) => { el.style.background = COLORS[state.colors[k]]; });
    markEls.forEach((el, k) => el.classList.toggle("on", k === state.cur));
    $("#ni-lamps").classList.toggle("edit", state.edit);
  }

  function startGoal(k) {
    gi = k;
    const g = it.goals[k];
    state = { colors: g.start.slice(), cur: 0, edit: false };
    rec = { actions: [], times: [] };
    out.goals.push(rec);
    $("#ni-label").textContent = tx.goal_label.replace("{n}", k + 1).replace("{total}", it.goals.length);
    $("#ni-goal").textContent = tx.goal.replace("{l}", tx.colors[g.target[0]])
      .replace("{m}", tx.colors[g.target[1]]).replace("{r}", tx.colors[g.target[2]]);
    $("#ni-legend").hidden = k !== 0;
    $("#ni-work").hidden = false;
    render();
    active = true;
    goalT0 = performance.now();
  }

  function press(pos) {
    if (!active || ended) return;
    const a = it.funcs[pos];
    rec.actions.push(a);
    rec.times.push(Math.round(performance.now() - goalT0));
    const [n, done] = step(state, a);
    state = n;
    render();
    if (done || rec.actions.length >= it.max_actions) goalDone();
  }

  function goalDone() {
    active = false;
    if (gi + 1 >= it.goals.length) { end(false); return; }
    if (document.activeElement) document.activeElement.blur();
    $("#ni-work").hidden = true;
    $("#ni-goal").textContent = tx.next_goal;
    timers.push(setTimeout(() => startGoal(gi + 1), 1200));
  }

  const onKey = (e) => {
    if (e.repeat || !active) return;
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= it.funcs.length) press(n - 1);
  };

  $("#ni-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", onKey);
    timers.push(setTimeout(() => end(true), it.limit_ms));
    startGoal(0);
  }, { once: true });

  function end(timedOut) {
    if (ended) return;
    ended = true;
    active = false;
    timers.forEach(clearTimeout);
    document.removeEventListener("keydown", onKey);
    ctx.root.querySelectorAll(".ctrl").forEach((b) => { b.disabled = true; });
    ctx.finish(out, timedOut);
  }
};
