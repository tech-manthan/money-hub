function copyText(id, btn) {
  const el = document.getElementById(id);
  navigator.clipboard.writeText(el.dataset.text || el.innerText).then(() => {
    const t = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => btn.textContent = t, 1200);
  });
}
document.addEventListener('click', e => {
  const tab = e.target.closest('[data-tab]');
  if (!tab) return;
  const group = tab.dataset.group;
  document.querySelectorAll(`[data-group="${group}"]`).forEach(b => b.classList.remove('on'));
  document.querySelectorAll(`.tabpane[data-group="${group}"]`).forEach(p => p.classList.remove('on'));
  tab.classList.add('on');
  document.getElementById(tab.dataset.tab).classList.add('on');
});
const form = document.getElementById('make-form');
if (form) {
  const out = document.getElementById('jobs');
  const type = document.getElementById('product_type');
  const sizeMap = JSON.parse(document.getElementById('size-map').textContent);
  const sizeBox = document.getElementById('size-box');
  const weeks = document.getElementById('weeks-wrap');
  function syncType() {
    const opt = type.selectedOptions[0];
    const defaults = (opt.dataset.defaults || '').split(',');
    sizeBox.innerHTML = '';
    (sizeMap[type.value] || []).forEach(([key, label]) => {
      const l = document.createElement('label');
      l.innerHTML = `<input type="checkbox" name="sizes" value="${key}" ${defaults.includes(key) ? 'checked' : ''}> ${label}`;
      sizeBox.appendChild(l);
    });
    weeks.style.display = type.value === 'weekly_planner' ? '' : 'none';
    document.getElementById('oracle-wrap').hidden = type.value !== 'oracle_deck';
    document.getElementById('kids-wrap').hidden = !['kids_coloring', 'sticker_sheets'].includes(type.value);
    document.getElementById('type-desc').textContent = opt.dataset.desc || '';
  }
  type.addEventListener('change', syncType); syncType();
  const nicheInput = document.getElementById('niche');
  nicheInput.addEventListener('change', async () => {
    const first = nicheInput.value.split(',')[0].trim();
    if (!first) return;
    const r = await (await fetch('/api/niche?q=' + encodeURIComponent(first))).json();
    document.getElementById('niche-note').textContent = r.in_library
      ? `Using the built-in "${r.name}" profile for ${r.audience}.`
      : 'Custom niche: an LLM will research it when one is available; offline mode uses a generic profile.';
  });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const res = await fetch('/api/jobs', { method: 'POST', body: new FormData(form) });
    const { jobs } = await res.json();
    jobs.forEach(id => track(id));
  });
  function track(id) {
    const row = document.createElement('div'); row.className = 'job'; row.innerHTML = '<span class="spin"></span><span class="t">queued…</span>';
    out.prepend(row);
    const timer = setInterval(async () => {
      const j = await (await fetch('/api/jobs/' + id)).json();
      const last = j.log[j.log.length - 1] || j.status;
      row.querySelector('.t').textContent = `${j.label}: ${last}`;
      if (j.status === 'done') { clearInterval(timer); row.innerHTML = `<span class="badge ${j.qa}">${j.qa}</span> <a href="/product/${j.product_id}">${j.label} - open</a>`; }
      if (j.status === 'error') { clearInterval(timer); row.innerHTML = `<span class="badge fail">error</span> ${j.label}: ${j.error}`; }
    }, 1500);
  }
}

/* Confirm dialog: any form with data-confirm-title opens it instead of the browser's alert. confirmDialog() can be used from scripts too. */
function confirmDialog(o) {
  return new Promise(resolve => {
    let d = document.getElementById('confirm-dialog');
    if (d) d.remove();
    d = document.createElement('dialog');
    d.id = 'confirm-dialog'; d.className = 'confirm';
    d.setAttribute('aria-labelledby', 'cf-title');
    const esc = s => String(s || '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    d.innerHTML = `<form method="dialog"><div class="cf-body"><div class="cf-icon" aria-hidden="true">${o.icon || '🗑'}</div><div>
      <h3 id="cf-title">${esc(o.title || 'Are you sure?')}</h3>
      ${o.name ? `<div class="cf-name">${esc(o.name)}</div>` : ''}
      ${o.message ? `<p>${esc(o.message)}</p>` : ''}
      ${o.note ? `<div class="cf-note">${esc(o.note)}</div>` : ''}</div></div>
      <div class="cf-actions"><button type="button" class="ghost cf-cancel" value="cancel">Cancel</button>
      <button type="button" class="cf-danger" value="ok">${esc(o.confirm || 'Delete')}</button></div></form>`;
    document.body.appendChild(d);
    const ok = d.querySelector('.cf-danger'), cancel = d.querySelector('.cf-cancel');
    let result = false;
    ok.addEventListener('click', () => { result = true; d.close(); });
    cancel.addEventListener('click', () => d.close());
    d.addEventListener('click', e => { if (e.target === d) d.close(); });   // backdrop click
    d.addEventListener('close', () => { d.remove(); resolve(result); });
    d.showModal();
    cancel.focus();   // the safe choice is focused, so Enter never deletes by accident
  });
}
document.addEventListener('submit', async e => {
  const f = e.target.closest('form[data-confirm-title]');
  if (!f || f.dataset.confirmed) return;
  e.preventDefault();
  const yes = await confirmDialog({ title: f.dataset.confirmTitle, name: f.dataset.confirmName, message: f.dataset.confirmMessage,
                                    note: f.dataset.confirmNote, confirm: f.dataset.confirmLabel });
  if (!yes) return;
  f.dataset.confirmed = '1';
  const b = f.querySelector('button'); if (b) { b.disabled = true; b.textContent = 'Deleting…'; }
  f.submit();
});
function toast(msg) {
  const t = document.createElement('div');
  t.className = 'toast'; t.setAttribute('role', 'status'); t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 250); }, 3200);
}
(function () {   // "?deleted=Name" after a delete: say so once, then clean the address bar
  const q = new URLSearchParams(location.search);
  if (q.has('deleted')) {
    toast('Deleted: ' + q.get('deleted'));
    q.delete('deleted');
    history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : ''));
  }
})();

