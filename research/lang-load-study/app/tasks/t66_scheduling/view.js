// Scheduling: read the rules, then put every job in a person/day cell (one job per cell).
// Click (or Tab + Enter) a job, then a cell; clicking a filled cell picks its job up, and a
// picked-up job dropped on a filled cell swaps the two. "Done" sends assign[job] = [person, day].
// finish() is called once: Done, Give up, or the item's time limit.
TaskViews["scheduling"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const P = it.people, D = it.days, J = it.jobs;
  const jobs = it.job_names.map((k) => tx.jobs[k]);
  const jobLabel = (j) => jobs[j].cap || jobs[j].name;
  const cell = Array.from({ length: P }, () => Array(D).fill(null));   // [person][day] -> job
  let sel = null, t0 = 0, firstMove = null, changes = 0, done = false, limitTimer = null;
  const now = () => Math.round(performance.now() - t0);
  const grid = root.querySelector(".sc-grid"), tray = root.querySelector(".sc-tray");
  const doneBtn = root.querySelector(".sc-done");

  // Fill "{a}", "{a.cap}", "{b}", "{w}", "{day}" from the text file.
  function sentence(r) {
    return tx.templates[r.type].replace(/\{(a|b|w|day)(?:\.(\w+))?\}/g, (m, who, form) => {
      if (who === "w") return tx.people[r.w];
      if (who === "day") return tx.days[r.d];
      const o = jobs[r[who]];
      return (form && o[form]) || o.name;
    });
  }
  function where(j) {
    for (let p = 0; p < P; p++) for (let d = 0; d < D; d++) if (cell[p][d] === j) return [p, d];
    return null;
  }
  function render(focus) {
    grid.innerHTML = ""; tray.innerHTML = "";
    grid.style.gridTemplateColumns = `minmax(4.5rem, auto) repeat(${D}, 1fr)`;
    let focusEl = null;
    grid.append(document.createElement("span"));
    for (let d = 0; d < D; d++) { const h = document.createElement("span"); h.className = "sc-head"; h.textContent = tx.days[d]; grid.append(h); }
    for (let p = 0; p < P; p++) {
      const h = document.createElement("span"); h.className = "sc-head"; h.textContent = tx.people[p]; grid.append(h);
      for (let d = 0; d < D; d++) {
        const j = cell[p][d], b = document.createElement("button");
        b.type = "button";
        b.className = "sc-cell" + (j !== null ? " filled" : "") + (sel && sel.from && sel.from[0] === p && sel.from[1] === d ? " sel" : "");
        b.textContent = j !== null ? jobLabel(j) : "";
        b.setAttribute("aria-label", `${tx.people[p]}, ${tx.days[d]}: ${j !== null ? jobLabel(j) : "—"}`);
        b.addEventListener("click", () => clickCell(p, d));
        grid.append(b);
        if (focus && focus.cell && focus.cell[0] === p && focus.cell[1] === d) focusEl = b;
      }
    }
    for (let j = 0; j < J; j++) {
      if (where(j)) continue;
      const b = document.createElement("button");
      b.type = "button"; b.className = "sc-chip" + (sel && sel.job === j && !sel.from ? " sel" : "");
      b.textContent = jobLabel(j);
      b.addEventListener("click", () => clickChip(j));
      tray.append(b);
      if (focus && focus.job === j) focusEl = b;
    }
    doneBtn.disabled = !Array.from({ length: J }, (_, j) => where(j)).every(Boolean);
    if (focusEl) focusEl.focus();
  }
  function touch() { changes += 1; if (firstMove === null) firstMove = now(); }
  function clickChip(j) {
    if (done) return;
    sel = sel && sel.job === j && !sel.from ? null : { job: j, from: null };
    render({ job: j });
  }
  function clickCell(p, d) {
    if (done) return;
    if (sel === null) {
      if (cell[p][d] !== null) sel = { job: cell[p][d], from: [p, d] };
      render({ cell: [p, d] }); return;
    }
    if (sel.from && sel.from[0] === p && sel.from[1] === d) { sel = null; render({ cell: [p, d] }); return; }
    const here = cell[p][d];
    if (sel.from) cell[sel.from[0]][sel.from[1]] = here;   // swap between cells
    cell[p][d] = sel.job;                                  // a tray job pushes the occupant back to the tray
    sel = null; touch(); render({ cell: [p, d] });
  }
  function end(timedOut, gaveUp) {
    if (done) return;
    done = true;
    clearTimeout(limitTimer);
    root.querySelectorAll("button").forEach((b) => (b.disabled = true));
    const assign = Array.from({ length: J }, (_, j) => where(j));
    ctx.finish({ assign, changes, first_move_ms: firstMove, rt_ms: now(), gave_up: !!gaveUp }, !!timedOut);
  }

  const list = root.querySelector(".sc-rules");
  it.rules.forEach((r) => { const li = document.createElement("li"); li.textContent = sentence(r); list.append(li); });
  doneBtn.addEventListener("click", () => { if (!doneBtn.disabled) end(false, false); });
  root.querySelector(".sc-giveup").addEventListener("click", () => end(false, true));
  root.querySelector(".sc-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    root.querySelector(".sc-area").hidden = false;
    t0 = performance.now();
    render();
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
  }, { once: true });
};
