(() => {
  "use strict";

  const SELECTORS = {
    askForm: 'form[action*="/api/ask"], #ask-form, [data-biosafe-workflow="ask"] form',
    reviewForm: 'form[action*="/api/review"], #review-form, [data-biosafe-workflow="review"] form',
    formEForm: 'form[action*="/api/form-e"], #form-e-form, [data-biosafe-workflow="form-e"] form',
  };

  const WORKFLOWS = [
    { key: "ask", label: "Ask BioSafe", selector: SELECTORS.askForm,
      intro: "Ask a biosafety or biosecurity question. BioSafe will identify the relevant authority, evidence, uncertainties, and next steps." },
    { key: "review", label: "Review a Document", selector: SELECTORS.reviewForm,
      intro: "Upload or paste a document for structured review. User documents are treated as scenario evidence, not regulatory authority." },
    { key: "form-e", label: "Form E Assistant", selector: SELECTORS.formEForm,
      intro: "Use BioSafe to identify supported Form E information, missing fields, and consistency issues. BioSafe does not simulate IBC approval." }
  ];

  function findForms() {
    return WORKFLOWS
      .map(w => ({...w, form: document.querySelector(w.selector)}))
      .filter(x => x.form);
  }

  function ensureStatus(form) {
    let status = form.querySelector(".biosafe-workflow-status");
    if (!status) {
      status = document.createElement("div");
      status.className = "biosafe-workflow-status";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      const submit = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submit?.parentElement) {
        const row = document.createElement("div");
        row.className = "biosafe-submit-row";
        submit.parentElement.insertBefore(row, submit);
        row.appendChild(submit);
        row.appendChild(status);
      } else {
        form.appendChild(status);
      }
    }
    return status;
  }

  function ensureStateCard(form) {
    let card = form.querySelector(".biosafe-state-card");
    if (!card) {
      card = document.createElement("div");
      card.className = "biosafe-state-card";
      card.setAttribute("role", "status");
      card.setAttribute("aria-live", "polite");
      form.appendChild(card);
    }
    return card;
  }

  function setState(form, state, message) {
    const status = ensureStatus(form);
    const card = ensureStateCard(form);

    status.dataset.state = state || "";
    card.dataset.state = state || "";
    card.dataset.visible = message ? "true" : "false";

    if (state === "loading") {
      status.innerHTML = '<span class="biosafe-spinner" aria-hidden="true"></span>BioSafe is reviewing your request…';
    } else {
      status.textContent = "";
    }

    card.textContent = message || "";
  }

  function addIntro(form, text) {
    if (form.previousElementSibling?.classList?.contains("biosafe-workflow-intro")) return;
    const p = document.createElement("p");
    p.className = "biosafe-workflow-intro";
    p.textContent = text;
    form.parentElement?.insertBefore(p, form);
  }

  function enhanceInputs(form, key) {
    form.querySelectorAll("textarea").forEach(t => {
      if (!t.getAttribute("rows")) t.setAttribute("rows", "7");
    });

    form.querySelectorAll('input[type="file"]').forEach(input => {
      if (!input.nextElementSibling?.classList?.contains("biosafe-file-summary")) {
        const summary = document.createElement("div");
        summary.className = "biosafe-file-summary";
        summary.textContent = "No file selected.";
        input.insertAdjacentElement("afterend", summary);
        input.addEventListener("change", () => {
          const file = input.files?.[0];
          summary.textContent = file ? `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB` : "No file selected.";
        });
      }
    });

    if (key === "form-e" && !form.querySelector(".biosafe-forme-helper")) {
      const helper = document.createElement("div");
      helper.className = "biosafe-forme-helper";
      helper.textContent = "BioSafe can help map supported information and identify gaps, but it does not make an IBC determination or certify Form E completeness.";
      form.insertBefore(helper, form.firstChild);
    }
  }

  function wireSubmitState(form) {
    if (form.dataset.biosafeStage102Wired === "true") return;
    form.dataset.biosafeStage102Wired = "true";

    form.addEventListener("submit", () => {
      const btn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (btn) {
        btn.dataset.originalLabel = btn.textContent || btn.value || "";
        if ("disabled" in btn) btn.disabled = true;
      }
      setState(form, "loading", "");
      window.setTimeout(() => {
        if (btn && "disabled" in btn) btn.disabled = false;
      }, 90000);
    });
  }

  function createShell(items) {
    if (document.querySelector(".biosafe-workflow-shell")) return;

    const first = items[0];
    if (!first?.form?.parentElement) return;

    const shell = document.createElement("section");
    shell.className = "biosafe-workflow-shell";
    shell.setAttribute("aria-label", "BioSafe workflows");

    const tabs = document.createElement("div");
    tabs.className = "biosafe-workflow-tabs";
    tabs.setAttribute("role", "tablist");
    shell.appendChild(tabs);

    const commonParent = first.form.parentElement;
    commonParent.insertBefore(shell, first.form);

    items.forEach((item, idx) => {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "biosafe-workflow-tab";
      tab.id = `biosafe-tab-${item.key}`;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", idx === 0 ? "true" : "false");
      tab.setAttribute("aria-controls", `biosafe-panel-${item.key}`);
      tab.textContent = item.label;
      tabs.appendChild(tab);

      const panel = document.createElement("section");
      panel.className = "biosafe-workflow-panel";
      panel.id = `biosafe-panel-${item.key}`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", tab.id);
      panel.dataset.active = idx === 0 ? "true" : "false";

      const originalParent = item.form.parentElement;
      panel.appendChild(item.form);
      shell.appendChild(panel);

      addIntro(item.form, item.intro);
      enhanceInputs(item.form, item.key);
      wireSubmitState(item.form);

      tab.addEventListener("click", () => {
        shell.querySelectorAll(".biosafe-workflow-tab").forEach(t => t.setAttribute("aria-selected", "false"));
        shell.querySelectorAll(".biosafe-workflow-panel").forEach(p => p.dataset.active = "false");
        tab.setAttribute("aria-selected", "true");
        panel.dataset.active = "true";
        const focusable = panel.querySelector("textarea,input,select,button");
        focusable?.focus();
      });

      if (originalParent !== commonParent && originalParent.children.length === 0) {
        originalParent.remove();
      }
    });
  }

  function observeResponses(items) {
    const observer = new MutationObserver(() => {
      items.forEach(item => {
        const form = item.form;
        if (!form) return;
        const rendered = document.querySelector('[data-biosafe-rendered="true"]');
        const raw = document.querySelector("pre");
        if (rendered || raw) {
          const btn = form.querySelector('button[type="submit"], input[type="submit"]');
          if (btn && "disabled" in btn) btn.disabled = false;
          const status = ensureStatus(form);
          status.textContent = "";
        }
      });
    });
    observer.observe(document.body, {childList:true, subtree:true});
  }

  function init() {
    const items = findForms();
    if (!items.length) return;
    createShell(items);
    observeResponses(items);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {once:true});
  } else {
    init();
  }

  window.BioSafeWorkflowUI = { init, setState };
})();
