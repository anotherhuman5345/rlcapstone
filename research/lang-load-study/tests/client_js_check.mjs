// Runs the shared browser scripts (session.js, common.js, plugin_shell.js) against a tiny
// fake DOM with a controllable clock. Called by tests/test_client_js.py; prints "ok <name>"
// for every check that passes and exits non-zero on the first failure.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const STATIC = new URL("../app/static/", import.meta.url);
const src = (name) => readFileSync(new URL(name, STATIC), "utf8");
const flush = () => new Promise((r) => setImmediate(r));

function element(id) {
  const listeners = {};
  const classes = new Set();
  return {
    id, hidden: false, disabled: false, textContent: "", children: [], listeners,
    classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c) },
    addEventListener(type, fn) { (listeners[type] ||= []).push(fn); },
    removeEventListener(type, fn) { listeners[type] = (listeners[type] || []).filter((f) => f !== fn); },
    dispatch(type, extra = {}) {
      const evt = { type, target: this, repeat: false, preventDefault() {}, ...extra };
      for (const fn of [...(listeners[type] || [])]) fn(evt);
    },
    querySelectorAll: () => [], querySelector: () => element("child"),
    appendChild(child) { this.children.push(child); }, setAttribute() {}, focus() {}, closest: () => null,
  };
}

function browser({ session, trial, fetchPlan = [] }) {
  let clock = 0, nextId = 1;
  const timers = new Map();
  const fetches = [];
  const els = { main: element("main"), status: element("status"), effort: element("effort"),
                "task-root": element("task-root"), quit: element("quit"), withdraw: element("withdraw") };
  const store = new Map();
  const document = element("document");
  Object.assign(document, {
    hidden: false, documentElement: { lang: "en" },
    getElementById: (id) => els[id] || null,
    querySelector: (sel) => (sel === "main" ? els.main : null),
    createElement: (tag) => element(tag),
  });
  const schedule = (fn, ms, every) => { const id = nextId++; timers.set(id, { at: clock + Math.max(0, ms), fn, every, ms }); return id; };
  const sandbox = {
    document, console, JSON, Math, Number, String, Promise, Object, Array, FormData: class { get() { return "4"; } },
    performance: { now: () => clock },
    setTimeout: (fn, ms = 0) => schedule(fn, ms, false),
    setInterval: (fn, ms) => schedule(fn, ms, true),
    clearTimeout: (id) => timers.delete(id),
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v),
                    removeItem: (k) => store.delete(k) },
    location: { href: "" },
    confirm: () => true,
    fetch: async (url, opts) => {
      fetches.push({ url, body: JSON.parse(opts.body), at: clock });
      const step = fetchPlan.length ? fetchPlan.shift() : { status: 200, json: { next: "/next" } };
      if (step === "network-error") throw new TypeError("Failed to fetch");
      return { status: step.status, ok: step.status < 300, json: async () => step.json || {} };
    },
    SESSION: session, TRIAL: trial, TaskViews: {},
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  return {
    sandbox, els, fetches, store,
    run: (code) => vm.runInContext(code, sandbox),
    timeoutsOf: (ms) => [...timers.values()].filter((t) => !t.every && t.ms === ms).length,
    async advance(ms) {
      const end = clock + ms;
      for (;;) {
        await flush();
        const due = [...timers.entries()].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        const [id, t] = due;
        clock = t.at;
        if (t.every) t.at += t.ms; else timers.delete(id);
        t.fn();
      }
      clock = end;
      await flush();
    },
  };
}

const SESSION = { index: 7, remainingMs: null, sid: "abc", msgTimeUp: "Time is up", msgQuitConfirm: "?",
                  msgWithdrawConfirm: "?", msgSaving: "Saving" };

