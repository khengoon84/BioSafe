const output = document.getElementById('output');
const statusEl = document.getElementById('status');

const BIOSAFE_CRA_SESSION_KEY = 'biosafe_cra_session_id_v1';

function getCraSessionId() {
  return localStorage.getItem(BIOSAFE_CRA_SESSION_KEY) || '';
}
function setCraSessionId(value) {
  if (value) localStorage.setItem(BIOSAFE_CRA_SESSION_KEY, value);
}
function clearCraSessionId() {
  localStorage.removeItem(BIOSAFE_CRA_SESSION_KEY);
}

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.target).classList.add('active');
  });
});

function userVisiblePayload(data) {
  if (!data || typeof data !== 'object') return data;
  if (data.session_id) setCraSessionId(data.session_id);

  if (data.response && typeof data.response === 'object') {
    const response = {...data.response};
    delete response._cra_adapter;
    delete response._cra_quality;
    delete response._meta;
    return response;
  }
  return data;
}

async function showRequest(promise) {
  statusEl.textContent = 'Running locally…';
  output.textContent = '';
  try {
    const r = await promise;
    const data = await r.json();
    const visible = userVisiblePayload(data);
    output.textContent = JSON.stringify(visible, null, 2);
    statusEl.textContent = r.ok ? 'Complete' : 'Error';
  } catch (e) {
    output.textContent = JSON.stringify({
      conclusion: 'BioSafe could not reach the local CRA service.',
      limitations: [String(e)]
    }, null, 2);
    statusEl.textContent = 'Error';
  }
}

function runAsk() {
  const query = document.getElementById('askQuery').value.trim();
  showRequest(fetch('/api/cra/ask', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query, session_id:getCraSessionId()})
  }));
}

function runFormE() {
  const query = document.getElementById('formEQuery').value.trim();
  showRequest(fetch('/api/cra/form-e', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query, session_id:getCraSessionId()})
  }));
}

function runReview() {
  const file = document.getElementById('reviewFile').files[0];
  const query = document.getElementById('reviewQuery').value.trim();
  const fd = new FormData();
  if (file) fd.append('file', file);
  fd.append('query', query);
  fd.append('session_id', getCraSessionId());
  showRequest(fetch('/api/cra/review', {method:'POST', body:fd}));
}

window.BioSafeCRAClient = {
  getSessionId:getCraSessionId,
  clearSessionId:clearCraSessionId,
  resetSession:async function(){
    const sid=getCraSessionId();
    clearCraSessionId();
    if(!sid) return {reset:false};
    try{
      const r=await fetch('/api/cra/session/reset',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({session_id:sid})
      });
      return await r.json();
    }catch(_){
      return {reset:false};
    }
  }
};
