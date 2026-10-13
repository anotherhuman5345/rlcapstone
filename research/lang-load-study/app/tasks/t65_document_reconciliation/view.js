// Date order follows the language: year-month-day for Japanese, Chinese and Korean.
function fmtDateLocal(d, monthName, y, lang) {
  if (lang === "ja" || lang === "zh") return y + "年" + monthName + d + "日";
  if (lang === "ko") return y + "년 " + monthName + " " + d + "일";
  if (lang === "de") return d + ". " + monthName + " " + y;
  return d + " " + monthName + " " + y;
}
// Document reconciliation: after Start, two tables appear. Cells of the delivery note
// (table B) are toggle buttons: click / tap, or Tab to them and press Enter or Space.
// Done ends the trial. Response: {marks: [[row, field], ...], rt, toggles}; finish() once.
TaskViews["document_reconciliation"] = function (ctx) {
  const T = ctx.text, it = ctx.item, FIELDS = it.fields || ["product", "qty", "date"];
  const $ = (s) => ctx.root.querySelector(s);
  const docs = $("#dr-docs"), done = $("#dr-done");
  const show = {
    product: (v) => (T.products || [])[v] || "?",
    qty: (v) => String(v),
    date: (v) => fmtDateLocal(v[2], (T.months || [])[v[1] - 1] || "?", v[0], document.documentElement.lang),
  };
  const marked = new Set();
  let toggles = 0, t0 = 0, finished = false;

  function fill(tbody, rows, clickable) {
    rows.forEach((r, i) => {
      const tr = document.createElement("tr");
      const code = document.createElement("td");
      const cs = document.createElement("span"); cs.className = "dr-cell"; cs.textContent = r.code;
      code.appendChild(cs); tr.appendChild(code);
      for (const f of FIELDS) {
        const td = document.createElement("td");
        if (clickable) {
          const b = document.createElement("button");
          b.type = "button"; b.className = "dr-cell"; b.textContent = show[f](r[f]);
          b.dataset.row = i; b.dataset.field = f; b.setAttribute("aria-pressed", "false");
          td.appendChild(b);
        } else {
          const sp = document.createElement("span");  // same box as the buttons, so rows line up
          sp.className = "dr-cell"; sp.textContent = show[f](r[f]);
          td.appendChild(sp);
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    });
  }
  fill($("#dr-a"), it.order || [], false);
  fill($("#dr-b"), it.delivery || [], true);

  $("#dr-b").addEventListener("click", (e) => {
    const b = e.target.closest("button.dr-cell");
    if (!b || finished || !t0) return;
    const k = b.dataset.row + "|" + b.dataset.field;
    if (marked.has(k)) marked.delete(k); else marked.add(k);
    b.setAttribute("aria-pressed", marked.has(k) ? "true" : "false");
    toggles += 1;
    ctx.status(T.marked_count.replace("{n}", marked.size));
  });

  $("#dr-start").addEventListener("click", (e) => {
    e.currentTarget.hidden = true;
    docs.classList.remove("dr-hidden");
    done.hidden = false;
    t0 = performance.now();
    ctx.status(T.marked_count.replace("{n}", 0));
  }, { once: true });

  done.addEventListener("click", () => {
    if (finished) return;
    finished = true;
    done.disabled = true;
    const marks = [...marked].map((k) => { const [r, f] = k.split("|"); return [Number(r), f]; });
    ctx.status("");
    ctx.finish({ marks, rt: Math.round(performance.now() - t0), toggles }, false);
  });
};
