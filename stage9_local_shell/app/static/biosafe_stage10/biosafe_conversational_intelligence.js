(()=>{"use strict";

const STORAGE_KEY="biosafeConversationState_v01";

function loadState(){
  try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||"{}")}catch(_){return{}}
}
function saveState(s){
  try{localStorage.setItem(STORAGE_KEY,JSON.stringify(s))}catch(_){}
}
function resetState(){
  try{localStorage.removeItem(STORAGE_KEY)}catch(_){}
}

function normalize(s){return (s||"").trim().replace(/\s+/g," ")}
function lower(s){return normalize(s).toLowerCase()}

const intents = {
  greeting:/^(hi|hello|hey|good morning|good afternoon|good evening)[!. ]*$/i,
  identity:/^(who are you|what are you|tell me about yourself)[?.! ]*$/i,
  capability:/^(what can you do(?: for me)?|how can you help(?: me)?|help me|what do you do)[?.! ]*$/i
};

function classifyConversationalIntent(text){
  const x=normalize(text);
  if(intents.greeting.test(x)) return "greeting";
  if(intents.identity.test(x)) return "identity";
  if(intents.capability.test(x)) return "capability";
  return null;
}

function conversationalAnswer(intent){
  if(intent==="greeting"){
    return {
      title:"BioSafe",
      text:"Hello. I’m BioSafe, a local biosafety and biosecurity decision-support assistant. You can ask a biosafety question, review a document, or use the Form E Assistant."
    };
  }
  if(intent==="identity"){
    return {
      title:"BioSafe",
      text:"I’m BioSafe, a biosafety and biosecurity decision-support assistant for researchers. I can help you reason through biosafety requirements, identify missing information, review documents, and explain the evidence behind a recommendation. I do not grant regulatory approval or certify compliance."
    };
  }
  return {
    title:"How BioSafe can help",
    text:"I can help you understand biosafety and biosecurity requirements, work through laboratory risk questions, review SOPs and research proposals, identify missing information or inconsistencies, interpret relevant Malaysian and international guidance, and assist with researcher-facing Form E information. You can ask a question directly, upload a document for review, or use the Form E Assistant. I provide evidence-based decision support, but I do not grant approval or certify compliance."
  };
}

function isShortFollowUp(text){
  const x=normalize(text);
  if(!x) return false;
  const n=x.split(/\s+/).length;
  return n<=10 && x.length<=100;
}

function buildContextualQuery(current){
  const state=loadState();
  if(!state || !state.pending || !state.pending.length || !isShortFollowUp(current)) return current;

  const pending=state.pending.slice(0,3).join("; ");
  const prior=state.lastUser||"";
  const conclusion=state.lastConclusion||"";
  return [
    "Conversation context:",
    prior ? `Previous user question: ${prior}` : "",
    conclusion ? `Previous BioSafe conclusion: ${conclusion}` : "",
    `BioSafe asked for clarification about: ${pending}`,
    `Current user follow-up: ${normalize(current)}`,
    "Interpret the current follow-up as a response to the prior clarification where appropriate. Do not treat organism identity alone as evidence of LMO/GMM status."
  ].filter(Boolean).join("\n");
}

function updateContextFromResponse(obj,visibleUserText){
  if(!obj || typeof obj!=="object") return;
  const state=loadState();
  state.lastUser=normalize(visibleUserText||state.lastUser||"");
  state.lastConclusion=normalize(obj.conclusion||"");
  state.pending=Array.isArray(obj.missing_information) ? obj.missing_information.slice(0,5) : [];
  state.lastSafetyMode=obj?.safety?.response_mode||"";
  saveState(state);
}

function hasModificationEvidence(obj){
  const hay=[
    obj?.conclusion,
    ...(obj?.evidence||[]).map(x=>x?.statement||""),
    ...(obj?.missing_information||[]),
    ...(obj?.recommended_next_step||[])
  ].join(" ").toLowerCase();
  return /\b(genetic(?:ally)? modified|recombinant|modern biotechnology|novel combination of genetic material|lmo status confirmed|living modified organism status confirmed)\b/.test(hay);
}

