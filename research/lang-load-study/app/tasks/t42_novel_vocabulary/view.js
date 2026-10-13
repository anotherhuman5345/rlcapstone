// Novel vocabulary: study 4 invented words (fixed time each), then 8 multiple-choice
// questions. Answer by clicking/tapping an option or pressing 1-4.
// Response: [{q, choice (word index or null), rt}] in question order.
TaskViews["novel_vocabulary"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const card = root.querySelector("#nv-card"), prog = root.querySelector("#nv-prog");
  const label = root.querySelector("#nv-label"), textEl = root.querySelector("#nv-text");
  const opts = root.querySelector("#nv-opts");
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const out = [];
  let ended = false, cancel = null;

  function end() {
    if (ended) return;
    ended = true;
    if (cancel) cancel();
    opts.innerHTML = "";
    card.hidden = true;
    ctx.finish(out, false);
  }

  function ask(labels) {
    // Show option buttons; resolve with the chosen position (0-3) and its RT.
    return new Promise((resolve) => {
      opts.innerHTML = "";
      const btns = labels.map((txt, i) => {
        const b = document.createElement("button");
        b.type = "button";
        const k = document.createElement("span");
        k.className = "k";
        k.textContent = String(i + 1);
        b.appendChild(k);
        b.appendChild(document.createTextNode(" " + txt));
        b.addEventListener("click", () => done(i));
        opts.appendChild(b);
        return b;
      });
      const t0 = performance.now();
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        const n = Number(e.key);
        if (Number.isInteger(n) && n >= 1 && n <= btns.length) { e.preventDefault(); done(n - 1); }
      };
      let settled = false;
      const timer = setTimeout(() => done(null), 20000);
      function done(i) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        cancel = null;
        resolve({ pos: i, rt: i === null ? null : Math.round(performance.now() - t0) });
      }
      cancel = () => { if (!settled) { settled = true; clearTimeout(timer); document.removeEventListener("keydown", onKey); } };
      document.addEventListener("keydown", onKey);
    });
  }

  root.querySelector("#nv-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    card.hidden = false;
    // Study phase: every word gets the same exposure time.
    for (let w = 0; w < it.words.length; w++) {
      const wd = it.words[w];
      prog.textContent = fill(tx.word_of, { n: w + 1, total: it.words.length });
      label.textContent = "";
      textEl.textContent = "";
      await wait(400);
      label.textContent = wd.label;
      textEl.textContent = tx.meanings[wd.meaning];
      await wait(it.study_ms);
    }
    // Test phase.
    for (let q = 0; q < it.questions.length; q++) {
      if (ended) return;
      const qu = it.questions[q];
      const wd = it.words[qu.word];
      prog.textContent = fill(tx.question_of, { n: q + 1, total: it.questions.length });
      let labels;
      if (qu.kind === "meaning") {
        label.textContent = wd.label;
        textEl.textContent = tx.q_meaning;
        labels = qu.options.map((w) => tx.meanings[it.words[w].meaning]);
      } else {
        label.textContent = "";
        textEl.textContent = tx.q_apply + " " + tx.examples[wd.meaning];
        labels = qu.options.map((w) => it.words[w].label);
      }
      const a = await ask(labels);
      out.push({ q, choice: a.pos === null ? null : qu.options[a.pos], rt: a.rt });
    }
    end();
  }, { once: true });
};
