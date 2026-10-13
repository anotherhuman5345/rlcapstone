// Troubleshooting: draws the machine (parts as buttons over an SVG of the wiring), lights the
// lamps for the current fault, and lets the participant select a part (click/tap, Tab+Enter, or
// keys 1-6), test it (shows power out / no power out, costs 1), and report it as broken.
// Two cases on the same machine; each starts with fresh test marks.
// Response: {cases: [{tests: [part...], diagnosis: part, t: ms}]}.
TaskViews["troubleshooting"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, tx = ctx.text, P = it.parent, N = P.length;
  const box = $("#tb-machine"), svg = $("#tb-lines");
  const SRC = [0.05, 0.5], LAMP_X = 0.94;
  const out = { cases: [] };
  let ci = -1, sel = null, rec = null, caseT0 = 0, ended = false, timer = 0;

  function upstream(u) { const a = []; while (u !== -1) { a.push(u); u = P[u]; } return a; }
  const powered = (u, fault) => !upstream(u).includes(fault);

  // Number parts in reading order (left to right, top to bottom) so numbers carry no wiring hint.
  const order = [...Array(N).keys()].sort((a, b) => it.x[a] - it.x[b] || it.y[a] - it.y[b]);
  const numOf = {}; order.forEach((v, k) => { numOf[v] = k + 1; });

  const line = (a, b) => '<line x1="' + a[0] * 1000 + '" y1="' + a[1] * 500 + '" x2="' + b[0] * 1000 + '" y2="' + b[1] * 500 + '" stroke="#8a9aa8" stroke-width="4"/>';
  let lines = "";
  for (let v = 0; v < N; v++) {
    const from = P[v] === -1 ? SRC : [it.x[P[v]], it.y[P[v]]];
    lines += line(from, [it.x[v], it.y[v]]);
  }
  it.lamps.forEach((v) => { lines += line([it.x[v], it.y[v]], [LAMP_X, it.y[v]]); });
  svg.innerHTML = lines;

  const place = (el, x, y) => { el.style.left = x * 100 + "%"; el.style.top = y * 100 + "%"; box.appendChild(el); };
  const src = document.createElement("div");
  src.className = "tag"; src.innerHTML = '<div class="src"></div>';
  src.appendChild(document.createTextNode(tx.power));
  place(src, SRC[0], SRC[1]);
  const lampEls = it.lamps.map((v) => {
    const d = document.createElement("div");
    d.className = "tag"; d.innerHTML = '<div class="lamp"></div>';
    d.appendChild(document.createTextNode(tx.lamp));
    place(d, LAMP_X, it.y[v]);
    return d.querySelector(".lamp");
  });
  const nodes = [];
  for (let v = 0; v < N; v++) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "node";
    b.innerHTML = '<span class="n">' + numOf[v] + '</span><span class="name"></span><span class="res"></span>';
    b.querySelector(".name").textContent = tx.parts[it.names[v]];
    b.addEventListener("click", () => select(v));
    place(b, it.x[v], it.y[v]);
    nodes.push(b);
  }

  function select(v) {
    if (ended || ci < 0) return;
    sel = v;
    nodes.forEach((b, u) => b.classList.toggle("sel", u === v));
    $("#tb-test").disabled = $("#tb-report").disabled = false;
  }
  function count() { $("#tb-count").textContent = tx.tests_used.replace("{n}", rec.tests.length); }

  function startCase(k) {
    ci = k; sel = null;
    rec = { tests: [], diagnosis: null, t: null };
    out.cases.push(rec);
    const fault = it.faults[k];
    $("#tb-case").textContent = tx.case_label.replace("{n}", k + 1).replace("{total}", it.faults.length);
    lampEls.forEach((el, i) => el.classList.toggle("on", powered(it.lamps[i], fault)));
    nodes.forEach((b) => { b.classList.remove("sel"); const r = b.querySelector(".res"); r.textContent = ""; r.className = "res"; });
    $("#tb-test").disabled = $("#tb-report").disabled = true;
    count();
    caseT0 = performance.now();
  }

  $("#tb-test").addEventListener("click", () => {
    if (ended || sel === null) return;
    const ok = powered(sel, it.faults[ci]);
    rec.tests.push(sel);
    const r = nodes[sel].querySelector(".res");
    r.textContent = ok ? "✓ " + tx.signal : "✗ " + tx.no_signal;
    r.className = "res " + (ok ? "yes" : "no");
    count();
  });
  $("#tb-report").addEventListener("click", () => {
    if (ended || sel === null) return;
    rec.diagnosis = sel;
    rec.t = Math.round(performance.now() - caseT0);
    if (ci + 1 < it.faults.length) startCase(ci + 1); else end(false);
  });

  const onKey = (e) => {
    if (e.repeat || ended) return;
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= N) select(order[n - 1]);
  };

  $("#tb-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    box.hidden = false;
    $("#tb-actions").hidden = false;
    $("#tb-hint").hidden = false;
    document.addEventListener("keydown", onKey);
    timer = setTimeout(() => end(true), it.limit_ms);
    startCase(0);
  }, { once: true });

  function end(timedOut) {
    if (ended) return;
    ended = true;
    clearTimeout(timer);
    document.removeEventListener("keydown", onKey);
    $("#tb-test").disabled = $("#tb-report").disabled = true;
    ctx.finish(out, timedOut);
  }
};
