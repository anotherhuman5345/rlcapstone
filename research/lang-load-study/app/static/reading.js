// Reading trial: time runs from when the passage appears to the answer.
(function () {
  const T = window.TRIAL;
  const form = document.getElementById("reading");
  let t0 = null, done = false;
  requestAnimationFrame(() => { t0 = performance.now(); });
  const timer = setTimeout(() => finish(null, true), T.timeout);

  function finish(answer, timedOut) {
    if (done || window.Study.stopped()) return;
    done = true;
    clearTimeout(timer);
    form.querySelectorAll("input, button").forEach((el) => (el.disabled = true));
    Study.askEffort({ response: answer, rt_ms: timedOut ? null : Math.round(performance.now() - t0),
                      timed_out: timedOut }, timedOut ? T.msgTimeout : "");
  }

  form.addEventListener("submit", (evt) => {
    evt.preventDefault();
    finish(Number(new FormData(form).get("answer")), false);
  });
})();
