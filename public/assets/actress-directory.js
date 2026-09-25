(() => {
  const input = document.getElementById('actressSearch');
  const results = document.getElementById('actressSearchResults');
  const count = document.getElementById('actressSearchCount');
  const defaultGrid = document.getElementById('actressDirectoryGrid');
  const pagination = document.querySelector('.directory-pagination');
  if (!input || !results || !count || !defaultGrid) return;

  let actresses = [];
  let photoActresses = [];
  let activeKana = 'all';

  function esc(value) {
    return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }

  function card(row) {
    const name = esc(row.name);
    const ruby = esc(row.ruby);
    const media = `<img src="${esc(row.imageURL)}" alt="${name}" loading="lazy" decoding="async">`;
    const inner = `<div class="actress-photo">${media}</div><div class="actress-card-body"><strong>${name}</strong>${ruby ? `<span>${ruby}</span>` : ''}</div>`;
    return row.hasDetail
      ? `<a class="actress-card" href="/ranking/actress/${encodeURIComponent(row.id)}/">${inner}</a>`
      : `<div class="actress-card">${inner}</div>`;
  }

  function toHiragana(value) {
    return String(value || '')
      .normalize('NFKC')
      .replace(/[\u30a1-\u30f6]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0x60))
      .normalize('NFD')
      .replace(/[\u3099\u309a]/g, '');
  }

  function firstKana(row) {
    return toHiragana(row.ruby || row.name).trim().charAt(0);
  }

  function buildKanaNav() {
    if (document.getElementById('actressKanaNav')) return;
    const nav = document.createElement('div');
    nav.id = 'actressKanaNav';
    nav.className = 'actress-kana-nav';
    const groups = ['all','あ','い','う','え','お','か','き','く','け','こ','さ','し','す','せ','そ','た','ち','つ','て','と','な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ','ま','み','む','め','も','や','ゆ','よ','ら','り','る','れ','ろ','わ','を','ん'];
    const labels = {all:'すべて'};
    nav.innerHTML = groups.map(group => `<button type="button" data-kana="${group}" class="${group === 'all' ? 'active' : ''}">${labels[group] || group}</button>`).join('');
    input.closest('.actress-search').insertAdjacentElement('afterend', nav);
    nav.addEventListener('click', event => {
      const button = event.target.closest('button[data-kana]');
      if (!button) return;
      activeKana = button.dataset.kana || 'all';
      nav.querySelectorAll('button').forEach(btn => btn.classList.toggle('active', btn === button));
      render();
      const target = document.getElementById('actressSearchResults');
      if (activeKana !== 'all' && target) {
        target.scrollIntoView({behavior:'smooth', block:'start'});
      }
    });
  }

  function showDefault() {
    results.hidden = true;
    results.style.display = 'none';
    defaultGrid.hidden = false;
    defaultGrid.style.display = 'grid';
    if (pagination) {
      pagination.hidden = false;
      pagination.style.display = 'flex';
    }
  }

  function showResults() {
    defaultGrid.hidden = true;
    defaultGrid.style.display = 'none';
    results.hidden = false;
    results.style.display = 'grid';
    if (pagination) {
      pagination.hidden = true;
      pagination.style.display = 'none';
    }
  }

  function render() {
    const q = input.value.trim().toLowerCase();
    const filtering = Boolean(q) || activeKana !== 'all';

    if (!filtering) {
      showDefault();
      count.textContent = `写真あり ${photoActresses.length.toLocaleString('ja-JP')}人 / 全${actresses.length.toLocaleString('ja-JP')}人`;
      return;
    }

    const matched = photoActresses.filter(row => {
      const name = String(row.name || '').toLowerCase();
      const ruby = String(row.ruby || '').toLowerCase();
      const textMatch = !q || name.includes(q) || ruby.includes(q);
      const kanaMatch = activeKana === 'all' || firstKana(row) === activeKana;
      return textMatch && kanaMatch;
    });

    showResults();
    results.innerHTML = matched.slice(0, 200).map(card).join('') || '<div class="entity-empty">該当する女優が見つかりませんでした。</div>';
    count.textContent = `${matched.length.toLocaleString('ja-JP')}人該当${matched.length > 200 ? '（先頭200人を表示）' : ''}`;
  }

  buildKanaNav();

  fetch('/data/fanza-actress-directory.json', {cache:'no-store'})
    .then(res => res.ok ? res.json() : Promise.reject(new Error('load failed')))
    .then(data => {
      actresses = Array.isArray(data.actresses) ? data.actresses : [];
      photoActresses = actresses.filter(row => String(row.imageURL || '').trim());
      count.textContent = `写真あり ${photoActresses.length.toLocaleString('ja-JP')}人 / 全${actresses.length.toLocaleString('ja-JP')}人`;
      input.addEventListener('input', render);
    })
    .catch(() => {
      count.textContent = '検索データを読み込めませんでした';
    });
})();
