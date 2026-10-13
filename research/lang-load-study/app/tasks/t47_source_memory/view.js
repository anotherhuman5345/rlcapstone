// Source memory: study 8 words (2000 ms each, in the left circle or the right square,
// 500 ms blank after), then 12 test words, each up to 6000 ms (400 ms blank after).
// Keys: left arrow = circle, right arrow = square, down arrow = new; or the buttons.
// Response: {answers: [{answer: "circle"|"square"|"new"|null, rt}, ...in test order]}.
TaskViews["source_memory"] = function (ctx) {
  const tx = ctx.text, item = ctx.item;
  const $ = (s) => ctx.root.querySelector(s);
  const phase = $("#sm-phase"), stage = $("#sm-stage"), probe = $("#sm-probe"), btnRow = $("#sm-btns");
  const slots = { circle: $("#sm-circle"), square: $("#sm-square") };
  const btns = [...btnRow.querySelectorAll("[data-key]")];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const keyOk = (e) => !e.repeat && !e.ctrlKey && !e.altKey && !e.metaKey && !(e.target.closest && e.target.closest("form"));
  const KEYS = { ArrowLeft: "circle", ArrowRight: "square", ArrowDown: "new" };

  function answer(limit) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (a) => { cleanup(); resolve({ answer: a, rt: a ? Math.round(performance.now() - t0) : null }); };
      const onKey = (e) => { if (keyOk(e) && KEYS[e.key]) { e.preventDefault(); done(KEYS[e.key]); } };
      const onBtn = (e) => { e.currentTarget.blur(); done(e.currentTarget.dataset.key); };
      const timer = setTimeout(() => done(null), limit);
      function cleanup() {
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        btns.forEach((b) => b.removeEventListener("click", onBtn));
      }
      document.addEventListener("keydown", onKey);
      btns.forEach((b) => b.addEventListener("click", onBtn));
    });
  }

  $("#sm-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    phase.textContent = tx.phase_study;
    for (const s of item.study) {
      const slot = slots[s.source];
      slot.textContent = tx.words[s.word];
      slot.classList.add("on");
      await wait(2000);
      slot.classList.remove("on");
      slot.textContent = "";
      await wait(500);
    }
    stage.hidden = true;
    phase.textContent = tx.phase_test;
    probe.hidden = false;
    btnRow.hidden = false;
    const answers = [];
    for (const w of item.test) {
      probe.textContent = tx.words[w];
      answers.push(await answer(6000));
      probe.textContent = "";
      await wait(400);
    }
    btnRow.hidden = true;
    probe.hidden = true;
    phase.textContent = "";
    ctx.finish({ answers }, false);
  }, { once: true });
};
