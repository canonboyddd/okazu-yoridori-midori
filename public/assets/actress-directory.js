(() => {
  const input = document.getElementById('actressSearch');
  const results = document.getElementById('actressSearchResults');
  const count = document.getElementById('actressSearchCount');
  const defaultGrid = document.getElementById('actressDirectoryGrid');
  if (!input || !results || !count || !defaultGrid) return;

  let actresses = [];

  function esc(value) {
    return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }

  function card(row) {
    const name = esc(row.name);
    const ruby = esc(row.ruby);
    const media = row.imageURL
      ? `<img src="${esc(row.imageURL)}" alt="${name}" loading="lazy" decoding="async">`
      : `<span class="actress-fallback">${name.slice(0,1)}</span>`;
    const inner = `<div class="actress-photo">${media}</div><div class="actress-card-body"><strong>${name}</strong>${ruby ? `<span>${ruby}</span>` : ''}</div>`;
    return row.hasDetail
      ? `<a class="actress-card" href="/ranking/actress/${encodeURIComponent(row.id)}/">${inner}</a>`
      : `<div class="actress-card">${inner}</div>`;
  }

  function render() {
    const q = input.value.trim().toLowerCase();
    if (!q) {
      results.hidden = true;
      defaultGrid.hidden = false;
      count.textContent = `${actresses.length.toLocaleString('ja-JP')}人収録`;
      return;
    }
    const matched = actresses.filter(row => {
      const name = String(row.name || '').toLowerCase();
      const ruby = String(row.ruby || '').toLowerCase();
      return name.includes(q) || ruby.includes(q);
    });
    defaultGrid.hidden = true;
    results.hidden = false;
    results.innerHTML = matched.slice(0, 120).map(card).join('') || '<div class="entity-empty">該当する女優が見つかりませんでした。</div>';
    count.textContent = `${matched.length.toLocaleString('ja-JP')}人該当${matched.length > 120 ? '（上位120人を表示）' : ''}`;
  }

  fetch('/data/fanza-actress-directory.json', {cache:'no-store'})
    .then(res => res.ok ? res.json() : Promise.reject(new Error('load failed')))
    .then(data => {
      actresses = Array.isArray(data.actresses) ? data.actresses : [];
      count.textContent = `${actresses.length.toLocaleString('ja-JP')}人収録`;
      input.addEventListener('input', render);
    })
    .catch(() => {
      count.textContent = '検索データを読み込めませんでした';
    });
})();
