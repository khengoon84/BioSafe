(()=>{"use strict";
let activeMode="ask";
let lastRawOutput="No request submitted yet.";
const labels={ask:"Ask BioSafe",review:"Review Document",forme:"Form E Assistant"};
const ids={ask:"askQuery",review:"reviewQuery",forme:"formEQuery"};

const E=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const q=m=>document.getElementById(ids[m]);
const panel=m=>document.getElementById(m);
const originalButton=m=>panel(m)?.querySelector("button");

function makeTurn(role){
  const t=E("div","biosafe-chat-turn"); t.dataset.role=role;
  const avatar=E("div","biosafe-avatar",role==="user"?"You":"BS");
  const body=E("div","biosafe-turn-body");
  t.append(avatar,body);
  return [t,body];
}

function addUserTurn(text){
  const s=document.querySelector(".biosafe-chat-stream");
  if(!s||!text.trim())return;
  document.querySelector(".biosafe-chat-welcome")?.remove();
  const [t,b]=makeTurn("user");
  b.append(E("div","biosafe-user-bubble",text.trim()));
  s.append(t);
  t.scrollIntoView({behavior:"smooth",block:"end"});
}

function assistantCard(title,bodyText){
  const wrap=E("div","biosafe-primary-answer");
  wrap.append(E("div","biosafe-answer-kicker",title));
  const body=E("div","biosafe-answer-text",bodyText||"");
  wrap.append(body);
  return wrap;
}

function buildSecondaryDetails(obj){
  const details=E("details","biosafe-secondary-details");
  const summary=E("summary","","More details");
  details.append(summary);

  const sections=[
    ["Applicable authority",obj.applicable_authority],
    ["Evidence",obj.evidence],
    ["Information needed",obj.missing_information],
    ["Recommended next steps",obj.recommended_next_step],
    ["Limitations",obj.limitations]
  ];

  sections.forEach(([title,val])=>{
    if(!val || (Array.isArray(val)&&!val.length)) return;
    const sec=E("section","biosafe-detail-section");
    sec.append(E("h4","",title));

    if(title==="Evidence" && Array.isArray(val)){
      val.forEach(item=>{
        const row=E("div","biosafe-evidence-row");
        if(item?.evidence_id) row.append(E("span","biosafe-evidence-id",item.evidence_id));
        row.append(E("span","",item?.statement||String(item)));
        sec.append(row);
      });
    } else if(Array.isArray(val)){
      const ul=E("ul","");
      val.forEach(item=>{const li=E("li","",typeof item==="string"?item:JSON.stringify(item));ul.append(li)});
      sec.append(ul);
    } else {
      sec.append(E("div","",String(val)));
    }
    details.append(sec);
  });

  if(obj.safety){
    const sec=E("section","biosafe-detail-section");
    sec.append(E("h4","","Safety & response status"));
    const txt=[
      obj.safety.classification?`Classification: ${obj.safety.classification}`:"",
      obj.safety.response_mode?`Mode: ${obj.safety.response_mode}`:"",
      obj.safety.reason||""
    ].filter(Boolean).join(" · ");
    sec.append(E("div","",txt));
    details.append(sec);
  }
  return details;
}

function renderOutputMirror(raw){
  const s=document.querySelector(".biosafe-chat-stream");
  if(!s)return;
  let obj=null;
  try{obj=JSON.parse(raw)}catch(_){}

  const [t,b]=makeTurn("assistant");

  if(obj){
    const conclusion=(obj.conclusion||"").trim();
    const policy=obj?._meta?.policy_mode||"";
    const safetyMode=obj?.safety?.response_mode||"";
    let title="BioSafe";
    if(safetyMode==="ask_before_concluding") title="More information needed";
    else if(safetyMode==="refuse_and_redirect") title="Safety-limited response";
    else if(policy==="ASSESS_NOT_CERTIFY") title="Advisory assessment";

    b.append(assistantCard(title, conclusion || "BioSafe completed the request."));
    const more=buildSecondaryDetails(obj);
    if(more.children.length>1) b.append(more);

    if(obj._meta){
      const dev=E("details","biosafe-developer-details");
      dev.append(E("summary","","Developer details"));
      const pre=E("pre",""); pre.textContent=JSON.stringify(obj._meta,null,2);
      dev.append(pre); b.append(dev);
    }
  } else {
    const pre=E("pre","biosafe-assistant-mirror"); pre.textContent=raw; b.append(pre);
  }

  s.append(t);
  t.scrollIntoView({behavior:"smooth",block:"end"});
}

function incompleteAsk(text){
  const x=text.trim();
  if(!x) return "Please enter a question.";
  const words=x.split(/\s+/);
  const lone=/^(who|what|when|where|why|how|can|could|should|do|does|is|are|will|would)$/i.test(x);
  if(lone || (words.length===1 && x.length<8))
    return "Please complete your question so BioSafe has enough context to answer safely and accurately.";
  return "";
}

function setFeedback(msg,state=""){
  const f=document.querySelector(".biosafe-composer-feedback");
  if(!f)return;
  f.textContent=msg; f.dataset.state=state;
}

function setMode(m){
  if(!labels[m])return;
  activeMode=m;
  document.querySelectorAll(".biosafe-side-nav button")
    .forEach(b=>b.setAttribute("aria-current",b.dataset.mode===m?"page":"false"));
  document.querySelector(".biosafe-mode-label").textContent=labels[m];
  document.querySelector(".biosafe-mode-boundary").textContent=
    m==="forme"?"Form E support only — BioSafe does not make an IBC determination or certify completeness.":"";

  const editor=document.querySelector(".biosafe-chat-editor");
  const src=q(m);
  editor.value=src?.value||"";
  setFeedback("");

  const attach=document.querySelector(".biosafe-attach-slot");
  attach.innerHTML="";
  if(m==="review"){
    const srcFile=document.getElementById("reviewFile");
    if(srcFile){
      const proxy=srcFile.cloneNode(true);
      proxy.id="reviewFileProxy";
      proxy.addEventListener("change",()=>{
        if(proxy.files?.length){
          const dt=new DataTransfer();
          [...proxy.files].forEach(f=>dt.items.add(f));
          srcFile.files=dt.files;
        }
      });
      attach.append(proxy);
    }
  }
  editor.focus();
}

function syncEditor(){
  const editor=document.querySelector(".biosafe-chat-editor");
  const src=q(activeMode);
  if(editor&&src) src.value=editor.value;
}

function clearEditor(){
  const editor=document.querySelector(".biosafe-chat-editor");
  const src=q(activeMode);
  if(editor) editor.value="";
  if(src) src.value="";
}

function submitActive(){
  syncEditor();
  const text=q(activeMode)?.value||"";

  if(activeMode==="ask"){
    const msg=incompleteAsk(text);
    if(msg){
      setFeedback(msg,"warning");
      const [t,b]=makeTurn("assistant");
      b.append(assistantCard("Please complete your question",msg));
      document.querySelector(".biosafe-chat-stream")?.append(t);
      clearEditor();
      return;
    }
  }

  setFeedback("");
  addUserTurn(text);
  const b=originalButton(activeMode);
  clearEditor();
  if(b) b.click();
}

function resetChat(){
  const s=document.querySelector(".biosafe-chat-stream");
  if(s){
    s.innerHTML='<div class="biosafe-chat-welcome"><h1>How can BioSafe help?</h1><p>Ask a biosafety or biosecurity question, review a document, or work through Form E information with evidence-aware guidance.</p></div>';
  }
  clearEditor();
  setFeedback("");
}

function mirrorOutput(){
  const out=document.getElementById("output");
  if(!out)return;
  const raw=(out.textContent||"").trim();
  if(!raw || raw==="No request submitted yet." || raw===lastRawOutput)return;
  lastRawOutput=raw;
  renderOutputMirror(raw);
}

function build(){
  if(document.querySelector(".biosafe-chat-app"))return;

  const ask=panel("ask"),rev=panel("review"),fe=panel("forme");
  const out=document.getElementById("output");
  const status=document.getElementById("status");

  if(!ask||!rev||!fe||!out||!status){
    console.warn("BioSafe conversational shell: Stage 9 DOM not found.");
    return;
  }

  // Keep original Stage 9 controls/handlers alive, but make them completely non-layout.
  const host=E("div","biosafe-stage9-hidden-host");
  host.setAttribute("aria-hidden","true");
  [ask,rev,fe,status.parentElement,out].forEach(node=>{
    if(node && !host.contains(node)) host.append(node);
  });
  document.body.append(host);

  document.body.classList.add("biosafe-chat-mode");

  const app=E("div","biosafe-chat-app");
  const side=E("aside","biosafe-chat-sidebar"); side.dataset.open="false";

  const brand=E("div","biosafe-chat-brand");
  brand.innerHTML="<strong>BioSafe</strong><span>Local biosafety assistant</span>";

  const nb=E("button","biosafe-new-chat","+ New conversation");
  nb.type="button"; nb.onclick=resetChat;

  const lab=E("div","biosafe-side-label","Workflows");
  const nav=E("nav","biosafe-side-nav");
  [["ask","Ask BioSafe"],["review","Review Document"],["forme","Form E Assistant"]]
    .forEach(([m,l])=>{
      const b=E("button","",l);
      b.type="button"; b.dataset.mode=m;
      b.onclick=()=>{setMode(m);side.dataset.open="false"};
      nav.append(b);
    });

  side.append(
    brand,nb,lab,nav,
    E("div","biosafe-local-note",
      "Runs locally. BioSafe provides evidence-based advisory support and does not certify regulatory compliance or approval.")
  );

  const main=E("main","biosafe-chat-main");
  const top=E("header","biosafe-chat-topbar");
  const left=E("div");
  const menu=E("button","biosafe-mobile-menu","☰");
  menu.type="button";
  menu.onclick=()=>side.dataset.open=side.dataset.open!=="true";
  left.append(menu,E("strong","","BioSafe"));
  top.append(left,E("span","biosafe-runtime-pill","Local • Qwen"));

  const scroll=E("div","biosafe-chat-scroll");
  const col=E("div","biosafe-chat-column");
  const stream=E("div","biosafe-chat-stream");
  stream.innerHTML='<div class="biosafe-chat-welcome"><h1>How can BioSafe help?</h1><p>Ask a biosafety or biosecurity question, review a document, or work through Form E information with evidence-aware guidance.</p></div>';
  col.append(stream); scroll.append(col);

  const wrap=E("div","biosafe-chat-composer-wrap");
  const comp=E("div","biosafe-chat-composer");
  const editor=E("textarea","biosafe-chat-editor");
  editor.placeholder="Ask BioSafe...";
  editor.addEventListener("keydown",e=>{
    if(e.key==="Enter"&&!e.shiftKey){
      e.preventDefault();
      submitActive();
    }
  });

  const attach=E("div","biosafe-attach-slot");
  const bound=E("div","biosafe-mode-boundary");
  const feedback=E("div","biosafe-composer-feedback");
  const actions=E("div","biosafe-composer-actions");
  const mode=E("span","biosafe-mode-label","Ask BioSafe");
  const send=E("button","primary","Send");
  send.type="button"; send.onclick=submitActive;

  actions.append(mode,send);
  comp.append(editor,attach,bound,feedback,actions);
  wrap.append(comp);

  main.append(top,scroll,wrap);
  app.append(side,main);
  document.body.insertBefore(app,document.body.firstChild);

  new MutationObserver(mirrorOutput).observe(out,{childList:true,subtree:true,characterData:true});
  setMode("ask");
}

if(document.readyState==="loading")
  document.addEventListener("DOMContentLoaded",build,{once:true});
else
  build();

window.BioSafeConversationalShell={build,setMode,resetChat,submitActive,incompleteAsk};
})();
