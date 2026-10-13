// Tracking plus arithmetic: a requestAnimationFrame loop draws the target from the item's
// sum-of-sines path using elapsed time (not frame count). The cursor follows the pointer
// over the canvas, or moves at a fixed speed while an arrow key / arrow button is held.
// Cursor position is sampled every item.sample_ms. Sums appear at their scheduled times and
// stay up to item.window_ms. Response: {samples:[[t,x,y]], answers:[{value,rt}], frame_gaps, input}.
TaskViews["tracking_arithmetic"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, H = it.height;
  const cv = $("#tr-canvas"), g = cv.getContext("2d");
  const sumEl = $("#tr-sum"), optsEl = $("#tr-opts");
  const KEY_SPEED = 0.45;                       // field widths per second
  const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  const KEYMAP = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
  const held = new Set();
  const samples = [], answers = it.sums.map(() => ({ value: null, rt: null }));
  const inputs = new Set(), shownSet = new Set();
  let running = false, ended = false, t0 = 0, last = 0, nextSample = 0, frameGaps = 0, raf = 0;
  let cur = null, active = -1, shownAt = 0;

  function target(tms) {
    const t = tms / 1000;
    let x = 0.5, y = H / 2;
    for (const [a, f, p] of it.path.x) x += a * Math.sin(2 * Math.PI * f * t + p);
    for (const [a, f, p] of it.path.y) y += a * Math.sin(2 * Math.PI * f * t + p);
    return [x, y];
  }
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  function draw(tx, ty) {
    const W = cv.width;
    g.clearRect(0, 0, W, cv.height);
    g.fillStyle = "#4FA3E0";
    g.beginPath(); g.arc(tx * W, ty * W, 0.03 * W, 0, 2 * Math.PI); g.fill();
    if (cur) {
      g.strokeStyle = "#F2C94C"; g.lineWidth = 4;
      const cx = cur[0] * W, cy = cur[1] * W, r = 14;
      g.beginPath(); g.moveTo(cx - r, cy); g.lineTo(cx + r, cy); g.moveTo(cx, cy - r); g.lineTo(cx, cy + r); g.stroke();
    }
  }

  // Pointer (mouse hover or touch drag) over the canvas sets the cursor directly.
  cv.addEventListener("pointermove", (e) => {
    if (!running) return;
    const r = cv.getBoundingClientRect();
    cur = [clamp((e.clientX - r.left) / r.width, 0, 1), clamp((e.clientY - r.top) / r.width, 0, H)];
    inputs.add(e.pointerType || "pointer");
  });
  cv.addEventListener("pointerdown", (e) => { if (running) e.preventDefault(); });

  const onKeyDown = (e) => {
    if (KEYMAP[e.key]) { e.preventDefault(); if (!e.repeat) held.add(KEYMAP[e.key]); inputs.add("keys"); return; }
    if (e.repeat || !running) return;
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= 3) answer(n - 1);
  };
  const onKeyUp = (e) => { if (KEYMAP[e.key]) held.delete(KEYMAP[e.key]); };
  ctx.root.querySelectorAll("[data-dir]").forEach((b) => {
    const d = b.dataset.dir;
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); held.add(d); inputs.add("buttons"); try { b.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ } });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach((ev) => b.addEventListener(ev, () => held.delete(d)));
  });

  function showSum(i) {
    active = i;
    shownAt = performance.now();
    const s = it.sums[i];
    sumEl.textContent = s.a + " + " + s.b + " = ?";
    optsEl.innerHTML = "";
    s.options.forEach((v, k) => {
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = '<span class="n">' + (k + 1) + "</span>" + v;
      b.addEventListener("click", () => answer(k));
      optsEl.appendChild(b);
    });
  }
  function clearSum() { active = -1; sumEl.textContent = ""; optsEl.innerHTML = ""; }
  function answer(k) {
    if (active < 0 || ended) return;
    answers[active] = { value: it.sums[active].options[k], rt: Math.round(performance.now() - shownAt) };
    clearSum();
  }

  function frame(now) {
    if (ended) return;
    const t = now - t0;
    const dt = Math.min(now - last, 100) / 1000;
    if (now - last > 50) frameGaps += 1;
    last = now;
    if (held.size && cur) {
      let dx = 0, dy = 0;
      held.forEach((d) => { dx += DIRS[d][0]; dy += DIRS[d][1]; });
      cur = [clamp(cur[0] + dx * KEY_SPEED * dt, 0, 1), clamp(cur[1] + dy * KEY_SPEED * dt, 0, H)];
    }
    // Sums: show at their time, drop when the window runs out (answer stays null).
    for (let i = 0; i < it.sums.length; i++) {
      if (shownSet.has(i) || t < it.sums[i].t) continue;
      shownSet.add(i);
      if (t < it.sums[i].t + it.window_ms) showSum(i);
    }
    if (active >= 0 && t >= it.sums[active].t + it.window_ms) clearSum();
    while (nextSample <= t && nextSample <= it.duration_ms) {
      samples.push([Math.round(nextSample), +cur[0].toFixed(4), +cur[1].toFixed(4)]);
      nextSample += it.sample_ms;
    }
    if (t >= it.duration_ms) { end(); return; }
    const [tx, ty] = target(t);
    draw(tx, ty);
    raf = requestAnimationFrame(frame);
  }
  draw(...target(0));
  $("#tr-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    if (document.activeElement) document.activeElement.blur();
    cur = target(0);
    running = true;
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
    t0 = last = performance.now();
    raf = requestAnimationFrame(frame);
  }, { once: true });

  function end() {
    if (ended) return;
    ended = true;
    running = false;
    cancelAnimationFrame(raf);
    document.removeEventListener("keydown", onKeyDown);
    document.removeEventListener("keyup", onKeyUp);
    clearSum();
    ctx.finish({ samples, answers, frame_gaps: frameGaps, input: [...inputs].sort().join("+") || "none" }, false);
  }
};
