// Tone detection during learning: a 30 s study phase (6 symbol-word pairs, 5 s each) with
// 5 beeps scheduled ahead on the Web Audio clock, then a 6-question recall test.
// Beep presses: Space, or pointerdown on the Tone button (keyboard "clicks" on it are ignored
// so one press is never counted twice). Press times are ms from the study start, which is
// aligned to the audio clock. Response: {presses, answers, test_rts, audio_ok, ...}.
TaskViews["tone_detection"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, words = ctx.text.words;
  const COLORS = ["#C0392B", "#1F6FB2", "#2E8B57"];
  function star() {
    const p = [];
    for (let k = 0; k < 10; k++) {
      const r = k % 2 ? 17 : 42, a = -Math.PI / 2 + k * Math.PI / 5;
      p.push((50 + r * Math.cos(a)).toFixed(1) + "," + (52 + r * Math.sin(a)).toFixed(1));
    }
    return '<polygon points="' + p.join(" ") + '"/>';
  }
  const SHAPES = [
    '<circle cx="50" cy="50" r="38"/>',
    '<rect x="14" y="14" width="72" height="72"/>',
    '<polygon points="50,10 90,86 10,86"/>',
    '<polygon points="50,8 92,50 50,92 8,50"/>',
    star(),
    '<polygon points="38,10 62,10 62,38 90,38 90,62 62,62 62,90 38,90 38,62 10,62 10,38 38,38"/>',
    '<polygon points="50,8 86,29 86,71 50,92 14,71 14,29"/>',
    '<polygon points="10,38 55,38 55,15 92,50 55,85 55,62 10,62"/>',
  ];
  const drawSym = (svg, s) => { svg.innerHTML = '<g fill="' + COLORS[Math.floor(s / 8) % 3] + '">' + SHAPES[s % 8] + "</g>"; };

  let ac = null, audioOk = false, ended = false, p0 = 0, studying = false;
  const presses = [], timers = [];
  function audio() {
    if (ac) return ac;
    try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { ac = null; }
    return ac;
  }
  // resume() can stay pending without a user gesture; never let it block the trial.
  const resume = (a) => Promise.race([a.resume(), new Promise((r) => setTimeout(r, 1000))]);
  function beep(at) {
    const o = ac.createOscillator(), g = ac.createGain(), len = it.tone_len_ms / 1000;
    o.frequency.value = it.tone_hz;
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(0.35, at + 0.01);
    g.gain.setValueAtTime(0.35, at + len - 0.01);
    g.gain.linearRampToValueAtTime(0, at + len);
    o.connect(g); g.connect(ac.destination);
    o.start(at); o.stop(at + len + 0.02);
  }

  $("#td-test").addEventListener("click", async () => {
    const a = audio();
    if (!a) { ctx.status(ctx.text.no_audio); return; }
    try { await resume(a); beep(a.currentTime + 0.05); } catch (e) { ctx.status(ctx.text.no_audio); }
  });

  function press() {
    if (!studying) return;
    presses.push(Math.round(performance.now() - p0));
  }
  const onKey = (e) => {
    if (e.code !== "Space" && e.key !== " ") return;
    e.preventDefault();
    if (!e.repeat) press();
  };
  $("#td-tone").addEventListener("pointerdown", (e) => { e.preventDefault(); press(); });

  $("#td-start").addEventListener("click", async () => {
    $("#td-setup").hidden = true;
    if (document.activeElement) document.activeElement.blur();
    const a = audio();
    let a0 = null;
    if (a) {
      try {
        await resume(a);
        a0 = a.currentTime + 0.3;
        const ts = a.getOutputTimestamp ? a.getOutputTimestamp() : null;
        p0 = ts && ts.performanceTime ? ts.performanceTime + (a0 - ts.contextTime) * 1000
                                      : performance.now() + 300;
        it.tones_ms.forEach((t) => beep(a0 + t / 1000));
        audioOk = a.state === "running";
      } catch (e) { audioOk = false; }
    }
    if (!audioOk) { p0 = performance.now() + 300; ctx.status(ctx.text.no_audio); }
    const at = (ms, fn) => timers.push(setTimeout(fn, Math.max(0, p0 + ms - performance.now())));
    studying = true;
    document.addEventListener("keydown", onKey);
    $("#td-study").hidden = false;
    it.pairs.forEach((pr, k) => at(k * it.study_ms, () => { drawSym($("#td-sym"), pr.symbol); $("#td-word").textContent = words[pr.word]; }));
    at(it.pairs.length * it.study_ms, startTest);
  }, { once: true });

  function startTest() {
    studying = false;
    document.removeEventListener("keydown", onKey);
    $("#td-study").hidden = true;
    $("#td-test-phase").hidden = false;
    const answers = [], rts = [];
    const opts = $("#td-opts");
    let k = 0, t0 = 0;
    opts.innerHTML = "";
    it.options.forEach((w, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = '<span class="n">' + (i + 1) + "</span>";
      b.appendChild(document.createTextNode(words[w]));
      b.addEventListener("click", () => choose(w));
      opts.appendChild(b);
    });
    const onDigit = (e) => {
      if (e.repeat) return;
      const n = parseInt(e.key, 10);
      if (n >= 1 && n <= it.options.length) choose(it.options[n - 1]);
    };
    document.addEventListener("keydown", onDigit);
    timers.push(setTimeout(() => finishTest(true), Math.max(0, p0 + it.limit_ms - performance.now())));
    function show() { drawSym($("#td-tsym"), it.pairs[it.test_order[k]].symbol); t0 = performance.now(); }
    function choose(w) {
      if (ended || k >= it.test_order.length) return;
      answers.push(w);
      rts.push(Math.round(performance.now() - t0));
      k += 1;
      if (k < it.test_order.length) { show(); return; }
      finishTest(false);
    }
    function finishTest(timedOut) {
      document.removeEventListener("keydown", onDigit);
      end({ presses, answers, test_rts: rts, audio_ok: audioOk,
            audio_latency_ms: ac ? Math.round(((ac.outputLatency || 0) + (ac.baseLatency || 0)) * 1000) : null },
          timedOut);
    }
    show();
  }

  function end(response, timedOut) {
    if (ended) return;
    ended = true;
    timers.forEach(clearTimeout);
    document.removeEventListener("keydown", onKey);
    if (ac) { try { ac.close(); } catch (e) { /* ignore */ } }
    ctx.finish(response, !!timedOut);
  }
};
