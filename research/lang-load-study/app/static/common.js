// Shared by the Corsi and reading trials: tab-switch counting, the
// "I'm exhausted" button, and the 1-9 effort rating that sends the trial.
window.Study = (function () {
  const T = window.TRIAL;
  let focusLost = 0, stopped = false;
  // Leaving the tab mid-trial is recorded so the trial can be flagged in analysis.
  document.addEventListener("visibilitychange", () => { if (document.hidden) focusLost += 1; });

  function askEffort(result, message) {
    const status = document.getElementById("status");
    if (message) status.textContent = message;
    const form = document.getElementById("effort");
    form.hidden = false;
    form.querySelector("input").focus();
    form.addEventListener("submit", async (evt) => {
      evt.preventDefault();
      form.querySelector("button").disabled = true;
      const effort = Number(new FormData(form).get("effort"));
      const res = await fetch("/api/trial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trial_index: T.index, effort, focus_lost: focusLost, ...result })
      });
      window.location.href = res.ok ? (await res.json()).next : "/trial";
    }, { once: true });
  }

  const quit = document.getElementById("quit");
  if (quit) {
    quit.addEventListener("click", async () => {
      if (!window.confirm(T.msgQuitConfirm)) return;
      stopped = true;
      const res = await fetch("/api/quit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trial_index: T.index })
      });
      window.location.href = res.ok ? (await res.json()).next : "/final";
    });
  }
  return { askEffort, stopped: () => stopped };
})();
