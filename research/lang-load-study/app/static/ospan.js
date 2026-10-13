// Operation span with words: for each step, judge a sum (up to 8 s), then see a
// word for 1 s. Afterwards click the words back in order. Time runs over recall only.
(function () {
  const T = window.TRIAL;
  const $ = (id) => document.getElementById(id);
  const sumPhase = $("sum-phase"), word = $("word"), recall = $("recall-phase");
  const answers = [], recalled = [];
  let t0 = null, done = false, timer = null;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  function judge() {
    return new Promise((resolve) => {
      const btns = [...sumPhase.querySelectorAll(".pick")];
      const limit = setTimeout(() => { cleanup(); resolve(null); }, 8000);
      const on = (evt) => { cleanup(); resolve(evt.currentTarget.dataset.v === "1"); };
      function cleanup() { clearTimeout(limit); btns.forEach((b) => b.removeEventListener("click", on)); }
      btns.forEach((b) => b.addEventListener("click", on));
    });
  }

  async function run() {
    $("ospan-start").hidden = true;
    for (let k = 0; k < T.sums.length; k++) {
      $("sum").textContent = T.sums[k];
      sumPhase.hidden = false;
      answers.push(await judge());
      sumPhase.hidden = true;
      word.textContent = T.words[k];
      word.hidden = false;
      await wait(1000);
      word.hidden = true;
      await wait(250);
    }
    recall.hidden = false;
    t0 = performance.now();
    timer = setTimeout(() => finish(true), T.timeout);
  }

  function show() {
    $("picked").textContent = recalled.map((k) =>
      document.querySelector(`.choice-word[data-k="${k}"]`).textContent).join(" → ");
  }

  function finish(timedOut) {
    if (done || window.Study.stopped()) return;
    done = true;
    clearTimeout(timer);
    recall.querySelectorAll("button").forEach((b) => (b.disabled = true));
    Study.askEffort({ response: { recall: recalled, sums: answers },
                      rt_ms: timedOut ? null : Math.round(performance.now() - t0),
                      timed_out: timedOut }, timedOut ? T.msgTimeout : "");
  }

  document.querySelectorAll(".choice-word").forEach((b) => b.addEventListener("click", () => {
    if (done || recalled.includes(Number(b.dataset.k))) return;
    recalled.push(Number(b.dataset.k));
    b.disabled = true;
    show();
    if (recalled.length === T.length) finish(false);
  }));
  $("undo").addEventListener("click", () => {
    const k = recalled.pop();
    if (k !== undefined) document.querySelector(`.choice-word[data-k="${k}"]`).disabled = false;
    show();
  });
  $("ospan-start").addEventListener("click", run, { once: true });
})();
