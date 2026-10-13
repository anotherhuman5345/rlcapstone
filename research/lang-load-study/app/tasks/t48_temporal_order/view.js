// Temporal order: each event phrase is shown 2000 ms with a 400 ms blank after. Then the
// cards appear (shuffled); tap them first-to-last (or press the card's number key),
// Undo/Backspace removes the last one, Done/Enter finishes once every card is placed.
// Response: {order: [study position of each tapped card], rt: ms from cards shown to Done}.
TaskViews["temporal_order"] = function (ctx) {
  const tx = ctx.text, item = ctx.item;
  const $ = (s) => ctx.root.querySelector(s);
  const phase = $("#to-phase"), evEl = $("#to-event"), cardsEl = $("#to-cards"), ctrl = $("#to-ctrl"), doneBtn = $("#to-done");
  const cards = [...cardsEl.querySelectorAll("[data-ev]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const keyOk = (e) => !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey && !(e.target.closest && e.target.closest("form"));
  const order = [];
  let finished = false, t0 = 0, onKey = null;

  function refresh() {
    cards.forEach((c) => {
      const i = order.indexOf(parseInt(c.dataset.ev, 10));
      c.classList.toggle("placed", i >= 0);
      c.querySelector(".pos").textContent = i >= 0 ? String(i + 1) : "";
    });
    doneBtn.disabled = order.length !== cards.length;
  }
  function pick(card) {
    const ev = parseInt(card.dataset.ev, 10);
    if (finished || order.includes(ev)) return;
    order.push(ev);
    refresh();
  }
  function undo() { if (!finished && order.length) { order.pop(); refresh(); } }
  function done() {
    if (finished || order.length !== cards.length) return;
    finished = true;
    document.removeEventListener("keydown", onKey);
    cards.forEach((c) => (c.disabled = true));
    ctrl.hidden = true;
    ctx.finish({ order: order.slice(), rt: Math.round(performance.now() - t0) }, false);
  }

  cards.forEach((c) => c.addEventListener("click", (e) => { if (e.detail) c.blur(); pick(c); }));
  $("#to-undo").addEventListener("click", undo);
  doneBtn.addEventListener("click", done);

  $("#to-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    phase.textContent = tx.phase_study;
    for (const ev of item.events) {
      evEl.textContent = tx.events[ev];
      await wait(2000);
      evEl.textContent = "";
      await wait(400);
    }
    evEl.hidden = true;
    phase.textContent = tx.phase_test;
    cardsEl.hidden = false;
    ctrl.hidden = false;
    t0 = performance.now();
    onKey = (e) => {
      if (!keyOk(e)) return;
      const k = parseInt(e.key, 10);
      if (k >= 1 && k <= cards.length) { e.preventDefault(); pick(cards[k - 1]); }
      else if (e.key === "Backspace") { e.preventDefault(); undo(); }
      else if (e.key === "Enter" && !(e.target.tagName === "BUTTON")) { e.preventDefault(); done(); }
    };
    document.addEventListener("keydown", onKey);
  }, { once: true });
};