// F11: one controlled start; pointer then keyboard never restarts the task timeout.
{
  const b = browser({ session: SESSION, trial: { index: 7, timeout: 5000, task: "demo", tryMode: false } });
  b.run(src("session.js"));
  b.run(src("common.js"));
  b.run(`TaskViews.demo = function (ctx) { window.ctx = ctx; };
         window.captured = null; Study.askEffort = (result) => { window.captured = result; };`);
  b.run(src("plugin_shell.js"));
  assert.equal(b.timeoutsOf(5000), 0, "no task timeout while instructions are read");
  await b.advance(1000);
  b.els["task-root"].dispatch("pointerdown");          // Start
  assert.equal(b.timeoutsOf(5000), 1);
  await b.advance(2000);
  b.sandbox.document.dispatch("keydown", { key: "ArrowLeft" });  // first response, other input kind
  b.els["task-root"].dispatch("pointerdown");
  assert.equal(b.timeoutsOf(5000), 1, "a second input kind must not add or restart the timeout");
  await b.advance(3000);                                // t = 6000: 5000 ms after Start
  const r = b.sandbox.captured;
  assert.ok(r && r.timed_out === true, "timed out exactly 5 s after Start");
  assert.deepEqual({ ...r.timing }, { instr_ms: 1000, start_ms: 1000, first_response_ms: 3000, complete_ms: 6000 });
  assert.equal(r.rt_ms, 5000);
  console.log("ok single_start_transition");
}

// F01: at the deadline the page freezes and the stop carries the partial trial.
{
  const b = browser({ session: { ...SESSION, remainingMs: 2000 }, trial: { index: 7 },
                      fetchPlan: [{ status: 200, json: { next: "/final" } }] });
  b.run(src("session.js"));
  b.run(`Session.setPartial(() => ({ response: [1, 2], rt_ms: 1500 }));`);
  await b.advance(1999);
  assert.equal(b.fetches.length, 0);
  assert.ok(!b.els.main.classList.contains("time-up"));
  await b.advance(1);
  assert.ok(b.els.main.classList.contains("time-up"), "presentation hidden at the deadline");
  assert.equal(b.fetches.length, 1);
  assert.equal(b.fetches[0].url, "/api/stop");
  assert.deepEqual(b.fetches[0].body, { trial_index: 7, reason: "time_cap", partial: { response: [1, 2], rt_ms: 1500 } });
  assert.equal(b.sandbox.location.href, "/final");
  await b.advance(5000);
  assert.equal(b.fetches.length, 1, "stops once");
  console.log("ok deadline_freezes_and_sends_partial");
}

// F05: the two stop buttons send different reasons; a second press does nothing.
{
  const b = browser({ session: SESSION, trial: { index: 7 } });
  b.run(src("session.js"));
  b.els.withdraw.dispatch("click");
  b.els.quit.dispatch("click");
  await b.advance(10);
  assert.equal(b.fetches.length, 1);
  assert.equal(b.fetches[0].body.reason, "withdrawn");
  const c = browser({ session: SESSION, trial: { index: 7 } });
  c.run(src("session.js"));
  c.els.quit.dispatch("click");
  await c.advance(10);
  assert.equal(c.fetches[0].body.reason, "exhausted");
  console.log("ok stop_buttons");
}

// F20: a lost connection is retried with the same body until the server answers.
{
  const b = browser({ session: SESSION, trial: { index: 7 },
                      fetchPlan: ["network-error", { status: 503 }, { status: 200, json: { next: "/trial" } }] });
  b.run(src("session.js"));
  b.run(`Session.submitTrial({ trial_index: 7, effort: 4, rt_ms: 900 });`);
  await b.advance(10000);
  assert.equal(b.fetches.length, 3);
  assert.ok(b.fetches.every((f) => f.url === "/api/trial" && JSON.stringify(f.body) === JSON.stringify(b.fetches[0].body)));
  assert.equal(b.sandbox.location.href, "/trial");
  assert.equal(b.els.status.textContent, "Saving");
  assert.equal(b.store.size, 0, "nothing left pending once stored");
  console.log("ok retry_until_stored");
}

// An answer still pending from before a reload is resent once, for this session only.
{
  const pending = JSON.stringify({ sid: "abc", body: { trial_index: 6, effort: 3 } });
  const b = browser({ session: SESSION, trial: { index: 7 } });
  b.store.set("study.pendingTrial", pending);
  b.run(src("session.js"));
  await b.advance(10);
  assert.equal(b.fetches.length, 1);
  assert.deepEqual(b.fetches[0].body, { trial_index: 6, effort: 3 });
  const other = browser({ session: { ...SESSION, sid: "zzz" }, trial: { index: 0 } });
  other.store.set("study.pendingTrial", pending);
  other.run(src("session.js"));
  await other.advance(10);
  assert.equal(other.fetches.length, 0, "never sent into another session");
  console.log("ok pending_resent_once");
}
