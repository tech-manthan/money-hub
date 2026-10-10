(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const form = $('#wizard');
  let step = 1, customOn = false;

  const val = name => ($(`input[name="${name}"]:checked`, form) || {}).value || '';
  const sel = id => $('#' + id).value;
  const typeLabel = () => { const r = $(`input[name="product_type"]:checked`); return r ? $('b', r.parentElement).textContent : ''; };
  const niche = () => customOn ? $('#custom-niche').value.trim() : (($(`input[name="idea"]:checked`) || { dataset: {} }).dataset.niche || '');

  function pickType(key) { const r = $(`input[name="product_type"][value="${key}"]`); if (r) r.checked = true; syncType(); }
  function markSuggested(key) {
    $$('#types .tag').forEach(t => t.hidden = true);
    const r = $(`input[name="product_type"][value="${key}"]`);
    if (r) $('.tag', r.parentElement).hidden = false;
  }
  function pickIdea(radio) {
    radio.checked = true; setCustom(false);
    pickType(radio.dataset.type); markSuggested(radio.dataset.type);
    $('#msg-1').textContent = '';
  }
  function setCustom(on) {
    customOn = on; $('#custom-box').hidden = !on;
    $('#custom-toggle').textContent = on ? '← Back to the ready-made ideas' : '✍️ Type my own audience';
    $('#ideas').classList.toggle('dim', on);
    if (on) { $$('input[name="idea"]').forEach(r => r.checked = false); markSuggested(''); $('#custom-niche').focus(); }
  }
  function syncType() {
    const wall = val('product_type') === 'wall_art';
    $('#wall-opts').hidden = !wall; $('#ai-wrap').hidden = !wall;
    $('#learn-opts').hidden = !['activity_book', 'learning_workbook'].includes(val('product_type'));
    $('#level-wrap').hidden = val('product_type') !== 'activity_book'; $('#focus-wrap').hidden = val('product_type') !== 'learning_workbook';
    $('#oracle-opts').hidden = val('product_type') !== 'oracle_deck';
    $('#kids-opts').hidden = !['kids_coloring', 'sticker_sheets', 'character_clipart'].includes(val('product_type'));
    const r = $(`input[name="product_type"]:checked`);
    $('#eink-wrap').hidden = !(r && r.dataset.eink === '1');
    if ($('#eink-wrap').hidden) $('#opt-eink').checked = false;
  }
  const pick = arr => arr[Math.floor(Math.random() * arr.length)];
  function shuffleLook() {
    const r = $('input[name="lookmode"][value="pick"]'); r.checked = true; $('#look-pick').hidden = false;
    $('#use-brand').checked = false; $('#brand').disabled = true;
    const radios = n => $$(`input[name="${n}"]`).filter(x => x.value);
    pick(radios('palette')).checked = true; pick(radios('fonts')).checked = true;
    ['header', 'radius', 'grid'].forEach(id => { const o = [...$('#' + id).options].filter(x => x.value); $('#' + id).value = pick(o).value; });
    updatePreview();
  }
  let prevTimer = null;
  function updatePreview() {
    clearTimeout(prevTimer);
    prevTimer = setTimeout(() => {
      const q = new URLSearchParams();
      if (val('lookmode') === 'pick') {
        const l = look(); ['palette', 'fonts', 'header', 'radius', 'grid', 'brand'].forEach(k => l[k] && q.set(k, l[k]));
        $('#prev-note').textContent = '';
      } else $('#prev-note').textContent = 'Shown in a sample look. With "Choose for me" we match colours to your audience.';
      if ($('#opt-eink') && $('#opt-eink').checked) q.set('eink', '1');
      $('#look-preview').src = '/api/preview.png?' + q;
    }, 200);
  }

  $$('#recs .rec').forEach(b => b.addEventListener('click', () => {
    setCustom(true); $('#custom-niche').value = b.dataset.niche; pickType(b.dataset.type); markSuggested(b.dataset.type); $('#msg-1').textContent = '';
  }));
  $('#ideas').addEventListener('change', e => { if (e.target.name === 'idea') pickIdea(e.target); });
  $('#types').addEventListener('change', syncType);
  $('#custom-toggle').addEventListener('click', () => setCustom(!customOn));
  $('#surprise').addEventListener('click', () => {
    const all = $$('input[name="idea"]'); const r = pick(all);
    pickIdea(r); shuffleLook(); r.closest('.idea').scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
  $('#shuffle').addEventListener('click', shuffleLook);
  $$('input[name="lookmode"]').forEach(r => r.addEventListener('change', () => { $('#look-pick').hidden = val('lookmode') !== 'pick'; updatePreview(); }));
  $('#look-pick').addEventListener('change', e => { if (e.target.id === 'use-brand') $('#brand').disabled = !e.target.checked; updatePreview(); });
  $('#brand').addEventListener('input', updatePreview);
  $('#opt-eink').addEventListener('change', () => { updatePreview(); if (step === 3) renderLayouts(); });

  function go(n) {
    if (n > step && step === 1) {
      if (!niche()) { $('#msg-1').textContent = customOn ? 'Describe the people you want to help.' : 'Pick an idea above, or press “Surprise me”.'; return; }
      if (!val('product_type')) { $('#msg-1').textContent = 'Choose what to make.'; return; }
    }
    step = n;
    $$('.step').forEach(s => s.classList.toggle('on', +s.dataset.step === n));
    $$('#stepper li').forEach(li => { const k = +li.dataset.step; li.classList.toggle('on', k === n); li.classList.toggle('done', k < n); });
    if (n === 2) updatePreview();
    if (n === 3) { renderLayouts(); summarise(); }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  $$('[data-go]').forEach(b => b.addEventListener('click', () => go(+b.dataset.go)));

  function look() {
    if (val('lookmode') !== 'pick') return {};
    const o = { palette: $('#use-brand').checked ? '' : val('palette'), brand: $('#use-brand').checked ? sel('brand') : '', fonts: val('fonts'),
                header: sel('header'), radius: sel('radius'), grid: sel('grid'), seed: sel('seed') };
    if (val('product_type') === 'wall_art') { o.motif = sel('motif'); }
    return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== ''));
  }
  let extraLayouts = [];   // generated or described layouts the person added, kept while they browse
  const layoutQuery = () => {
    const r = $('input[name="product_type"]:checked'), l = look(), q = new URLSearchParams({ product_type: r.value });
    ['palette', 'fonts', 'brand'].forEach(k => l[k] && q.set(k, l[k]));
    if ($('#opt-eink').checked) q.set('eink', '1');
    return q;
  };
  const layCard = (key, title, desc, src, checked, attrs = '') => `<label class="opt layopt"><input type="radio" name="page_layout" value="${key}" ${checked ? 'checked' : ''} ${attrs}>
    <span class="in"><img loading="lazy" alt="Example ${title} page" src="${src}"><b>${title}</b><span class="meta">${desc}</span></span></label>`;
  function renderLayouts() {
    const r = $('input[name="product_type"]:checked'), wrap = $('#layout-wrap'), box = $('#layouts');
    const layouts = r ? JSON.parse(r.dataset.layouts || '{}') : {}, keys = Object.keys(layouts);
    wrap.hidden = keys.length < 2; $('#layout-tools').hidden = wrap.hidden;
    if (wrap.hidden) { box.innerHTML = ''; return; }
    if (box.dataset.type !== r.value) { extraLayouts = []; box.dataset.type = r.value; }
    const keep = val('page_layout'), q = layoutQuery();
    const presets = keys.map((k, i) => layCard(k, layouts[k].split(':')[0], layouts[k].split(': ')[1] || '', `/api/layout-preview.png?${q}&layout=${k}`, keep ? keep === k : i === 0));
    const extras = extraLayouts.map(x => x.spec
      ? layCard(x.key, /^auto/.test(x.name) ? 'Your layout' : x.name, `Designed from: ${x.text}`, `/api/layout-preview.png?${q}&layout=custom&spec=${encodeURIComponent(JSON.stringify(x.spec))}`, keep === x.key,
                `data-spec='${JSON.stringify(x.spec).replace(/'/g, '&#39;')}' data-text="${x.text.replace(/"/g, '&quot;')}"`)
      : layCard(x.key, `Generated layout ${extraLayouts.filter(y => !y.spec).indexOf(x) + 1}`, 'A new arrangement, made for you.', `/api/layout-preview.png?${q}&layout=${x.key}`, keep === x.key));
    box.innerHTML = presets.concat(extras).join('');
    if (step === 3) summarise();
  }
  $('#layouts').addEventListener('change', () => summarise());
  $('#gen-layout').addEventListener('click', () => {
    const key = 'auto:' + (1 + Math.floor(Math.random() * 99999));
    extraLayouts.push({ key }); renderLayouts(); const c = $(`input[value="${key}"]`); if (c) { c.checked = true; summarise(); c.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
  });
  $('#design-layout').addEventListener('click', async () => {
    const text = $('#layout-text').value.trim(), msg = $('#layout-msg'); if (!text) { msg.textContent = 'Type what you want first.'; return; }
    msg.textContent = 'Designing…'; $('#design-layout').disabled = true;
    try {
      const r = await fetch('/api/layout-spec', { method: 'POST', body: new URLSearchParams({ product_type: val('product_type'), text }) });
      if (!r.ok) throw new Error((await r.json()).detail || 'That did not work.');
      const j = await r.json(), key = 'custom:' + (extraLayouts.length + 1);
      extraLayouts.push({ key, spec: j.spec, name: j.name, text });
      msg.textContent = j.source === 'ai' ? 'Designed by your AI helper.' : 'No AI helper is set up, so here is a generated layout instead. Add one in Settings for exact results.';
      renderLayouts(); const c = $(`input[value="${key}"]`); if (c) c.checked = true;
    } catch (err) { msg.textContent = err.message; }
    $('#design-layout').disabled = false;
  });
  const markets = () => $$('input[name="mk"]:checked').map(x => x.value);
  function payload() {
    const o = { niche: niche(), product_type: val('product_type'), ...look() };
    if (!$('#opt-video').checked) o.no_video = '1';
    if ($('#opt-eink').checked) o.eink = '1';
    const pl = !$('#layout-wrap').hidden && val('page_layout');
    if (pl && pl.startsWith('custom')) { const c = $('input[name="page_layout"]:checked'); o.layout_spec = c.dataset.spec; }
    else if (pl) o.page_layout = pl;
    if (val('product_type') === 'wall_art' && $('#opt-ai').checked) o.ai_art = '1';
    if (val('product_type') === 'kids_coloring') { o.theme = $('#theme').value; o.age = $('#age').value; if ($('#pages').value) o.pages = $('#pages').value; }
    if (val('product_type') === 'activity_book') { o.level = $('#level').value; if ($('#pages2').value) o.pages = $('#pages2').value; }
    if (val('product_type') === 'learning_workbook') { o.focus = $('#focus').value; if ($('#pages2').value) o.pages = $('#pages2').value; }
    if (val('product_type') === 'oracle_deck') { o.deck = $('#deck').value; o.card_size = $('#card_size').value; }
    if (val('product_type') === 'character_clipart') { o.theme = $('#theme').value; if ($('#pages').value) o.count = $('#pages').value; }
    if (val('product_type') === 'sticker_sheets') { o.theme = $('#theme').value; if ($('#pages').value) o.stickers = $('#pages').value; }
    return o;
  }
  function summarise() {
    const l = look(), bits = [];
    if (l.palette) bits.push(`<b>${l.palette}</b> colours`);
    if (l.brand) bits.push(`your brand colour <b>${l.brand}</b>`);
    if ($('#opt-eink').checked) bits.push('<b>e-ink</b> black and white pages');
    if (l.fonts) bits.push(`<b>${l.fonts}</b> fonts`);
    $('#summary').innerHTML = `I'll make a <b>${typeLabel()}</b> for <b>${niche()}</b>, ` + (bits.length ? 'with ' + bits.join(' and ') + '.' : 'with a look chosen to suit them.');
    const p = payload(), flag = { palette: '--palette', brand: '--brand', fonts: '--fonts', header: '--header', radius: '--radius', grid: '--grid', motif: '--motif', seed: '--seed', theme: '--theme', age: '--age', pages: '--pages', stickers: '--stickers', count: '--count', deck: '--deck', card_size: '--card-size', level: '--level', focus: '--focus' };
    let cmd = `moneyhub make "${p.niche}" ${p.product_type}`;
    Object.entries(flag).forEach(([k, f]) => { if (p[k]) cmd += ` ${f} ${p[k]}`; });
    if (p.eink) cmd += ' --eink';
    const chosen = $('input[name="page_layout"]:checked');
    if (p.layout_spec && chosen) cmd += ` --layout-prompt "${(chosen.dataset.text || '').replace(/"/g, "'")}"`;
    if (p.page_layout && p.page_layout !== Object.keys(JSON.parse($('input[name="product_type"]:checked').dataset.layouts))[0]) cmd += ` --page-layout ${p.page_layout}`;
    const mk = markets(); if (mk.join() !== 'etsy,pinterest') cmd += ` --marketplaces ${mk.join(',')}`;
    if (p.no_video) cmd += ' --no-video';
    if (p.ai_art) cmd += ' --ai-art';
    $('#cli').textContent = cmd;
  }

  let timer = null;
  async function make() {
    const body = new FormData(); Object.entries(payload()).forEach(([k, v]) => body.append(k, v));
    markets().forEach(m => body.append('marketplaces', m));
    form.hidden = true; $('#stepper').hidden = true;
    const box = $('#progress'); box.hidden = false; $('#p-done').hidden = $('#p-error').hidden = true;
    $('#p-title').textContent = 'Making your product…'; $$('#p-steps li').forEach(li => li.className = '');
    try {
      const res = await fetch('/api/jobs', { method: 'POST', body });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const { jobs } = await res.json(); track(jobs[0]);
    } catch (err) { fail(err.message); }
  }
  function fail(msg) {
    clearInterval(timer);
    $('#p-title').textContent = 'Something went wrong'; $('#p-errmsg').textContent = msg; $('#p-error').hidden = false;
  }
  function track(id) {
    timer = setInterval(async () => {
      let j; try { j = await (await fetch('/api/jobs/' + id)).json(); } catch { return; }
      const items = $$('#p-steps li'); let cur = -1;
      items.forEach((li, i) => { if (j.log.some(m => m.startsWith(li.dataset.key))) cur = i; });
      items.forEach((li, i) => li.className = j.status === 'done' || i < cur ? 'done' : i === cur ? 'now' : '');
      if (j.status === 'done') {
        clearInterval(timer); $('#p-title').textContent = 'Done!'; $('#p-link').href = '/product/' + j.product_id; $('#p-done').hidden = false;
        if (j.qa === 'fail') $('#p-done .ok').textContent = 'Your product is ready, but some quality checks failed. Open it to see what to fix.';
      }
      if (j.status === 'error') fail(j.error || 'The product could not be made.');
    }, 1200);
  }

  form.addEventListener('submit', e => { e.preventDefault(); step === 3 ? make() : go(step + 1); });
  $('#retry').addEventListener('click', () => { $('#progress').hidden = true; form.hidden = false; $('#stepper').hidden = false; go(3); });
  syncType();
})();
