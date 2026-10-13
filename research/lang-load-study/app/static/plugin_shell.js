// Runs one library task: hands the task its item and text, starts the time limit,
// and when the task calls finish() either asks for effort (study) or shows the score (try page).
(function () {
  // First code point (the zero) of the digit runs people may type in instead of 0-9.
  const ZEROS = [0x660, 0x6F0, 0x7C0, 0x966, 0x9E6, 0xA66, 0xAE6, 0xB66, 0xBE6, 0xC66, 0xCE6,
    0xD66, 0xDE6, 0xE50, 0xED0, 0xF20, 0x1040, 0x1090, 0x17E0, 0x1810, 0xFF10];
  function asciiDigit(ch) {
    const c = ch.codePointAt(0);
    for (const z of ZEROS) if (c >= z && c < z + 10) return String(c - z);
    return ch;
  }
  const T = window.TRIAL;
  const view = window.TaskViews[T.task];
  const status = document.getElementById("status");
  let done = false, timer = null;

  async function finish(response, timedOut) {
    if (done || (window.Study && window.Study.stopped())) return;
    done = true;
    clearTimeout(timer);
    if (T.tryMode) {
      const res = await fetch(`/try/${T.task}/score`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_id: T.imageId, response })
      });
      const out = document.getElementById("try-result");
      out.hidden = false;
      out.textContent = res.ok ? JSON.stringify(await res.json(), null, 1) : "Scoring failed";
      return;
    }
    Study.askEffort({ response, timed_out: !!timedOut, rt_ms: ctx.rt() }, timedOut ? T.msgTimeout : "");
  }

  const t0 = performance.now();
  const ctx = {
    item: T.item, text: T.text, imgUrl: T.imgUrl, lang: document.documentElement.lang,
    // True on the practice item (and on the try page): the only place correctness feedback belongs.
    practice: T.practice,
    root: document.getElementById("task-root"),
    status: (msg) => { status.textContent = msg || ""; },
    finish,
    // Default reaction time: from page start; tasks may pass their own in the response.
    rt: () => Math.round(performance.now() - t0),
  };
  // Digits typed in another script (٣, ৩, ३ ...) become 0-9 as they are typed.
  ctx.root.addEventListener("input", (e) => {
    const el = e.target;
    if (!("value" in el) || typeof el.value !== "string") return;
    const fixed = el.value.replace(/\p{Nd}/gu, asciiDigit);
    if (fixed !== el.value) el.value = fixed;
  }, true);
  if (!view) { status.textContent = "Task view missing"; return; }
  // The time limit runs from the person's first action in the task (normally pressing
  // Start), so reading the instructions does not count against it.
  timer = setTimeout(() => finish(null, true), T.timeout);
  const restart = () => { clearTimeout(timer); timer = setTimeout(() => finish(null, true), T.timeout); };
  ctx.root.addEventListener("pointerdown", restart, { once: true, capture: true });
  document.addEventListener("keydown", restart, { once: true, capture: true });
  view(ctx);
})();
