// Shared by every timed screen (all trial pages, the plugin shell, fatigue check-ins).
// - Hard deadline: the server sends the time left until the stored deadline (null before
//   the first scored stimulus). Refreshing never renews it. When it passes, every task
//   element is hidden and disabled at once, whatever the task is doing, and the session
//   stops with reason "time_cap".
// - Stop buttons: "I'm exhausted" (#quit) and "Stop / withdraw" (#withdraw).
// - Partial data: the page registers setPartial(fn); a stop sends whatever fn returns,
//   so an unfinished trial is kept rather than lost.
// - Saving: submitTrial() retries on network or server errors with the same body. The
//   server stores one answer per trial and returns it again for a repeat, so a retry can
//   never record twice. An unsent answer also survives a reload (localStorage).
window.Session = (function () {
  const S = window.SESSION || {};
  const PENDING = "study.pendingTrial";
  const loadedAt = performance.now();
  let stopped = false, partial = null;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  function post(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body) });
  }
  async function readJson(res) { try { return await res.json(); } catch (e) { return {}; } }
  function store(key, value) {
    try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, JSON.stringify(value)); }
    catch (e) { /* private mode: retrying in the page still works */ }
  }
  function load(key) { try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return null; } }
  function status(msg) { const el = document.getElementById("status"); if (el) el.textContent = msg; }

  function freeze(message) {
    // End presentation now: hide every task element and disable every control.
    const main = document.querySelector("main");
    if (!main) return;
    main.querySelectorAll("button, input, select, textarea").forEach((el) => { el.disabled = true; });
    main.classList.add("time-up");
    const note = document.createElement("p");
    note.className = "time-up-msg";
    note.setAttribute("role", "alert");
    note.textContent = message;
    main.appendChild(note);
  }

  async function stop(reason) {
    if (stopped) return;
    stopped = true;
    let body = { trial_index: S.index, reason, partial: null };
    try { body.partial = partial ? partial() : null; } catch (e) { body.partial = null; }
    let next = "/final";
    for (let k = 0; k < 4; k++) {
      try {
        const res = await post("/api/stop", body);
        const data = await readJson(res);
        if (data.next) next = data.next;
        if (res.status < 500) break;
      } catch (e) { /* offline: try again */ }
      await wait(1000 * (k + 1));
    }
    window.location.href = next;
  }

  async function submitTrial(body) {
    if (stopped) return;
    const pending = { sid: S.sid, body };
    store(PENDING, pending);
    for (let k = 0; ; k++) {
      try {
        const res = await post("/api/trial", body);
        if (res.status < 500) {
          // Stored (or already stored), or refused as out of phase: either way the
          // server says where to go. Nothing is retried after a 4xx.
          const data = await readJson(res);
          store(PENDING, null);
          window.location.href = data.next || "/trial";
          return;
        }
      } catch (e) { /* network error: retry below */ }
      if (stopped) return;
      status(S.msgSaving || "");
      await wait(Math.min(8000, 500 * 2 ** k));
    }
  }

  // An answer saved in this browser but never confirmed (the page was reloaded while
  // offline) is sent once more; the server ignores it if it is already stored.
  const leftover = load(PENDING);
  if (leftover && leftover.sid === S.sid && leftover.body) {
    post("/api/trial", leftover.body).then((res) => { if (res.status < 500) store(PENDING, null); })
      .catch(() => {});
  } else if (leftover) {
    store(PENDING, null);
  }

  function bind(id, reason, message) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", () => {
      if (stopped || !window.confirm(message)) return;
      stop(reason);
    });
  }
  bind("quit", "exhausted", S.msgQuitConfirm);
  bind("withdraw", "withdrawn", S.msgWithdrawConfirm);

  if (typeof S.remainingMs === "number") {
    // performance.now() is monotonic; a changed system clock cannot move the deadline.
    const deadline = loadedAt + S.remainingMs;
    const expire = () => {
      if (stopped || performance.now() < deadline) return;
      freeze(S.msgTimeUp || "");
      stop("time_cap");
    };
    setTimeout(expire, Math.max(0, S.remainingMs));
    // Background tabs may delay timers: check again every second and on return.
    setInterval(expire, 1000);
    document.addEventListener("visibilitychange", expire);
  }

  return {
    stopped: () => stopped,
    setPartial: (fn) => { partial = fn; },
    submitTrial,
    stop,
  };
})();
