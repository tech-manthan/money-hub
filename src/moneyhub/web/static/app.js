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
