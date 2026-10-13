// Procedure learning: study the written steps + a worked example (up to study_ms), then
// operate the machine for 3 new cases without the steps. Press action buttons (or keys
// 1-8), Undo (Backspace) and Done (Enter). A case ends by itself after item.case_ms.
// Response: {study_ms, cases: [{presses: [action ids], rt, undos, timed_out}]}.
TaskViews["procedure_learning"] = function (ctx) {
  const it = ctx.item, tx = ctx.text, root = ctx.root;
  const $ = (s) => root.querySelector(s);
  const LAMP = ["#d1402a", "#2a6fd1"];
  const fill = (s, map) => String(s).replace(/\{(\w+)\}/g, (_, k) => (k in map ? map[k] : ""));
  const act = (a) => tx.actions[a];
  const out = { study_ms: null, cases: [] };

  function machine(el, c) {
    el.innerHTML = "";
    const l = document.createElement("span");
    l.textContent = tx.lamp + " ";
    const dot = document.createElement("span");
    dot.className = "pl-lamp";
    dot.style.background = LAMP[c.lamp];
    dot.title = tx.colors[c.lamp];
    l.appendChild(dot);
    const n = document.createElement("span");
    n.textContent = tx.number + " ";
    const num = document.createElement("span");
    num.className = "pl-num";
    num.textContent = String(c.number);
    n.appendChild(num);
    el.append(l, n);
  }

  function chips(el, seq) {
    el.innerHTML = "";
    seq.forEach((a) => {
      const s = document.createElement("span");
      s.className = "pl-chip";
      s.textContent = act(a);
      el.appendChild(s);
    });
  }

  function stepText(st) {
    if (st.t === "fixed") return fill(tx.step_fixed, { a: act(st.a) });
    if (st.t === "repeat") return fill(tx.step_repeat, { a: act(st.a) });
    return fill(tx.step_cond, { c: tx.colors[st.color], a: act(st.a), b: act(st.b) });
  }

  function study() {
    return new Promise((resolve) => {
      $("#pl-study").hidden = false;
      const ol = $("#pl-steps");
      it.steps.forEach((st) => {
        const li = document.createElement("li");
        li.textContent = stepText(st);
        ol.appendChild(li);
      });
      machine($("#pl-demo-machine"), it.demo);
      chips($("#pl-demo-chips"), it.demo_answer);
      const t0 = performance.now();
      let settled = false;
      const tick = setInterval(() => {
        const left = it.study_ms - (performance.now() - t0);
        $("#pl-study-left").textContent = fill(tx.study_left, { s: Math.max(0, Math.ceil(left / 1000)) });
        if (left <= 0) done();
      }, 250);
      function done() {
        if (settled) return;
        settled = true;
        clearInterval(tick);
        $("#pl-study").hidden = true;
        resolve(Math.round(performance.now() - t0));
      }
      $("#pl-learned").addEventListener("click", done, { once: true });
    });
  }

  function operate(c, k) {
    return new Promise((resolve) => {
      $("#pl-prog").textContent = fill(tx.case_of, { n: k + 1, total: it.cases.length });
      machine($("#pl-machine"), c);
      const presses = [];
      let undos = 0, settled = false;
      chips($("#pl-chips"), presses);
      const acts = $("#pl-acts");
      acts.innerHTML = "";
      const btns = it.buttons.map((a, i) => {
        const b = document.createElement("button");
        b.type = "button";
        const s = document.createElement("span");
        s.className = "k";
        s.textContent = String(i + 1);
        b.append(s, document.createTextNode(act(a)));
        b.addEventListener("click", () => { push(a); b.blur(); });
        acts.appendChild(b);
        return b;
      });
      const t0 = performance.now();
      const timer = setTimeout(() => done(true), it.case_ms);
      function push(a) { if (!settled) { presses.push(a); chips($("#pl-chips"), presses); } }
      function undo() { if (!settled && presses.length) { presses.pop(); undos += 1; chips($("#pl-chips"), presses); } }
      function done(timedOut) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", onKey);
        undoB.removeEventListener("click", undo);
        doneB.removeEventListener("click", onDone);
        resolve({ presses: presses.slice(), rt: Math.round(performance.now() - t0), undos, timed_out: timedOut === true });
      }
      const onKey = (e) => {
        if (e.repeat || (e.target.closest && e.target.closest("#effort"))) return;
        if ((e.key === "Enter" || e.key === " ") && e.target.tagName === "BUTTON") return; // the button's own click
        const n = Number(e.key);
        if (Number.isInteger(n) && n >= 1 && n <= btns.length) { e.preventDefault(); push(it.buttons[n - 1]); }
        else if (e.key === "Backspace") { e.preventDefault(); undo(); }
        else if (e.key === "Enter") { e.preventDefault(); done(false); }
      };
      const onDone = () => done(false);
      const undoB = $("#pl-undo"), doneB = $("#pl-done");
      undoB.addEventListener("click", undo);
      doneB.addEventListener("click", onDone);
      document.addEventListener("keydown", onKey);
    });
  }

  $("#pl-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    out.study_ms = await study();
    $("#pl-test").hidden = false;
    for (let k = 0; k < it.cases.length; k++) out.cases.push(await operate(it.cases[k], k));
    $("#pl-test").hidden = true;
    ctx.finish(out, false);
  }, { once: true });
};
