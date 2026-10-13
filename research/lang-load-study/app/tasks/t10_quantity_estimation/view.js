// Brief quantity estimation: 9 displays. Each: 500 ms fixation cross, dots for 200 ms
// (rAF-measured), a 300 ms pattern mask, then number entry (keyboard digits of any script,
// Backspace, Enter; or the on-screen keypad) for up to 10 s. If time runs out, whatever
// was typed is sent with confirmed=false. The server parses and scores the digits.
// Response: {events: [{estimate, rt, confirmed, flash_ms}], interruptions} in display order.
TaskViews["quantity_estimation"] = function (ctx) {
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s) => ctx.root.querySelector(s);
  const dotsG = $("#qe-dots"), maskG = $("#qe-mask"), fix = $("#qe-fix");
  const entry = $("#qe-entry"), valueEl = $("#qe-value");
  const flashMs = ctx.item.flash_ms || 200, limit = ctx.item.limit_ms || 10000;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const frame = () => new Promise((r) => requestAnimationFrame(r));
  const isDigit = (c) => /^\p{Nd}$/u.test(c);
  let interruptions = 0, finished = false, sink = null;
  const onVis = () => { if (document.hidden) interruptions++; };

  function el(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function drawMask() {
    // Random grey squares over the whole field; it only hides after-images, nothing is scored.
    const parts = [];
    for (let i = 0; i < 260; i++) {
      const s = 14 + Math.random() * 30, g = Math.round(60 + Math.random() * 150);
      parts.push(el("rect", { x: Math.random() * 800 - s / 2, y: Math.random() * 500 - s / 2, width: s, height: s,
                              fill: `rgb(${g},${g},${g})` }));
    }
    maskG.replaceChildren(...parts);
  }

  const send = (cmd) => { if (sink) sink(cmd); };
  const onKey = (e) => {
    if (e.repeat || !sink) return;
    if (e.key === "Enter") { e.preventDefault(); send("ok"); }
    else if (e.key === "Backspace") { e.preventDefault(); send("erase"); }
    else if (isDigit(e.key)) { e.preventDefault(); send(e.key); }
  };
  const wire = (b, cmd) => {
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); send(cmd); });
    b.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault(); e.stopPropagation();
      if (!e.repeat) send(cmd);
    });
  };
  ctx.root.querySelectorAll("[data-digit]").forEach((b) => wire(b, b.dataset.digit));
  wire($("#qe-erase"), "erase");
  wire($("#qe-ok"), "ok");

  function ask() {
    return new Promise((resolve) => {
      let typed = "";
      valueEl.textContent = "";
      entry.hidden = false;
      const t0 = performance.now();
      const end = (confirmed) => {
        clearTimeout(timer); sink = null; entry.hidden = true;
        resolve({ estimate: typed || null, rt: Math.round(performance.now() - t0), confirmed });
      };
      const timer = setTimeout(() => end(false), limit);
      sink = (cmd) => {
        if (cmd === "ok") { if (typed) end(true); return; }
        if (cmd === "erase") typed = [...typed].slice(0, -1).join("");
        else if ([...typed].length < 3) typed += cmd;
        valueEl.textContent = typed;
      };
    });
  }

  $("#qe-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    const out = [];
    for (const d of ctx.item.displays) {
      maskG.replaceChildren();
      fix.setAttribute("visibility", "visible");
      await wait(500);
      fix.setAttribute("visibility", "hidden");
      dotsG.replaceChildren(...d.dots.map(([x, y]) => el("circle", { cx: x, cy: y, r: d.r })));
      const on = await frame();
      await wait(Math.max(0, flashMs - 8));
      dotsG.replaceChildren();
      drawMask();
      const off = await frame();
      await wait(300);
      maskG.replaceChildren();
      const r = await ask();
      r.flash_ms = Math.round(off - on);
      out.push(r);
    }
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    if (!finished) { finished = true; ctx.finish({ events: out, interruptions }, false); }
  }, { once: true });
};