function applyLmoSafeguard(obj){
  if(!obj || typeof obj!=="object") return obj;
  const conclusion=String(obj.conclusion||"");
  const speciesToLmo=/\b([A-Z][a-z]+(?:\s+[a-z][a-z-]+)+)\s+(?:is|are)\s+(?:an?\s+)?(?:class\s*[ivx0-9.-]+\s+)?(?:lmo|living modified organism|gmm|genetically modified microorganism)\b/i;
  const genericSpeciesLmo=/\b(?:is|are)\s+(?:an?\s+)?(?:class\s*[ivx0-9.-]+\s+)?(?:lmo|living modified organism|gmm)\b/i;

  if(genericSpeciesLmo.test(conclusion) && !hasModificationEvidence(obj)){
    const copy=JSON.parse(JSON.stringify(obj));
    copy.conclusion="The organism identity alone does not establish that the material is a living modified organism (LMO) or genetically modified microorganism. LMO/GMM status depends on whether a novel combination of genetic material was obtained through modern biotechnology. Please confirm whether the material is genetically modified, recombinant, or otherwise produced using relevant modern-biotechnology techniques before applying an LMO-specific regulatory pathway.";
    copy.missing_information=Array.from(new Set([
      ...(copy.missing_information||[]),
      "Whether the organism or material is genetically modified, recombinant, or otherwise involves a novel combination of genetic material obtained through modern biotechnology"
    ]));
    copy.recommended_next_step=Array.from(new Set([
      ...(copy.recommended_next_step||[]),
      "Confirm the genetic-modification / recombinant / modern-biotechnology status before applying LMO-specific notification or contained-use requirements."
    ]));
    copy.limitations=Array.from(new Set([
      ...(copy.limitations||[]),
      "Species identity by itself is not evidence of LMO/GMM status."
    ]));
    copy.safety=copy.safety||{};
    copy.safety.classification="caution";
    copy.safety.response_mode="ask_before_concluding";
    copy.safety.reason="LMO/GMM status requires modification-related trigger facts that are not established by species identity alone.";
    copy._product_guard=copy._product_guard||{};
    copy._product_guard.DQ_LMO_001="applied";
    return copy;
  }
  return obj;
}

function educationalSections(obj){
  const sections=[];
  const evidence=(obj?.evidence||[]).filter(x=>x&&x.statement).slice(0,3);
  if(evidence.length){
    sections.push({
      title:"Why this matters",
      items:evidence.map(x=>x.statement)
    });
  }
  const missing=(obj?.missing_information||[]).filter(Boolean);
  if(missing.length){
    sections.push({
      title:"What I need from you",
      items:missing.slice(0,4)
    });
  }
  const next=(obj?.recommended_next_step||[]).filter(Boolean);
  if(next.length){
    sections.push({
      title:"What to do next",
      items:next.slice(0,4)
    });
  }
  return sections;
}

function addEducationalContent(container,obj){
  const sections=educationalSections(obj);
  for(const sec of sections){
    const wrap=document.createElement("section");
    wrap.className="biosafe-education-section";
    const h=document.createElement("h4"); h.textContent=sec.title; wrap.append(h);
    const ul=document.createElement("ul");
    sec.items.forEach(t=>{const li=document.createElement("li");li.textContent=t;ul.append(li)});
    wrap.append(ul); container.append(wrap);
  }
}

