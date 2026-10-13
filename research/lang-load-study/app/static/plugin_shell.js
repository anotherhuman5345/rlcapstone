// Runs one library task: hands the task its item and text, starts the time limit,
// and when the task calls finish() either asks for effort (study) or shows the score (try page).
//
// Phases and timing (all ms from page load, sent as the "timing" envelope):
//   instructions -> start: one controlled transition, made by the person's first pointer
//   or key action in the task (normally pressing Start) or by the view calling
//   ctx.start(). It happens once; a later input of another kind cannot restart it.
//   The task time limit runs from the start, so reading instructions never counts.
//   first_response: the first pointer/key action after the start.
//   complete: when the view calls finish().
// The hard session deadline (session.js) is separate and ends the page regardless.
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
  const Session = window.Session; // absent on the try pages
  let done = false, timer = null;
  const tPage = performance.now();
  let tStart = null, tFirst = null, tDone = null;
  const ms = (t) => (t === null ? null : Math.round(t - tPage));

  function timing() {
    return { instr_ms: tStart === null ? null : Math.round(tStart - tPage), start_ms: ms(tStart),
             first_response_ms: ms(tFirst), complete_ms: ms(tDone) };
  }
  // Block duration from the start (from page load if the view never started).
  function rt() { return Math.round((tDone ?? performance.now()) - (tStart ?? tPage)); }

  function start() {
    if (tStart !== null || done) return;
    tStart = performance.now();
    timer = setTimeout(() => finish(null, true), T.timeout);
  }

  // One listener for both input kinds: the first action starts, the next is the first response.
  function onInput(evt) {
    if (evt.type === "keydown" && evt.repeat) return;
    if (evt.target && evt.target.closest && evt.target.closest("#effort, .stop-buttons")) return;
    if (tStart === null) start();
    else if (tFirst === null) tFirst = performance.now();
  }

  async function finish(response, timedOut) {
    if (done || (Session && Session.stopped())) return;
    done = true;
    tDone = performance.now();
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
    Study.askEffort({ response, timed_out: !!timedOut, rt_ms: rt(), timing: timing() },
                    timedOut ? T.msgTimeout : "");
  }

  const ctx = {
    item: T.item, text: T.text, imgUrl: T.imgUrl, lang: document.documentElement.lang,
    // True on the practice item (and on the try page): the only place correctness feedback belongs.
    practice: T.practice,
    root: document.getElementById("task-root"),
    status: (msg) => { status.textContent = msg || ""; },
    finish,
    // Views with their own start screen may call this; it is a no-op after the first time.
    start,
    // Views may set ctx.partial = () => response-so-far; a stop sends it with the timing.
    partial: null,
    // Block duration so far, from the start.
    rt,
  };
  if (!T.tryMode) {
    Study.setPartial(() => ({ response: ctx.partial ? ctx.partial() : null, timed_out: false,
                              rt_ms: rt(), timing: timing() }));
  }
  // Digits typed in another script (٣, ৩, ३ ...) become 0-9 as they are typed.
  ctx.root.addEventListener("input", (e) => {
    const el = e.target;
    if (!("value" in el) || typeof el.value !== "string") return;
    const fixed = el.value.replace(/\p{Nd}/gu, asciiDigit);
    if (fixed !== el.value) el.value = fixed;
  }, true);
  if (!view) {
    status.textContent = "Task view missing";
    if (Session) Session.stop("technical_failure");
    return;
  }
  ctx.root.addEventListener("pointerdown", onInput, { capture: true });
  document.addEventListener("keydown", onInput, { capture: true });
  view(ctx);
})();
