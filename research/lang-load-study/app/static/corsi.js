// Corsi trial: after "Start", the squares light up one by one (500 ms on,
// 500 ms off). Then the person clicks them back in the order the clue asked
// for. Time runs from the end of the sequence to the last click.
(function () {
  const T = window.TRIAL;
  const blocks = [...document.querySelectorAll(".corsi-block")];
  const start = document.getElementById("corsi-start");
  const status = document.getElementById("status");
  const clicks = [];
  let t0 = null, timer = null, done = false;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  async function play() {
    start.hidden = true;
    await wait(600);
    for (const i of T.sequence) {
      blocks[i].classList.add("lit");
      await wait(500);
      blocks[i].classList.remove("lit");
      await wait(500);
    }
    blocks.forEach((b) => (b.disabled = false));
    status.textContent = T.msgGo;
    t0 = performance.now();
    timer = setTimeout(() => finish(true), T.timeout);
  }

  function finish(timedOut) {
    if (done || window.Study.stopped()) return;
    done = true;
    clearTimeout(timer);
    blocks.forEach((b) => (b.disabled = true));
    Study.askEffort({ response: clicks, rt_ms: timedOut ? null : Math.round(performance.now() - t0),
                      timed_out: timedOut }, timedOut ? T.msgTimeout : "");
  }

  blocks.forEach((b) => b.addEventListener("click", () => {
    if (done || t0 === null) return;
    clicks.push(Number(b.dataset.i));
    b.classList.add("picked");
    setTimeout(() => b.classList.remove("picked"), 180);
    if (clicks.length === T.sequence.length) finish(false);
  }));
  start.addEventListener("click", play, { once: true });
})();
