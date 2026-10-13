// Attentional blink: 10 streams. Each: 500 ms fixation, 18 letters at item.soa_ms each
// (requestAnimationFrame, onsets measured from the first letter's frame), 200 ms blank, then
// the person reports the two red letters (letter buttons or letter keys; Backspace/"Undo" to
// correct, Enter/"OK" to confirm). Response per stream: {r1, r2, late} where late is the
// largest observed-minus-intended letter onset (ms) in that stream.
TaskViews["attentional_blink"] = function (ctx) {
  const it = ctx.item, T = ctx.text;
  const screen = ctx.root.querySelector("#ab-screen");
  const ans = ctx.root.querySelector("#ab-answer");
  const slots = ctx.root.querySelector("#ab-slots");
  const grid = ctx.root.querySelector("#ab-letters");
  const ok = ctx.root.querySelector("#ab-ok");
  const undo = ctx.root.querySelector("#ab-undo");
  const out = [];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fmt = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => (k in v ? v[k] : ""));
  const RED = "#C62828", INK = "#1D2731";

  const letterBtns = it.choices.map((c) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c;
    b.dataset.letter = c;
    b.style.cssText = "margin:0;min-width:2.8rem;font-family:ui-monospace,Menlo,Consolas,monospace";
    grid.appendChild(b);
    return b;
  });

  function play(st) {
    return new Promise((resolve) => {
      let start = null, shown = -1, late = 0;
      function tick(now) {
        if (start === null) start = now;
        const i = Math.floor((now - start) / it.soa_ms);
        if (i >= st.letters.length) { screen.textContent = ""; resolve(Math.round(late)); return; }
        if (i !== shown) {
          shown = i;
          late = Math.max(late, now - start - i * it.soa_ms);
          screen.textContent = st.letters[i];
          screen.style.color = i === st.t1 || i === st.t2 ? RED : INK;
        }
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  function report() {
    return new Promise((resolve) => {
      const picks = [];
      ans.hidden = false;
      const refresh = () => {
        slots.textContent = fmt(T.slots, { a: picks[0] || "_", b: picks[1] || "_" });
        ok.disabled = picks.length !== 2;
      };
      const add = (c) => { if (picks.length < 2) picks.push(c); refresh(); };
      const onLetter = (e) => add(e.currentTarget.dataset.letter);
      const onUndo = () => { picks.pop(); refresh(); };
      const submit = () => {
        if (picks.length !== 2) return;
        letterBtns.forEach((b) => b.removeEventListener("click", onLetter));
        undo.removeEventListener("click", onUndo);
        ok.removeEventListener("click", submit);
        document.removeEventListener("keydown", onKey);
        ans.hidden = true;
        resolve({ r1: picks[0], r2: picks[1] });
      };
      const onKey = (e) => {
        if (e.repeat) return;
        if (e.target.closest && e.target.closest("button") && (e.key === "Enter" || e.key === " ")) return;
        if (e.key === "Enter") { e.preventDefault(); submit(); return; }
        if (e.key === "Backspace") { e.preventDefault(); onUndo(); return; }
        // Letters are plain ASCII A-Z; the list has no I, so Turkish i/ı/İ casing cannot matter.
        const c = e.key.length === 1 ? e.key.toUpperCase() : "";
        if (it.choices.includes(c)) add(c);
      };
      letterBtns.forEach((b) => b.addEventListener("click", onLetter));
      undo.addEventListener("click", onUndo);
      ok.addEventListener("click", submit);
      document.addEventListener("keydown", onKey);
      refresh();
    });
  }

  ctx.root.querySelector("#ab-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    for (let s = 0; s < it.streams.length; s++) {
      ctx.status(fmt(T.progress, { n: s + 1, total: it.streams.length }));
      screen.style.color = INK;
      screen.textContent = "+";
      await wait(500);
      const late = await play(it.streams[s]);
      await wait(200);
      ctx.status(T.ask);
      const r = await report();
      r.late = late;
      out.push(r);
      screen.textContent = "";
      await wait(300);
    }
    ctx.status("");
    ctx.finish(out, false);
  }, { once: true });
};
