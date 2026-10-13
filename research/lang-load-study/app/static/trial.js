// One trial: show clue + image together, time until the correct click,
// then collect a 1-9 mental-effort rating and send everything to the server.
// Every click is kept (position and time from onset), so first-click time, first-click
// correctness and wrong clicks can be scored on the server.
(function () {
  const T = window.TRIAL;
  const img = document.getElementById("stim");
  const clue = document.getElementById("clue");
  const mark = document.getElementById("mark");
  const status = document.getElementById("status");
  const effortForm = document.getElementById("effort");
  const TOLERANCE = 1.6; // must match HIT_TOLERANCE on the server

  let t0 = null, done = false, falseClicks = 0, result = null, timer = null;
  const clicks = []; // {x, y, t_ms} in natural image pixels, ms since onset
  let focusLost = 0; // leaving the tab mid-trial is recorded and flagged in analysis
  document.addEventListener("visibilitychange", () => { if (document.hidden) focusLost += 1; });

  // What a stop (exhausted, withdrawn, time cap) sends for this trial: the finished
  // result if only the effort rating is missing, otherwise the clicks so far.
  Session.setPartial(() => result
    ? { ...result, false_clicks: falseClicks, clicks, focus_lost: focusLost, complete: true }
    : { clicks, false_clicks: falseClicks, focus_lost: focusLost, timed_out: false,
        rt_ms: t0 === null ? null : Math.round(performance.now() - t0) });

  function begin() {
    if (Session.stopped()) return;
    clue.hidden = false;
    img.classList.add("live");
    // Start the clock on the next frame, once clue and image are painted.
    requestAnimationFrame(() => {
      t0 = performance.now();
      timer = setTimeout(timeOut, T.timeout);
    });
  }

  function toNatural(evt) {
    const r = img.getBoundingClientRect();
    return {
      x: (evt.clientX - r.left) * (T.naturalW / r.width),
      y: (evt.clientY - r.top) * (T.naturalH / r.height),
      px: evt.clientX - r.left, py: evt.clientY - r.top
    };
  }

  function finish(res, message) {
    if (Session.stopped()) return;
    done = true;
    clearTimeout(timer);
    result = res;
    status.textContent = message;
    effortForm.hidden = false;
    effortForm.querySelector("input").focus();
  }

  function timeOut() {
    if (done) return;
    finish({ rt_ms: null, click_x: null, click_y: null, timed_out: true }, T.msgTimeout);
  }

  img.addEventListener("pointerdown", (evt) => {
    if (done || t0 === null || Session.stopped()) return;
    const p = toNatural(evt);
    const rt = Math.round(performance.now() - t0);
    clicks.push({ x: p.x, y: p.y, t_ms: rt });
    const dist = Math.hypot(p.x - T.target.x, p.y - T.target.y);
    if (dist <= T.target.r * TOLERANCE) {
      mark.style.left = p.px + "px";
      mark.style.top = p.py + "px";
      mark.hidden = false;
      finish({ rt_ms: rt, click_x: p.x, click_y: p.y, timed_out: false }, T.msgFound);
    } else {
      falseClicks += 1;
    }
  });

  effortForm.addEventListener("submit", (evt) => {
    evt.preventDefault();
    const effort = Number(new FormData(effortForm).get("effort"));
    effortForm.querySelector("button").disabled = true;
    Session.submitTrial({ trial_index: T.index, false_clicks: falseClicks, clicks, effort,
                          focus_lost: focusLost, ...result });
  });

  // A picture that cannot load makes the trial impossible: record it, do not guess.
  img.addEventListener("error", () => Session.stop("technical_failure"), { once: true });
  if (img.complete && img.naturalWidth) begin();
  else if (img.complete) Session.stop("technical_failure"); // failed before this script ran
  else img.addEventListener("load", begin, { once: true });
})();
