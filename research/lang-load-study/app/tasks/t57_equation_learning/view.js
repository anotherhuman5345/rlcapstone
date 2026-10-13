// Equation learning: the two symbol rules (words from the text file) and worked examples are
// shown first; Start begins 4 expressions, answered with the keypad or keyboard.
// Rules stay visible. Response: {study_ms, answers: [{answer, rt}]}; finish() once at the end.
TaskViews["equation_learning"] = function (ctx) {
  const T = ctx.text, it = ctx.item, probs = it.problems || [];
  const $ = (s) => ctx.root.querySelector(s);
  const rulesEl = $("#eq-rules"), probEl = $("#eq-problem"), entry = $("#eq-entry"), pad = $("#eq-pad");
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
  const expr = (toks) => toks.join(" ");
  const answers = [];
  let typed = "", cur = null;
  const t0 = performance.now();

  function line(cls, txt) { const p = document.createElement("p"); p.className = cls; p.textContent = txt; rulesEl.appendChild(p); return p; }
  for (const s of [it.hi, it.lo]) {
    const p = line("", "");
    const b = document.createElement("span"); b.className = "sym"; b.textContent = "a " + s + " b";
    p.append(b, document.createTextNode(" : " + T["rule_" + it.rules[s]]));
    const ex = it.examples.filter((e) => e.tokens[1] === s).map((e) => expr(e.tokens) + " = " + e.value);
    const exl = line("ex", T.examples + " " + ex.join(T.list_sep));
    exl.dir = "auto";
  }
  line("prec", fmt(T.precedence, { hi: it.hi, lo: it.lo }));

  function digitOf(key) {
    if (/^[0-9]$/.test(key)) return key;
    const c = key.length === 1 ? key.charCodeAt(0) : 0;
    if (c >= 0x660 && c <= 0x669) return String(c - 0x660);
    if (c >= 0x6f0 && c <= 0x6f9) return String(c - 0x6f0);
    return null;
  }
  const render = () => { entry.textContent = typed || " "; };
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
  function ask(p) {
    return new Promise((resolve) => {
      typed = ""; render();
      probEl.textContent = expr(p.tokens) + " = ?";
      cur = { resolve, t0: performance.now() };
    });
  }

  $("#eq-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const study = Math.round(performance.now() - t0);
    pad.hidden = false; entry.hidden = false;
    document.addEventListener("keydown", onKey);
    for (let i = 0; i < probs.length; i++) {
      ctx.status(fmt(T.progress, { i: i + 1, n: probs.length }));
      answers.push(await ask(probs[i]));
    }
    document.removeEventListener("keydown", onKey);
    pad.hidden = true; entry.hidden = true; probEl.textContent = " "; ctx.status("");
    ctx.finish({ study_ms: study, answers }, false);
  }, { once: true });
};
