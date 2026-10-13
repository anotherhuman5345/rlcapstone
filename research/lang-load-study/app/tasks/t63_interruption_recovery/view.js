// Interruption recovery: two cases, each a 6-step procedure carried out by clicking palette
// buttons (or number keys 1-8). In the interrupted case, the 3rd click hides the procedure and
// starts a fixed-length even/odd digit task (arrow keys or buttons); then the same screen comes
// back with no cue (resume_at logged). A case ends after 6 clicks. Times are ms from case start.
// Response: {cases: [{clicks: [[step, t]], resume_at}], parity: [{key, rt}]}.
TaskViews["interruption_recovery"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, tx = ctx.text, N = it.cases[0].procedure.length;
  const out = { cases: [], parity: it.parity_digits.map(() => ({ key: null, rt: null })) };
  const timers = [];
  let phase = "idle", ci = -1, caseT0 = 0, rec = null, ended = false;
  let parIdx = -1, parT0 = 0;

  function renderCase() {
    const c = it.cases[ci];
    $("#ir-case").textContent = tx.case_label.replace("{n}", ci + 1).replace("{total}", it.cases.length);
    const ol = $("#ir-proc"); ol.innerHTML = "";
    c.procedure.forEach((s) => { const li = document.createElement("li"); li.textContent = tx.steps[s]; ol.appendChild(li); });
    const pal = $("#ir-palette"); pal.innerHTML = "";
    c.palette.forEach((s, k) => {
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = '<span class="n">' + (k + 1) + "</span>";
      b.appendChild(document.createTextNode(tx.steps[s]));
      b.addEventListener("click", () => step(s));
      pal.appendChild(b);
    });
  }

  function startCase(k) {
    ci = k;
    rec = { clicks: [], resume_at: null };
    out.cases.push(rec);
    renderCase();
    $("#ir-between").hidden = true;
    $("#ir-work").hidden = false;
    phase = "work";
    caseT0 = performance.now();
  }

  function step(s) {
    if (phase !== "work" || ended) return;
    rec.clicks.push([s, Math.round(performance.now() - caseT0)]);
    const c = it.cases[ci];
    if (rec.clicks.length >= N) { caseDone(); return; }
    if (c.interrupt_after !== null && rec.clicks.length === c.interrupt_after) interrupt();
  }

  function interrupt() {
    phase = "interrupt";
    if (document.activeElement) document.activeElement.blur();
    $("#ir-work").hidden = true;
    $("#ir-interrupt").hidden = false;
    it.parity_digits.forEach((d, k) => timers.push(setTimeout(() => {
      parIdx = k; parT0 = performance.now(); $("#ir-digit").textContent = d;
    }, k * it.parity_ms)));
    timers.push(setTimeout(() => {
      parIdx = -1;
      $("#ir-digit").textContent = "";
      $("#ir-interrupt").hidden = true;
      $("#ir-work").hidden = false;
      phase = "work";
      rec.resume_at = Math.round(performance.now() - caseT0);
    }, it.parity_digits.length * it.parity_ms));
  }

  function parity(key) {
    if (phase !== "interrupt" || parIdx < 0 || out.parity[parIdx].key !== null) return;
    out.parity[parIdx] = { key, rt: Math.round(performance.now() - parT0) };
  }
  ctx.root.querySelectorAll("[data-par]").forEach((b) => b.addEventListener("click", () => parity(b.dataset.par)));

  function caseDone() {
    if (ci + 1 >= it.cases.length) { end(false); return; }
    phase = "between";
    if (document.activeElement) document.activeElement.blur();
    $("#ir-work").hidden = true;
    $("#ir-between").hidden = false;
    timers.push(setTimeout(() => startCase(ci + 1), 1500));
  }

  const onKey = (e) => {
    if (e.repeat || ended) return;
    if (phase === "interrupt") {
      if (e.key === "ArrowLeft") { e.preventDefault(); parity("even"); }
      if (e.key === "ArrowRight") { e.preventDefault(); parity("odd"); }
      return;
    }
    if (phase !== "work") return;
    const n = parseInt(e.key, 10);
    const pal = it.cases[ci].palette;
    if (n >= 1 && n <= pal.length) step(pal[n - 1]);
  };

  $("#ir-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", onKey);
    timers.push(setTimeout(() => end(true), it.limit_ms));
    startCase(0);
  }, { once: true });

  function end(timedOut) {
    if (ended) return;
    ended = true;
    phase = "done";
    timers.forEach(clearTimeout);
    document.removeEventListener("keydown", onKey);
    $("#ir-work").hidden = true;
    $("#ir-interrupt").hidden = true;
    ctx.finish(out, timedOut);
  }
};
