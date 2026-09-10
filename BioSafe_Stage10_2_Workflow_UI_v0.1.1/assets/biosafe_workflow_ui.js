(() => {
  "use strict";

  const PANEL_CONFIG = [
    { id:"ask", label:"Ask BioSafe",
      intro:"Ask a biosafety, biosecurity, transport, waste, or Malaysian regulatory question. BioSafe will identify relevant authority, evidence, uncertainty, and next steps." },
    { id:"review", label:"Review a Document",
      intro:"Review a document for biosafety and regulatory gaps. Uploaded documents are treated as scenario evidence, not regulatory authority." },
    { id:"forme", label:"Form E Assistant",
      intro:"Map supported project information to Form E, identify missing information, and flag inconsistencies without simulating IBC approval." }
  ];

  function getPanels() {
    return PANEL_CONFIG.map(cfg => ({...cfg, el:document.getElementById(cfg.id)})).filter(x => x.el);
  }

  function setActive(shell, panelId) {
    shell.querySelectorAll(".biosafe-workflow-tab").forEach(btn => {
      const active = btn.dataset.target === panelId;
      btn.setAttribute("aria-selected", active ? "true" : "false");
      btn.tabIndex = active ? 0 : -1;
    });
    shell.querySelectorAll(".panel").forEach(panel => {
      const active = panel.id === panelId;
      panel.classList.toggle("active", active);
      panel.hidden = !active;
      panel.setAttribute("aria-hidden", active ? "false" : "true");
    });
    document.getElementById(panelId)?.querySelector("textarea,input,button")?.focus();
  }

  function addIntro(panel, text) {
    if (panel.querySelector(".biosafe-workflow-intro")) return;
    const p = document.createElement("p");
    p.className = "biosafe-workflow-intro";
    p.textContent = text;
    const heading = panel.querySelector("h1,h2,h3");
    heading ? heading.insertAdjacentElement("afterend",p) : panel.insertBefore(p,panel.firstChild);
  }

  function enhanceReview() {
    const input = document.getElementById("reviewFile");
    if (!input || input.nextElementSibling?.classList?.contains("biosafe-file-summary")) return;
    const summary = document.createElement("div");
    summary.className = "biosafe-file-summary";
    summary.textContent = "No file selected.";
    input.insertAdjacentElement("afterend",summary);
    input.addEventListener("change",() => {
      const file = input.files?.[0];
      summary.textContent = file ? `${file.name} · ${Math.max(1,Math.round(file.size/1024))} KB` : "No file selected.";
    });
  }

  function enhanceFormE() {
    const panel = document.getElementById("forme");
    if (!panel || panel.querySelector(".biosafe-forme-helper")) return;
    const helper = document.createElement("div");
    helper.className = "biosafe-forme-helper";
    helper.textContent = "BioSafe can help map supported information and identify gaps, but it does not make an IBC determination or certify Form E completeness.";
    const textarea = document.getElementById("formEQuery");
    textarea ? textarea.insertAdjacentElement("beforebegin",helper) : panel.insertBefore(helper,panel.firstChild);
  }

  function enhanceTextareas() {
    ["askQuery","reviewQuery","formEQuery"].forEach(id => {
      const t = document.getElementById(id);
      if (t && !t.getAttribute("rows")) t.setAttribute("rows","7");
    });
  }

  function mirrorStatus() {
    const source = document.getElementById("status");
    if (!source) return;
    let mirror = document.querySelector(".biosafe-ui-status");
    if (!mirror) {
      mirror = document.createElement("span");
      mirror.className = "biosafe-ui-status";
      source.insertAdjacentElement("afterend",mirror);
    }
    const update = () => {
      const low = (source.textContent || "").trim().toLowerCase();
      if (/loading|working|reviewing|processing|thinking/.test(low)) {
        mirror.dataset.state = "loading";
        mirror.innerHTML = '<span class="biosafe-spinner" aria-hidden="true"></span>Processing locally…';
      } else {
        mirror.dataset.state = "";
        mirror.textContent = "";
      }
    };
    update();
    new MutationObserver(update).observe(source,{childList:true,subtree:true,characterData:true});
  }

  function init() {
    if (document.querySelector(".biosafe-workflow-shell")) return;

    const panels = getPanels();
    if (panels.length !== 3) {
      console.warn("BioSafe Stage 10.2: expected #ask, #review and #forme panels.");
      return;
    }

    const first = panels[0].el;
    const parent = first.parentElement;
    if (!parent) return;

    const shell = document.createElement("div");
    shell.className = "biosafe-workflow-shell";

    const tabs = document.createElement("div");
    tabs.className = "biosafe-workflow-tabs";
    tabs.setAttribute("role","tablist");
    tabs.setAttribute("aria-label","BioSafe workflows");
    shell.appendChild(tabs);

    parent.insertBefore(shell,first);

    panels.forEach((item,idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "biosafe-workflow-tab";
      btn.dataset.target = item.id;
      btn.id = `biosafe-tab-${item.id}`;
      btn.textContent = item.label;
      btn.setAttribute("role","tab");
      btn.setAttribute("aria-controls",item.id);
      btn.setAttribute("aria-selected",idx === 0 ? "true" : "false");
      btn.tabIndex = idx === 0 ? 0 : -1;
      tabs.appendChild(btn);

      item.el.setAttribute("role","tabpanel");
      item.el.setAttribute("aria-labelledby",btn.id);
      item.el.hidden = idx !== 0;
      item.el.setAttribute("aria-hidden",idx === 0 ? "false" : "true");
      item.el.classList.toggle("active",idx === 0);

      shell.appendChild(item.el);
      addIntro(item.el,item.intro);

      btn.addEventListener("click",() => setActive(shell,item.id));
      btn.addEventListener("keydown",ev => {
        if (!["ArrowLeft","ArrowRight"].includes(ev.key)) return;
        ev.preventDefault();
        const buttons = [...tabs.querySelectorAll(".biosafe-workflow-tab")];
        const current = buttons.indexOf(btn);
        const next = ev.key === "ArrowRight"
          ? (current + 1) % buttons.length
          : (current - 1 + buttons.length) % buttons.length;
        buttons[next].click();
      });
    });

    enhanceReview();
    enhanceFormE();
    enhanceTextareas();
    mirrorStatus();

    window.BioSafeWorkflowUI = { setActive:id => setActive(shell,id) };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
