(() => {
  "use strict";
  const MARKER = "data-biosafe-rendered";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")
      .replaceAll('"',"&quot;").replaceAll("'","&#039;");
  }

  function isBioSafeResponse(obj) {
    return obj && typeof obj === "object" && !Array.isArray(obj)
      && typeof obj.conclusion === "string"
      && Array.isArray(obj.evidence)
      && Array.isArray(obj.missing_information)
      && Array.isArray(obj.recommended_next_step);
  }

  function listHtml(items, ordered=false) {
    if (!Array.isArray(items) || items.length === 0) return '<p class="biosafe-empty">None identified.</p>';
    const tag = ordered ? "ol" : "ul";
    return `<${tag}>${items.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</${tag}>`;
  }

  function authoritiesHtml(items) {
    if (!Array.isArray(items) || items.length === 0) return '<p class="biosafe-empty">No authority identified.</p>';
    return `<div class="biosafe-authorities">${items.map(x => `<span class="biosafe-chip">${escapeHtml(x)}</span>`).join("")}</div>`;
  }

  function evidenceHtml(items) {
    if (!Array.isArray(items) || items.length === 0) return '<p class="biosafe-empty">No evidence returned.</p>';
    return `<div class="biosafe-evidence">${items.map(e => `
      <div class="biosafe-evidence-item">
        <span class="biosafe-evidence-id">${escapeHtml(e?.evidence_id || "Evidence")}</span>
        <p>${escapeHtml(e?.statement || "")}</p>
      </div>`).join("")}</div>`;
  }

  function statusClass(safety) {
    const c = String(safety?.classification || "normal").toLowerCase();
    if (c === "refusal") return "biosafe-refusal";
    if (c === "caution") return "biosafe-caution";
    return "biosafe-answer";
  }

  function statusLabel(safety) {
    const mode = String(safety?.response_mode || "answer");
    if (mode === "ask_before_concluding") return "More information needed";
    if (mode === "refuse_and_redirect") return "Restricted request";
    return "Advisory answer";
  }

  function render(obj) {
    const raw = JSON.stringify(obj, null, 2);
    const safety = obj.safety || {};
    const meta = obj._meta || {};
    const validation = meta.output_validation?.decision || "";
    const boundary = meta.boundary_validation?.decision || "";

    const wrapper = document.createElement("section");
    wrapper.className = "biosafe-response";
    wrapper.setAttribute("aria-label","BioSafe response");
    wrapper.setAttribute(MARKER,"true");

    wrapper.innerHTML = `
      <section class="biosafe-card biosafe-conclusion">
        <div class="biosafe-kicker">
          <span class="biosafe-badge" data-state="${escapeHtml(safety.classification || "normal")}">${escapeHtml(statusLabel(safety))}</span>
          ${validation ? `<span class="biosafe-badge">Validation: ${escapeHtml(validation)}</span>` : ""}
          ${boundary ? `<span class="biosafe-badge">Boundary: ${escapeHtml(boundary)}</span>` : ""}
        </div>
        <h2>Conclusion</h2>
        <p>${escapeHtml(obj.conclusion)}</p>
      </section>

      <section class="biosafe-card"><h2>Applicable authority</h2>${authoritiesHtml(obj.applicable_authority)}</section>
      <section class="biosafe-card"><h2>Evidence</h2>${evidenceHtml(obj.evidence)}</section>

      <section class="biosafe-card ${safety.response_mode === "ask_before_concluding" ? "biosafe-caution" : ""}">
        <h2>Information needed</h2>${listHtml(obj.missing_information)}
      </section>

      <section class="biosafe-card"><h2>Recommended next steps</h2>${listHtml(obj.recommended_next_step,true)}</section>
      <section class="biosafe-card"><h2>Limitations</h2>${listHtml(obj.limitations)}</section>

      <section class="biosafe-card ${statusClass(safety)}">
        <h2>Safety & response status</h2>
        <p><strong>${escapeHtml(statusLabel(safety))}</strong></p>
        ${safety.reason ? `<p class="biosafe-muted" style="margin-top:6px">${escapeHtml(safety.reason)}</p>` : ""}
      </section>

      <details class="biosafe-debug">
        <summary>Developer details</summary>
        <button type="button" class="biosafe-copy-button">Copy raw JSON</button>
        <pre>${escapeHtml(raw)}</pre>
      </details>
    `;

    const copyBtn = wrapper.querySelector(".biosafe-copy-button");
    copyBtn?.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(raw);
        copyBtn.textContent = "Copied";
        setTimeout(() => copyBtn.textContent = "Copy raw JSON", 1400);
      } catch (_) {
        copyBtn.textContent = "Copy unavailable";
      }
    });
    return wrapper;
  }

  function tryParseElement(el) {
    if (!el || el.closest(`[${MARKER}]`)) return;
    const txt = (el.textContent || "").trim();
    if (!txt.startsWith("{") || !txt.endsWith("}")) return;
    let obj;
    try { obj = JSON.parse(txt); } catch (_) { return; }
    if (!isBioSafeResponse(obj)) return;
    el.replaceWith(render(obj));
  }

  function scan(root=document) {
    root.querySelectorAll?.("pre, code").forEach(tryParseElement);
  }

  scan();

  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach(node => {
        if (!(node instanceof Element)) return;
        if (node.matches?.("pre, code")) tryParseElement(node);
        scan(node);
      });
    }
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});

  window.BioSafeResponseRenderer = { render, scan, isBioSafeResponse };
})();
