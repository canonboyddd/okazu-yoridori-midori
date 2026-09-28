// Full-catalog sharded search loader v20260928-2348
(() => {
  const app = document.querySelector('#catalogAdvancedSearch');
  if (!app) return;

  const PAGE_SIZE = 60;
  let all = [];
  let filtered = [];
  let page = 1;

  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const norm = value => String(value == null ? '' : value).normalize('NFKC').trim().toLowerCase();
  const num = value => {
    const n = Number(String(value == null ? '' : value).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? n : 0;
  };

  function productCard(item) {
    const discount = Number(item.discountRate || 0);
    const reviewCount = Number(item.reviewCount || 0);
    const actress = Array.isArray(item.actresses) ? item.actresses.slice(0, 2).join(' / ') : '';
    const sub = [item.maker, actress].filter(Boolean).join(' / ');
    const review = item.reviewAverage ? `★ ${esc(item.reviewAverage)}${reviewCount ? ` (${reviewCount})` : ''}` : '';
    const badge = discount > 0 ? `<span class="fc-discount">${discount}%OFF</span>` : '';
    return `<a class="fc-card catalog-search-card" href="/products/view/?id=${encodeURIComponent(item.id || '')}" data-product-id="${esc(item.id || '')}">
      <div class="fc-img">${badge}<img src="${esc(item.image || '')}" alt="${esc(item.title || 'FANZA作品')}" loading="lazy" decoding="async"></div>
      <div class="fc-body"><strong>${esc(item.title || 'FANZA作品')}</strong><span>${esc(sub)}</span><b>${esc(item.price || '公式で価格確認')}</b>${review ? `<small>${review}</small>` : ''}</div>
    </a>`;
  }

  function uniqueSorted(values) {
    return [...new Set(values.map(x => String(x || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'ja'));
  }

  function controlMarkup(makers, genres) {
    return `<div class="catalog-search-controls">
      <label class="wide">作品名・キーワード<input type="search" data-keyword placeholder="作品名を入力"></label>
      <label>女優<input type="search" data-actress placeholder="例：MINAMO"></label>
      <label>ジャンル<input type="search" data-genre list="catalogGenreList" placeholder="ジャンル名"></label>
      <label>メーカー<input type="search" data-maker list="catalogMakerList" placeholder="メーカー名"></label>
      <label>最低価格<input type="number" data-min-price min="0" step="100" placeholder="0"></label>
      <label>最高価格<input type="number" data-max-price min="0" step="100" placeholder="上限なし"></label>
      <label>最低評価<select data-min-rating><option value="0">指定なし</option><option value="3">★3以上</option><option value="3.5">★3.5以上</option><option value="4">★4以上</option><option value="4.5">★4.5以上</option></select></label>
      <label>並び順<select data-sort><option value="new">新着順</option><option value="popular">人気順</option><option value="rating">評価順</option><option value="priceAsc">価格が安い順</option><option value="priceDesc">価格が高い順</option><option value="sale">割引率順</option></select></label>
      <label class="check"><input type="checkbox" data-sale> セール作品のみ</label>
      <button type="button" data-reset>条件をリセット</button>
    </div>
    <datalist id="catalogGenreList">${genres.map(x => `<option value="${esc(x)}"></option>`).join('')}</datalist>
    <datalist id="catalogMakerList">${makers.map(x => `<option value="${esc(x)}"></option>`).join('')}</datalist>
    <div class="catalog-search-summary"><strong data-count>0作品</strong><span>取得済みFANZAカタログから検索</span></div>
    <div class="fc-grid" data-grid></div>
    <div class="catalog-search-empty" data-empty hidden>条件に一致する作品がありません。</div>
    <nav class="fc-pagination" data-pagination><button type="button" data-prev>← 前へ</button><span data-page></span><button type="button" data-next>次へ →</button></nav>`;
  }

  function injectStyle() {
    if (document.querySelector('style[data-catalog-search-style]')) return;
    const style = document.createElement('style');
    style.dataset.catalogSearchStyle = '1';
    style.textContent = `
      .catalog-search-app{margin-top:22px}
      .catalog-search-controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:16px;border:1px solid #e2e8f0;border-radius:16px;background:#f8fafc}
      .catalog-search-controls label{display:flex;flex-direction:column;gap:6px;font-size:.82rem;font-weight:800;color:#475569}
      .catalog-search-controls .wide{grid-column:span 2}
      .catalog-search-controls input,.catalog-search-controls select{box-sizing:border-box;width:100%;border:1px solid #cbd5e1;border-radius:10px;background:#fff;padding:10px 11px;color:#0f172a;font:inherit}
      .catalog-search-controls .check{flex-direction:row;align-items:center;align-self:end;min-height:42px}
      .catalog-search-controls button{align-self:end;min-height:42px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;font-weight:800;cursor:pointer}
      .catalog-search-summary{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:18px 0 14px;color:#64748b}.catalog-search-summary strong{font-size:1.15rem;color:#0f172a}
      .catalog-search-empty{padding:32px;text-align:center;border:1px dashed #cbd5e1;border-radius:14px;color:#64748b}
      .fc-pagination{display:flex;align-items:center;justify-content:center;gap:14px;margin:28px 0}.fc-pagination button{border:1px solid #d7dce4;border-radius:999px;background:#fff;padding:10px 16px;font-weight:800;cursor:pointer}.fc-pagination button:disabled{opacity:.35;cursor:not-allowed}.fc-pagination span{min-width:100px;text-align:center;font-weight:800}
      @media(max-width:900px){.catalog-search-controls{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @media(max-width:620px){.catalog-search-controls{grid-template-columns:1fr}.catalog-search-controls .wide{grid-column:auto}.catalog-search-summary{align-items:flex-start;flex-direction:column}}
    `;
    document.head.appendChild(style);
  }

  function sortItems(items, mode) {
    const out = [...items];
    if (mode === 'popular') out.sort((a,b) => Number(b.reviewCount||0)-Number(a.reviewCount||0) || Number(b.reviewAverage||0)-Number(a.reviewAverage||0));
    else if (mode === 'rating') out.sort((a,b) => Number(b.reviewAverage||0)-Number(a.reviewAverage||0) || Number(b.reviewCount||0)-Number(a.reviewCount||0));
    else if (mode === 'priceAsc') out.sort((a,b) => (Number(a.priceValue)||Number.MAX_SAFE_INTEGER)-(Number(b.priceValue)||Number.MAX_SAFE_INTEGER));
    else if (mode === 'priceDesc') out.sort((a,b) => Number(b.priceValue||0)-Number(a.priceValue||0));
    else if (mode === 'sale') out.sort((a,b) => Number(b.discountRate||0)-Number(a.discountRate||0) || String(b.date||'').localeCompare(String(a.date||'')));
    else out.sort((a,b) => String(b.date||'').localeCompare(String(a.date||'')) || Number(b.reviewCount||0)-Number(a.reviewCount||0));
    return out;
  }

  function paramsFromControls() {
    return {
      q: app.querySelector('[data-keyword]').value.trim(),
      actress: app.querySelector('[data-actress]').value.trim(),
      genre: app.querySelector('[data-genre]').value.trim(),
      maker: app.querySelector('[data-maker]').value.trim(),
      minPrice: app.querySelector('[data-min-price]').value.trim(),
      maxPrice: app.querySelector('[data-max-price]').value.trim(),
      minRating: app.querySelector('[data-min-rating]').value,
      sort: app.querySelector('[data-sort]').value,
      sale: app.querySelector('[data-sale]').checked,
    };
  }

  function syncUrl(p) {
    const u = new URL(location.href);
    const map = {q:p.q, actress:p.actress, genre:p.genre, maker:p.maker, min_price:p.minPrice, max_price:p.maxPrice, rating:p.minRating !== '0' ? p.minRating : '', sort:p.sort !== 'new' ? p.sort : '', sale:p.sale ? '1' : ''};
    Object.entries(map).forEach(([k,v]) => v ? u.searchParams.set(k, v) : u.searchParams.delete(k));
    history.replaceState(null, '', u.pathname + (u.searchParams.toString() ? '?' + u.searchParams.toString() : ''));
  }

  function loadUrlParams() {
    const p = new URLSearchParams(location.search);
    app.querySelector('[data-keyword]').value = p.get('q') || '';
    app.querySelector('[data-actress]').value = p.get('actress') || '';
    app.querySelector('[data-genre]').value = p.get('genre') || '';
    app.querySelector('[data-maker]').value = p.get('maker') || '';
    app.querySelector('[data-min-price]').value = p.get('min_price') || '';
    app.querySelector('[data-max-price]').value = p.get('max_price') || '';
    app.querySelector('[data-min-rating]').value = p.get('rating') || '0';
    app.querySelector('[data-sort]').value = p.get('sort') || 'new';
    app.querySelector('[data-sale]').checked = p.get('sale') === '1';
  }

  function applyFilters(track = false) {
    const p = paramsFromControls();
    const q = norm(p.q), actress = norm(p.actress), genre = norm(p.genre), maker = norm(p.maker);
    const minPrice = num(p.minPrice), maxPrice = num(p.maxPrice), minRating = Number(p.minRating || 0);
    filtered = all.filter(item => {
      if (q && !norm(item.title).includes(q)) return false;
      if (actress && !norm((item.actresses || []).join(' ')).includes(actress)) return false;
      if (genre && !norm((item.genres || []).join(' ')).includes(genre)) return false;
      if (maker && !norm(item.maker).includes(maker)) return false;
      const pv = Number(item.priceValue || 0);
      if (minPrice && (!pv || pv < minPrice)) return false;
      if (maxPrice && (!pv || pv > maxPrice)) return false;
      if (minRating && Number(item.reviewAverage || 0) < minRating) return false;
      if (p.sale && Number(item.discountRate || 0) <= 0) return false;
      return true;
    });
    filtered = sortItems(filtered, p.sort);
    page = 1;
    syncUrl(p);
    render(false);
    if (track && window.trackOpsEvent) {
      window.trackOpsEvent('catalog_search', {
        program: 'fanza_catalog_search',
        placement: [p.q,p.actress,p.genre,p.maker].filter(Boolean).join(' | ').slice(0,160),
        search_query: p.q,
        actress: p.actress,
        genre: p.genre,
        maker: p.maker,
        result_count: filtered.length,
      });
    }
  }

  function render(scroll) {
    const grid = app.querySelector('[data-grid]');
    const count = app.querySelector('[data-count]');
    const empty = app.querySelector('[data-empty]');
    const prev = app.querySelector('[data-prev]');
    const next = app.querySelector('[data-next]');
    const pageEl = app.querySelector('[data-page]');
    const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (page > pages) page = pages;
    const start = (page - 1) * PAGE_SIZE;
    grid.innerHTML = filtered.slice(start, start + PAGE_SIZE).map(productCard).join('');
    count.textContent = `${filtered.length.toLocaleString()}作品`;
    empty.hidden = filtered.length > 0;
    prev.disabled = !filtered.length || page <= 1;
    next.disabled = !filtered.length || page >= pages;
    pageEl.textContent = filtered.length ? `${page} / ${pages}` : '0 / 0';
    if (scroll) app.scrollIntoView({behavior:'smooth',block:'start'});
  }

  function bind() {
    let timer = 0;
    app.querySelectorAll('input[type="search"],input[type="number"]').forEach(el => el.addEventListener('input', () => {
      clearTimeout(timer); timer = setTimeout(() => applyFilters(true), 180);
    }));
    app.querySelectorAll('select,input[type="checkbox"]').forEach(el => el.addEventListener('change', () => applyFilters(true)));
    app.querySelector('[data-reset]').addEventListener('click', () => {
      app.querySelectorAll('input[type="search"],input[type="number"]').forEach(x => x.value = '');
      app.querySelector('[data-min-rating]').value = '0';
      app.querySelector('[data-sort]').value = 'new';
      app.querySelector('[data-sale]').checked = false;
      applyFilters(true);
    });
    app.querySelector('[data-prev]').addEventListener('click', () => { if (page > 1) { page--; render(true); } });
    app.querySelector('[data-next]').addEventListener('click', () => { const pages = Math.max(1, Math.ceil(filtered.length/PAGE_SIZE)); if (page < pages) { page++; render(true); } });
  }

  async function fetchShard(ref, index, total) {
    const file = String(ref && ref.file || '');
    if (!file) return [];
    const status = app.querySelector('.catalog-search-loading');
    if (status) status.textContent = `検索データを読み込み中です… ${index + 1}/${total}`;
    const res = await fetch(`${file}?v=20260928-2348`, {cache:'no-cache'});
    if (!res.ok) throw new Error(`Shard HTTP ${res.status}: ${file}`);
    const payload = await res.json();
    return Array.isArray(payload.items) ? payload.items : [];
  }

  async function init() {
    try {
      const res = await fetch('/data/catalog-search-index.json?v=20260928-2348', {cache:'no-cache'});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const shards = Array.isArray(data.shards) ? data.shards : [];
      if (!shards.length) throw new Error('Search shard manifest is empty');

      const chunks = [];
      for (let i = 0; i < shards.length; i++) {
        chunks.push(await fetchShard(shards[i], i, shards.length));
      }
      all = chunks.flat();
      if (Number(data.count || 0) && all.length !== Number(data.count)) {
        throw new Error(`Search count mismatch: ${all.length}/${data.count}`);
      }

      const makers = uniqueSorted(all.map(x => x.maker));
      const genres = uniqueSorted(all.flatMap(x => Array.isArray(x.genres) ? x.genres : []));
      injectStyle();
      app.innerHTML = controlMarkup(makers, genres);
      loadUrlParams();
      bind();
      applyFilters(false);
    } catch (err) {
      app.innerHTML = '<div class="catalog-search-empty">検索データを読み込めませんでした。時間をおいて再度お試しください。</div>';
      console.warn('Catalog search load failed', err);
    }
  }

  init();
})();
