// Code tracing: 3 short programs; type the number each one prints with the on-screen
// keypad or the keyboard (digits, minus, Backspace, Enter), then OK. Time limit
// item.limit_ms per program. Response: [{p, answer (integer or null), rt}].
TaskViews["code_tracing"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const $ = (s) => root.querySelector(s);
  const code = $("#ct-code"), val = $("#ct-val"), prog = $("#ct-prog");
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const OPS = { "+": "+", "-": "−", "*": "×", ">": ">", "<": "<" };
  const out = [];

  function expr(e) {
    if (typeof e === "number" || typeof e === "string") return String(e);
    return expr(e[1]) + " " + OPS[e[0]] + " " + expr(e[2]);
  }

  function lines(stmts, depth, acc) {
    const pad = "    ".repeat(depth);
    stmts.forEach((s) => {
      if (s.op === "set") acc.push(pad + fill(tx.kw_set, { v: s.v, e: expr(s.e) }));
      else if (s.op === "print") acc.push(pad + fill(tx.kw_print, { e: expr(s.e) }));
      else if (s.op === "repeat") { acc.push(pad + fill(tx.kw_repeat, { n: s.n })); lines(s.body, depth + 1, acc); }
      else if (s.op === "if") {
        acc.push(pad + fill(tx.kw_if, { c: expr(s.c) }));
        lines(s.then, depth + 1, acc);
        if (s.else && s.else.length) { acc.push(pad + tx.kw_else); lines(s.else, depth + 1, acc); }
      }
    });
    return acc;
  }

  function ask() {
    return new Promise((resolve) => {
      let txt = "", settled = false;
      const show = () => { val.textContent = txt; };
      show();
      const t0 = performance.now();
      const press = (k) => {
        if (k === "back") txt = txt.slice(0, -1);
        else if (k === "-") txt = txt.startsWith("-") ? txt.slice(1) : "-" + txt;
        else if (/^[0-9]$/.test(k) && txt.replace("-", "").length < 4) txt += k;
        show();
      };
      const onPad = (e) => { const b = e.target.closest("[data-k]"); if (b) { press(b.dataset.k); b.blur(); } };
      const okB = $("#ct-ok"), pad = $("#ct-pad");
      const submit = () => { if (/^-?[0-9]+$/.test(txt)) done(parseInt(txt, 10)); };
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        if ((e.key === "Enter" || e.key === " ") && e.target.tagName === "BUTTON") return; // the button's own click
        if (/^[0-9]$/.test(e.key)) { e.preventDefault(); press(e.key); }
        else if (e.key === "-" || e.key === "Subtract") { e.preventDefault(); press("-"); }
        else if (e.key === "Backspace") { e.preventDefault(); press("back"); }
        else if (e.key === "Enter") { e.preventDefault(); submit(); }
      };
      const timer = setTimeout(() => done(null), it.limit_ms);
      function done(v) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        pad.removeEventListener("click", onPad);
        okB.removeEventListener("click", submit);
        resolve({ answer: v, rt: v === null ? null : Math.round(performance.now() - t0) });
      }
      pad.addEventListener("click", onPad);
      okB.addEventListener("click", submit);
      document.addEventListener("keydown", onKey);
    });
  }

  $("#ct-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    code.hidden = false;
    $("#ct-answer").hidden = false;
    for (let p = 0; p < it.programs.length; p++) {
      prog.textContent = fill(tx.program_of, { n: p + 1, total: it.programs.length });
      code.textContent = lines(it.programs[p], 0, []).join("\n");
      const a = await ask();
      out.push({ p, answer: a.answer, rt: a.rt });
    }
    code.hidden = true;
    $("#ct-answer").hidden = true;
    prog.textContent = "";
    ctx.finish(out, false);
  }, { once: true });
};
