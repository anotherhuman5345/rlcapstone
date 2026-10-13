// Memory updating: start values shown 4000 ms, then hidden; each update instruction is
// shown for 3000 ms with a 500 ms blank after it. Then one input per box (keyboard digits,
// or the on-screen keypad writing into the selected box; Enter moves on). Done sends
// {values: [int|null per box], rt: ms from answer screen to Done}.
TaskViews["memory_updating"] = function (ctx) {
  const tx = ctx.text, item = ctx.item;
  const $ = (s) => ctx.root.querySelector(s);
  const boxesEl = $("#mu-boxes"), instr = $("#mu-instr"), phase = $("#mu-phase"), answer = $("#mu-answer");
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const label = (b) => tx.box_labels[b];
  const vals = [], inputs = [];
  let finished = false;

  for (let b = 0; b < item.boxes; b++) {
    const box = document.createElement("div");
    box.className = "mu-box";
    const lab = document.createElement("div");
    lab.className = "mu-label";
    lab.textContent = label(b);
    const v = document.createElement("div");
    v.className = "mu-val";
    box.append(lab, v);
    boxesEl.appendChild(box);
    vals.push(v);
  }

  function phrase(u) {
    const tpl = u.op === "add" ? tx.op_add : tx.op_sub;
    return tpl.split("{n}").join(String(u.n)).split("{b}").join(label(u.box));
  }

  function answerPhase() {
    phase.textContent = tx.phase_answer;
    instr.textContent = "";
    let active = 0;
    vals.forEach((v, b) => {
      const inp = document.createElement("input");
      inp.type = "text";
      inp.inputMode = "none";          // on-screen keypad on touch devices; real keys still type
      inp.autocomplete = "off";
      inp.maxLength = 2;
      inp.setAttribute("aria-label", label(b));
      inp.addEventListener("focus", () => { active = b; });
      inp.addEventListener("input", () => { inp.value = inp.value.replace(/[^0-9]/g, "").slice(0, 2); });
      inp.addEventListener("keydown", (e) => {
        if (e.key !== "Enter" || e.repeat) return;
        e.preventDefault();
        if (b + 1 < inputs.length) inputs[b + 1].focus(); else done();
      });
      v.replaceChildren(inp);
      inputs.push(inp);
    });
    answer.hidden = false;
    const t0 = performance.now();
    ctx.root.querySelectorAll("[data-digit]").forEach((btn) => {
      btn.addEventListener("pointerdown", (e) => e.preventDefault()); // keep focus in the box
      btn.addEventListener("click", () => {
        const inp = inputs[active];
        if (inp.value.length < 2) inp.value += btn.dataset.digit;
        inp.focus();
      });
    });
    const back = $("#mu-back");
    back.addEventListener("pointerdown", (e) => e.preventDefault());
    back.addEventListener("click", () => { const inp = inputs[active]; inp.value = inp.value.slice(0, -1); inp.focus(); });
    function done() {
      if (finished) return;
      finished = true;
      inputs.forEach((i) => (i.disabled = true));
      answer.hidden = true;
      const values = inputs.map((i) => (i.value === "" ? null : parseInt(i.value, 10)));
      ctx.finish({ values, rt: Math.round(performance.now() - t0) }, false);
    }
    $("#mu-done").addEventListener("click", done);
    inputs[0].focus();
  }

  $("#mu-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    phase.textContent = tx.phase_study;
    item.start.forEach((s, b) => (vals[b].textContent = String(s)));
    await wait(4000);
    vals.forEach((v) => (v.textContent = "?"));
    phase.textContent = tx.phase_update;
    await wait(500);
    for (const u of item.updates) {
      instr.textContent = phrase(u);
      await wait(3000);
      instr.textContent = "";
      await wait(500);
    }
    answerPhase();
  }, { once: true });
};
