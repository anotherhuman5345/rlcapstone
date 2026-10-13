// Constraint satisfaction: read the sentences, then put every animal in a place.
// Click (or Tab + Enter) an animal, then a place; clicking a filled place picks its animal up,
// and a picked-up animal dropped on a filled place swaps the two. "Done" sends the row as
// order[place] = index into item.objects. finish() is called once: Done, Give up, or time limit.
TaskViews["constraint_satisfaction"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root, n = it.n;
  const objs = it.objects.map((k) => tx.objects[k]);
  const label = (i) => objs[i].cap || objs[i].name;
  const order = Array(n).fill(null);           // place -> object index
  let sel = null, t0 = 0, firstMove = null, changes = 0, done = false, limitTimer = null;
  const now = () => Math.round(performance.now() - t0);
  const rowEl = root.querySelector(".cs-row"), trayEl = root.querySelector(".cs-tray");
  const doneBtn = root.querySelector(".cs-done");

  // Fill "{a}", "{a.gen}", "{b.cap}", "{p}" ... from the text file's object forms.
  function sentence(con) {
    return tx.templates[con.type].replace(/\{([abc])(?:\.(\w+))?\}|\{p\}/g, (m, who, form) => {
      if (m === "{p}") return String(con.p);
      const o = objs[con[who]];
      return (form && o[form]) || o.name;
    });
  }
  function render(focus) {
    rowEl.innerHTML = ""; trayEl.innerHTML = "";
    let focusEl = null;
    for (let p = 0; p < n; p++) {
      const b = document.createElement("button");
      b.type = "button";
      const o = order[p];
      b.className = "cs-slot" + (o !== null ? " filled" : "") + (sel && sel.place === p ? " sel" : "");
      const num = document.createElement("span"); num.className = "num"; num.textContent = tx.place + " " + (p + 1);
      const name = document.createElement("span"); name.textContent = o !== null ? label(o) : "";
      b.append(num, name);
      b.addEventListener("click", () => clickPlace(p));
      rowEl.append(b);
      if (focus && focus.place === p) focusEl = b;
    }
    for (let i = 0; i < n; i++) {
      if (order.includes(i)) continue;
      const b = document.createElement("button");
      b.type = "button"; b.className = "cs-chip" + (sel && sel.obj === i && sel.place === null ? " sel" : "");
      b.textContent = label(i);
      b.addEventListener("click", () => clickChip(i));
      trayEl.append(b);
      if (focus && focus.obj === i) focusEl = b;
    }
    doneBtn.disabled = order.includes(null);
    if (focusEl) focusEl.focus();
  }
  function touch() { changes += 1; if (firstMove === null) firstMove = now(); }
  function clickChip(i) {
    if (done) return;
    sel = sel && sel.obj === i ? null : { obj: i, place: null };
    render({ obj: i });
  }
  function clickPlace(p) {
    if (done) return;
    if (sel === null) {
      if (order[p] !== null) sel = { obj: order[p], place: p };
      render({ place: p }); return;
    }
    if (sel.place === p) { sel = null; render({ place: p }); return; }
    const here = order[p];
    if (sel.place !== null) order[sel.place] = here;  // swap between places
    order[p] = sel.obj;                               // a tray animal pushes the occupant back to the tray
    sel = null; touch(); render({ place: p });
  }
  function end(timedOut, gaveUp) {
    if (done) return;
    done = true;
    clearTimeout(limitTimer);
    root.querySelectorAll("button").forEach((b) => (b.disabled = true));
    ctx.finish({ order: order.slice(), changes, first_move_ms: firstMove, rt_ms: now(), gave_up: !!gaveUp }, !!timedOut);
  }

  const list = root.querySelector(".cs-rules");
  it.constraints.forEach((con) => { const li = document.createElement("li"); li.textContent = sentence(con); list.append(li); });
  doneBtn.addEventListener("click", () => { if (!order.includes(null)) end(false, false); });
  root.querySelector(".cs-giveup").addEventListener("click", () => end(false, true));
  root.querySelector(".cs-start").addEventListener("click", (e) => {
    e.currentTarget.style.display = "none";  // the hidden attribute loses to the site-wide button display rule
    root.querySelector(".cs-area").hidden = false;
    t0 = performance.now();
    render();
    limitTimer = setTimeout(() => end(true, false), it.limit_ms || 90000);
  }, { once: true });
};
