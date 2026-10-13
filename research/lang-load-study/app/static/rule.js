// Rule card: read the rule, look at the card, click group A or B.
(function () {
  const T = window.TRIAL;
  const picks = [...document.querySelectorAll(".rule-answer .pick")];
  let t0 = null, done = false;
  requestAnimationFrame(() => { t0 = performance.now(); });
  const timer = setTimeout(() => finish(null, true), T.timeout);

  function finish(answer, timedOut) {
    if (done || window.Study.stopped()) return;
    done = true;
    clearTimeout(timer);
    picks.forEach((b) => (b.disabled = true));
    Study.askEffort({ response: answer, rt_ms: timedOut ? null : Math.round(performance.now() - t0),
                      timed_out: timedOut }, timedOut ? T.msgTimeout : "");
  }
  picks.forEach((b) => b.addEventListener("click", () => finish(b.dataset.v, false)));
})();
