// Number sequences: 4 sequences, one at a time; six numbers in boxes, then an answer box.
// Type the next number with the keypad or the keyboard (digits, Backspace, Enter).
// Response: [{answer, rt}] in sequence order; finish() is called once after the last one.
TaskViews["number_sequences"] = function (ctx) {
  const T = ctx.text, seqs = ctx.item.sequences || [];
  const $ = (s) => ctx.root.querySelector(s);
  const row = $("#ns-row"), pad = $("#ns-pad");
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const out = [];
  let typed = "", cur = null, box = null;

  function digitOf(key) {
    if (/^[0-9]$/.test(key)) return key;
    const c = key.length === 1 ? key.charCodeAt(0) : 0;
    if (c >= 0x660 && c <= 0x669) return String(c - 0x660);
    if (c >= 0x6f0 && c <= 0x6f9) return String(c - 0x6f0);
    return null;
  }
  const render = () => { if (box) box.textContent = typed || "?"; };
  function press(act, d) {
    if (!cur) return;
    if (d != null) { if (typed.length < 5) typed += d; }
    else if (act === "back") typed = typed.slice(0, -1);
    else if (act === "ok") {
      if (!typed) return;
      const c = cur; cur = null;
      c.resolve({ answer: typed, rt: Math.round(performance.now() - c.t0) });
      return;
    }
    render();
  }
  pad.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) press(b.dataset.act, b.dataset.d != null ? b.dataset.d : null);
  });
  function onKey(e) {
    if (e.repeat || !cur) return;
    const d = digitOf(e.key);
    if (d != null) { press(null, d); e.preventDefault(); }
    else if (e.key === "Backspace") { press("back"); e.preventDefault(); }
    else if (e.key === "Enter") { press("ok"); e.preventDefault(); }
  }
  function ask(s) {
    return new Promise((resolve) => {
      row.textContent = "";
      for (const t of s.terms) {
        const el = document.createElement("span");
        el.className = "term"; el.textContent = t; row.appendChild(el);
      }
      box = document.createElement("span");
      box.className = "entry-box"; box.setAttribute("aria-live", "polite");
      row.appendChild(box);
      typed = ""; render();
      cur = { resolve, t0: performance.now() };
    });
  }

  $("#ns-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    pad.hidden = false;
    document.addEventListener("keydown", onKey);
    for (let i = 0; i < seqs.length; i++) {
      ctx.status(fmt(T.progress, { i: i + 1, n: seqs.length }));
      out.push(await ask(seqs[i]));
    }
    document.removeEventListener("keydown", onKey);
    pad.hidden = true; row.textContent = ""; ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
