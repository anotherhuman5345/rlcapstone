// Mental arithmetic: 4 problems, one at a time, each with a fixed deadline (item.deadline_ms).
// Answer with the on-screen keypad or the keyboard (digits, Backspace, Enter).
// Response: [{answer, rt, timed_out}] in problem order; finish() is called once at the end.
TaskViews["mental_arithmetic"] = function (ctx) {
  const T = ctx.text, probs = ctx.item.problems || [], LIMIT = ctx.item.deadline_ms || 20000;
  const $ = (s) => ctx.root.querySelector(s);
  const probEl = $("#ma-problem"), entry = $("#ma-entry"), pad = $("#ma-pad"), clock = $("#ma-clock");
  const SYM = { "+": T.sym_add, "-": T.sym_sub, "*": T.sym_mul, "/": T.sym_div };
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const show = (toks) => toks.map((t) => SYM[t] || t).join(" ").replace(/\( /g, "(").replace(/ \)/g, ")");
  const out = [];
  let typed = "", cur = null, tick = null;

  function digitOf(key) {
    if (/^[0-9]$/.test(key)) return key;
    const c = key.length === 1 ? key.charCodeAt(0) : 0;
    if (c >= 0x660 && c <= 0x669) return String(c - 0x660);
    if (c >= 0x6f0 && c <= 0x6f9) return String(c - 0x6f0);
    return null;
  }
  const render = () => { entry.textContent = typed || " "; };
  function submit(timedOut) {
    if (!cur) return;
    const c = cur; cur = null;
    clearTimeout(c.timer); clearInterval(tick);
    c.resolve({ answer: typed || null, rt: timedOut ? null : Math.round(performance.now() - c.t0), timed_out: timedOut });
  }
  function press(act, d) {
    if (!cur) return;
    if (d != null) { if (typed.length < 6) typed += d; }
    else if (act === "back") typed = typed.slice(0, -1);
    else if (act === "ok") { if (typed) submit(false); return; }
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

  function ask(p) {
    return new Promise((resolve) => {
      typed = ""; render();
      probEl.textContent = show(p.tokens) + " = ?";
      const t0 = performance.now();
      const showClock = () => { clock.textContent = fmt(T.seconds_left, { s: Math.max(0, Math.ceil((LIMIT - (performance.now() - t0)) / 1000)) }); };
      showClock(); tick = setInterval(showClock, 250);
      cur = { resolve, t0, timer: setTimeout(() => submit(true), LIMIT) };
    });
  }

  $("#ma-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    pad.hidden = false;
    document.addEventListener("keydown", onKey);
    for (let i = 0; i < probs.length; i++) {
      ctx.status(fmt(T.progress, { i: i + 1, n: probs.length }));
      out.push(await ask(probs[i]));
    }
    document.removeEventListener("keydown", onKey);
    pad.hidden = true; probEl.textContent = " "; clock.textContent = " "; ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
