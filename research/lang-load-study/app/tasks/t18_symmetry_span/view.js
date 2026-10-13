// Symmetry span: for each step, judge an 8x8 pattern (up to 4000 ms; left arrow / Yes,
// right arrow / No), then a red square flashes for 1000 ms in a 4x4 grid (500 ms blank after).
// After the set, tap the squares in order (mouse/touch, or arrow keys + Enter; Backspace undoes).
// Response: {symmetry: [{answer, rt}], recall: [cell...], recall_rt}.
TaskViews["symmetry_span"] = function (ctx) {
  const tx = ctx.text;
  const $ = (s) => ctx.root.querySelector(s);
  const area = $("#sp-area"), phase = $("#sp-phase"), judge = $("#sp-judge"), recallRow = $("#sp-recall");
  const judgeBtns = [...judge.querySelectorAll("[data-key]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const keyOk = (e) => !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey && !(e.target.closest && e.target.closest("form"));
  let finished = false, recallKey = null;

  function drawPattern(rows) {
    const g = document.createElement("div");
    g.className = "sp-pat";
    rows.forEach((row) => [...row].forEach((ch) => {
      const c = document.createElement("div");
      if (ch === "1") c.className = "on";
      g.appendChild(c);
    }));
    area.replaceChildren(g);
  }

  function drawLocation(loc) {
    const g = document.createElement("div");
    g.className = "sp-grid";
    for (let i = 0; i < 16; i++) {
      const c = document.createElement("div");
      if (i === loc) c.className = "lit";
      g.appendChild(c);
    }
    area.replaceChildren(g);
  }

  function judgeAnswer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (answer) => { cleanup(); resolve({ answer, rt: answer ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => {
        if (!keyOk(e)) return;
        if (e.key === "ArrowLeft") { e.preventDefault(); done("yes"); }
        else if (e.key === "ArrowRight") { e.preventDefault(); done("no"); }
      };
      const onBtn = (e) => { e.currentTarget.blur(); done(e.currentTarget.dataset.key); };
      const timer = setTimeout(() => done(null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        judgeBtns.forEach((b) => b.removeEventListener("click", onBtn));
      }
      document.addEventListener("keydown", onKey);
      judgeBtns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  function recall(symmetry) {
    const picks = [];
    const g = document.createElement("div");
    g.className = "sp-grid";
    const cells = [];
    for (let i = 0; i < 16; i++) {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.cell = String(i);
      b.addEventListener("click", () => {
        if (finished || picks.includes(i)) return;
        picks.push(i);
        b.classList.add("picked");
        b.textContent = String(picks.length);
      });
      cells.push(b);
      g.appendChild(b);
    }
    area.replaceChildren(g);
    phase.textContent = tx.phase_recall;
    recallRow.hidden = false;
    const t0 = performance.now();
    const undo = () => {
      const last = picks.pop();
      if (last === undefined) return;
      cells[last].classList.remove("picked");
      cells[last].textContent = "";
    };
    $("#sp-undo").addEventListener("click", undo);
    recallKey = (e) => {
      if (!keyOk(e)) return;
      if (e.key === "Backspace") { e.preventDefault(); undo(); return; }
      const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -4, ArrowDown: 4 };
      if (!(e.key in moves)) return;
      e.preventDefault();
      const cur = cells.indexOf(document.activeElement);
      if (cur < 0) { cells[0].focus(); return; }
      const nxt = cur + moves[e.key];
      const sameRow = Math.abs(moves[e.key]) === 4 || Math.floor(nxt / 4) === Math.floor(cur / 4);
      if (nxt >= 0 && nxt < 16 && sameRow) cells[nxt].focus();
    };
    document.addEventListener("keydown", recallKey);
    $("#sp-done").addEventListener("click", () => {
      if (finished) return;
      finished = true;
      document.removeEventListener("keydown", recallKey);
      recallRow.hidden = true;
      cells.forEach((c) => (c.disabled = true));
      ctx.finish({ symmetry, recall: picks.slice(), recall_rt: Math.round(performance.now() - t0) }, false);
    });
  }

  $("#sp-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const symmetry = [];
    for (const st of ctx.item.steps) {
      phase.textContent = tx.phase_judge;
      drawPattern(st.pattern);
      judge.hidden = false;
      symmetry.push(await judgeAnswer(4000));
      judge.hidden = true;
      phase.textContent = tx.phase_remember;
      drawLocation(st.loc);
      await wait(1000);
      area.replaceChildren();
      phase.textContent = "";
      await wait(500);
    }
    recall(symmetry);
  }, { once: true });
};