function install(){
  const shell=window.BioSafeConversationalShell;
  if(!shell) return setTimeout(install,50);

  const originalSubmit=shell.submitActive;
  const stream=()=>document.querySelector(".biosafe-chat-stream");
  const editor=()=>document.querySelector(".biosafe-chat-editor");

  // Rebind Send and Enter to our wrapper after the base shell has built.
  function renderLocal(answer,userText){
    document.querySelector(".biosafe-chat-welcome")?.remove();

    const userTurn=document.createElement("div");
    userTurn.className="biosafe-chat-turn"; userTurn.dataset.role="user";
    userTurn.innerHTML='<div class="biosafe-avatar">You</div><div class="biosafe-turn-body"><div class="biosafe-user-bubble"></div></div>';
    userTurn.querySelector(".biosafe-user-bubble").textContent=userText;
    stream()?.append(userTurn);

    const turn=document.createElement("div");
    turn.className="biosafe-chat-turn"; turn.dataset.role="assistant";
    const av=document.createElement("div"); av.className="biosafe-avatar"; av.textContent="BS";
    const body=document.createElement("div"); body.className="biosafe-turn-body";
    const card=document.createElement("div"); card.className="biosafe-primary-answer";
    const k=document.createElement("div"); k.className="biosafe-answer-kicker"; k.textContent=answer.title;
    const t=document.createElement("div"); t.className="biosafe-answer-text"; t.textContent=answer.text;
    card.append(k,t); body.append(card); turn.append(av,body); stream()?.append(turn);
    turn.scrollIntoView({behavior:"smooth",block:"end"});
  }

  function submit(){
    const ed=editor();
    const text=ed?.value||"";
    const intent=classifyConversationalIntent(text);
    if(intent){
      renderLocal(conversationalAnswer(intent),normalize(text));
      if(ed) ed.value="";
      const state=loadState(); state.lastUser=normalize(text); state.pending=[]; saveState(state);
      return;
    }

    const hidden=document.getElementById("askQuery");
    const activeAsk=document.querySelector('.biosafe-side-nav button[data-mode="ask"][aria-current="page"]');
    if(activeAsk && hidden){
      const visible=normalize(text);
      const contextual=buildContextualQuery(visible);
      hidden.value=contextual;
      const state=loadState(); state.visiblePendingUser=visible; saveState(state);
    }
    originalSubmit();
  }

  const send=document.querySelector(".biosafe-chat-composer .primary");
  if(send){send.onclick=submit}
  const ed=editor();
  if(ed){
    const clone=ed.cloneNode(true);
    ed.replaceWith(clone);
    clone.addEventListener("keydown",e=>{
      if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();submit()}
    });
  }

  // Patch response rendering by observing assistant turns and enhancing the next completed structured object.
  const out=document.getElementById("output");
  if(out){
    new MutationObserver(()=>{
      let obj=null;
      try{obj=JSON.parse((out.textContent||"").trim())}catch(_){}
      if(!obj) return;
      const state=loadState();
      const guarded=applyLmoSafeguard(obj);
      updateContextFromResponse(guarded,state.visiblePendingUser||state.lastUser||"");

      // If safeguard changed the response, replace newest assistant card text.
      if(guarded?._product_guard?.DQ_LMO_001==="applied"){
        setTimeout(()=>{
          const turns=[...document.querySelectorAll('.biosafe-chat-turn[data-role="assistant"]')];
          const last=turns.at(-1);
          const textEl=last?.querySelector(".biosafe-answer-text");
          if(textEl) textEl.textContent=guarded.conclusion;
          const body=last?.querySelector(".biosafe-turn-body");
          if(body && !body.querySelector(".biosafe-education-section")) addEducationalContent(body,guarded);
        },0);
      }else{
        setTimeout(()=>{
          const turns=[...document.querySelectorAll('.biosafe-chat-turn[data-role="assistant"]')];
          const last=turns.at(-1);
          const body=last?.querySelector(".biosafe-turn-body");
          if(body && !body.querySelector(".biosafe-education-section")) addEducationalContent(body,guarded);
        },0);
      }
    }).observe(out,{childList:true,subtree:true,characterData:true});
  }

  // New conversation also clears local conversational state.
  const newBtn=document.querySelector(".biosafe-new-chat");
  if(newBtn){
    const prior=newBtn.onclick;
    newBtn.onclick=()=>{resetState(); if(prior) prior()}
  }

  window.BioSafeConversationalIntelligence={
    classifyConversationalIntent,
    conversationalAnswer,
    buildContextualQuery,
    applyLmoSafeguard,
    educationalSections,
    resetState
  };
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install,{once:true}); else install();
})();
