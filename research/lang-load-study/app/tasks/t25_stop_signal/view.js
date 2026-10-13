// Stop-signal: 32 events. Each: 500 ms blank, 500 ms fixation cross, then the arrow for
// up to 1000 ms. The first left/right answer ends the event (on a stop event that is a
// failed stop). Stop events: at the current SSD the arrow turns red inside a red ring and,
// if sound is on, a 100 ms 1000 Hz beep plays (Web Audio, started on the Start click);
// a press before the SSD cancels the signal. Staircase: start 250 ms, +50 after a
// successful stop, -50 after a failed one, bounded to [50, 900]; the server re-runs it.
// Response: {events: [{key, rt, ssd}], audio, interruptions} in event order.
TaskViews["stop_signal"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const fix = $("#ss-fix"), ring = $("#ss-ring"), arrow = $("#ss-arrow");
  const btns = [...ctx.root.querySelectorAll("[data-key]")];
  const limit = ctx.item.limit_ms || 1000;
  const S = ctx.item.ssd || { start: 250, step: 50, min: 50, max: 900 };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const vis = (el, on) => el.setAttribute("visibility", on ? "visible" : "hidden");
  let interruptions = 0, finished = false, sink = null, audio = null;
  const onVis = () => { if (document.hidden) interruptions++; };

  const press = (key) => { if (sink) sink(key); };
  const onKey = (e) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    if (!e.repeat) press(e.key === "ArrowLeft" ? "left" : "right");
  };
  btns.forEach((b) => {
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); press(b.dataset.key); });
    b.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      if (!e.repeat) press(b.dataset.key);
    });
  });

  function beep() {
    if (!audio) return;
    try {
      const t = audio.currentTime, osc = audio.createOscillator(), gain = audio.createGain();
      osc.frequency.value = 1000;
      gain.gain.setValueAtTime(0.25, t);
      gain.gain.setValueAtTime(0, t + 0.1);
      osc.connect(gain).connect(audio.destination);
      osc.start(t); osc.stop(t + 0.12);
    } catch (err) { audio = null; }
  }

  // One event: resolves with {key, rt}; on stop events the signal fires at `ssd` ms unless
  // a key came first.
  function runEvent(ev, ssd) {
    return new Promise((resolve) => {
      arrow.setAttribute("transform", ev.dir === "left" ? "rotate(180 200 150)" : "");
      arrow.setAttribute("fill", "#1d2731");
      vis(arrow, true);
      const t0 = performance.now();
      let sigTimer = null;
      if (ev.stop) sigTimer = setTimeout(() => { arrow.setAttribute("fill", "#c62828"); vis(ring, true); beep(); }, ssd);
      const end = (key) => {
        clearTimeout(timer); clearTimeout(sigTimer); sink = null;
        vis(arrow, false); vis(ring, false);
        resolve({ key, rt: key ? Math.round(performance.now() - t0) : null });
      };
      const timer = setTimeout(() => end(null), limit);
      sink = (key) => end(key);
    });
  }

  $("#ss-start").addEventListener("click", async (e) => {
    e.currentTarget.hidden = true;
    const soundBox = $("#ss-sound");
    if (soundBox.checked) {
      try { const AC = window.AudioContext || window.webkitAudioContext; audio = AC ? new AC() : null; if (audio) audio.resume(); }
      catch (err) { audio = null; }
    }
    soundBox.disabled = true;
    btns.forEach((b) => (b.disabled = false));
    document.addEventListener("keydown", onKey);
    document.addEventListener("visibilitychange", onVis);
    const out = [];
    let ssd = S.start;
    for (const ev of ctx.item.events) {
      vis(fix, false);
      await wait(500);
      vis(fix, true);
      await wait(500);
      vis(fix, false);
      const r = await runEvent(ev, ssd);
      r.ssd = ev.stop ? ssd : null;
      if (ev.stop) ssd = r.key === null ? Math.min(S.max, ssd + S.step) : Math.max(S.min, ssd - S.step);
      out.push(r);
    }
    btns.forEach((b) => (b.disabled = true));
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
    const audioOk = !!audio;
    if (audio) { try { audio.close(); } catch (err) { /* ignore */ } }
    if (!finished) { finished = true; ctx.finish({ events: out, audio: audioOk, interruptions }, false); }
  }, { once: true });
};
