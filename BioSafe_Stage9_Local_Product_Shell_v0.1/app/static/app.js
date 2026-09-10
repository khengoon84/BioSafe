
const output = document.getElementById('output');
const statusEl = document.getElementById('status');

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.target).classList.add('active');
  });
});

async function showRequest(promise) {
  statusEl.textContent = 'Running locally…';
  output.textContent = '';
  try {
    const r = await promise;
    const data = await r.json();
    output.textContent = JSON.stringify(data, null, 2);
    statusEl.textContent = r.ok ? 'Complete' : 'Error';
  } catch (e) {
    output.textContent = String(e);
    statusEl.textContent = 'Error';
  }
}

function runAsk() {
  const query = document.getElementById('askQuery').value.trim();
  showRequest(fetch('/api/ask', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query})
  }));
}

function runFormE() {
  const query = document.getElementById('formEQuery').value.trim();
  showRequest(fetch('/api/form-e', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query})
  }));
}

function runReview() {
  const file = document.getElementById('reviewFile').files[0];
  const query = document.getElementById('reviewQuery').value.trim();
  const fd = new FormData();
  if (file) fd.append('file', file);
  fd.append('query', query);
  showRequest(fetch('/api/review', {method:'POST', body:fd}));
}
