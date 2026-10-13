// Shared by the Corsi, reading, rule and operation-span trials and the plugin shell:
// tab-switch counting and the 1-9 effort rating that sends the trial. The stop buttons,
// the session deadline and retrying a failed save live in session.js.
window.Study = (function () {
  const T = window.TRIAL;
  // The task library's try pages have no session: nothing is saved there.
  const Session = window.Session || { stopped: () => false, setPartial() {}, submitTrial() {} };
  let focusLost = 0;
  // Leaving the tab mid-trial is recorded so the trial can be flagged in analysis.
  document.addEventListener("visibilitychange", () => { if (document.hidden) focusLost += 1; });

  // What a stop sends for the trial on screen: the scripts call this as the response
  // grows, so an unfinished trial is kept rather than lost.
  function setPartial(fn) {
    Session.setPartial(() => ({ focus_lost: focusLost, ...fn() }));
  }

  function askEffort(result, message) {
    if (Session.stopped()) return;
    // The response is complete; only the effort rating is still missing.
    setPartial(() => ({ ...result, complete: true }));
    const status = document.getElementById("status");
    if (message) status.textContent = message;
    const form = document.getElementById("effort");
    form.hidden = false;
    form.querySelector("input").focus();
    form.addEventListener("submit", (evt) => {
      evt.preventDefault();
      form.querySelector("button").disabled = true;
      const effort = Number(new FormData(form).get("effort"));
      Session.submitTrial({ trial_index: T.index, effort, focus_lost: focusLost, ...result });
    }, { once: true });
  }

  return { askEffort, setPartial, stopped: () => Session.stopped() };
})();
