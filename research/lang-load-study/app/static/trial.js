// One trial: show clue + image together, time until the correct click,
// then collect a 1-9 mental-effort rating and send everything to the server.
(function () {
  const T = window.TRIAL;
  const img = document.getElementById("stim");
  const clue = document.getElementById("clue");
  const mark = document.getElementById("mark");
  const status = document.getElementById("status");
  const effortForm = document.getElementById("effort");
  const TOLERANCE = 1.6; // must match HIT_TOLERANCE on the server

  let t0 = null, done = false, falseClicks = 0, result = null, timer = null;

  function begin() {
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
    if (done || t0 === null) return;
    const p = toNatural(evt);
    const dist = Math.hypot(p.x - T.target.x, p.y - T.target.y);
    if (dist <= T.target.r * TOLERANCE) {
      const rt = performance.now() - t0;
      mark.style.left = p.px + "px";
      mark.style.top = p.py + "px";
      mark.hidden = false;
      finish({ rt_ms: Math.round(rt), click_x: p.x, click_y: p.y, timed_out: false }, T.msgFound);
    } else {
      falseClicks += 1;
    }
  });

  effortForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const effort = Number(new FormData(effortForm).get("effort"));
    const btn = effortForm.querySelector("button");
    btn.disabled = true;
    const res = await fetch("/api/trial", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trial_index: T.index, false_clicks: falseClicks, effort, ...result })
    });
    if (res.ok) {
      const data = await res.json();
      window.location.href = data.next;
    } else {
      window.location.href = "/trial"; // resync if the trial was already recorded
    }
  });

  if (img.complete && img.naturalWidth) begin();
  else img.addEventListener("load", begin, { once: true });
})();
