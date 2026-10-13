// Date order follows the language: year-month-day for Japanese, Chinese and Korean.
function fmtDateLocal(d, monthName, y, lang) {
  if (lang === "ja" || lang === "zh") return y + "年" + monthName + d + "日";
  if (lang === "ko") return y + "년 " + monthName + " " + d + "일";
  if (lang === "de") return d + ". " + monthName + " " + y;
  return d + " " + monthName + " " + y;
}
// Form completion: after Start, shows the fictional record, the 3 rules and the empty form
// (autocomplete off; suspected autofill and paste events are counted). Help toggles a format
// note (each opening counted). Submit sends the raw field values; scoring happens on the server.
// Response: {fields: {...}, time_ms, help_views, autofill_events, paste_events}.
TaskViews["form_completion"] = function (ctx) {
  const $ = (s) => ctx.root.querySelector(s);
  const it = ctx.item, tx = ctx.text, rec = it.record;
  let ended = false, t0 = 0, timer = 0, helpViews = 0, autofill = 0, pastes = 0;

  const rows = [
    ["family", rec.family], ["given", rec.given], ["member", rec.member],
    ["birth", fmtDateLocal(rec.birth[0], tx.months[rec.birth[1] - 1], rec.birth[2], document.documentElement.lang)],
    ["postcode", rec.postcode], ["phone", rec.phone || tx.no_phone],
    ["plan", tx.plans[rec.plan]], ["contact", tx.contacts[rec.contact]], ["amount", String(rec.amount)],
  ];
  const dl = $("#fc-record");
  rows.forEach(([k, v]) => {
    const dt = document.createElement("dt"); dt.textContent = tx.labels[k];
    const dd = document.createElement("dd"); dd.textContent = v;
    dl.appendChild(dt); dl.appendChild(dd);
  });
  const ol = $("#fc-rules");
  it.rules.forEach((r) => {
    const li = document.createElement("li");
    li.textContent = tx.rules[r].replace("{year}", it.junior_year);
    ol.appendChild(li);
  });

  const inputs = [...ctx.root.querySelectorAll("input[type=text][data-f]")];
  inputs.forEach((el) => {
    el.addEventListener("input", (e) => {
      // Typing and deleting have an inputType; browser autofill usually has none or a replacement type.
      if (!e.inputType || e.inputType === "insertReplacementText") autofill += 1;
    });
    el.addEventListener("paste", () => { pastes += 1; });
  });

  $("#fc-help").addEventListener("click", () => {
    const h = $("#fc-help-text");
    h.hidden = !h.hidden;
    if (!h.hidden) helpViews += 1;
  });

  function collect() {
    const fields = {};
    inputs.forEach((el) => { fields[el.dataset.f] = el.value; });
    const sel = $("select[data-f=plan]").value;
    fields.plan = sel === "" ? null : parseInt(sel, 10);
    const c = ctx.root.querySelector("input[name=fc-contact]:checked");
    fields.contact = c ? parseInt(c.value, 10) : null;
    return { fields, time_ms: Math.round(performance.now() - t0), help_views: helpViews,
             autofill_events: autofill, paste_events: pastes };
  }

  $("#fc-submit").addEventListener("click", () => end(false));

  $("#fc-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    $("#fc-work").hidden = false;
    t0 = performance.now();
    timer = setTimeout(() => end(true), it.limit_ms);
    inputs[0].focus();
  }, { once: true });

  function end(timedOut) {
    if (ended) return;
    ended = true;
    clearTimeout(timer);
    const r = collect();
    ctx.root.querySelectorAll("input, select, button").forEach((el) => { el.disabled = true; });
    ctx.finish(r, timedOut);
  }
};
