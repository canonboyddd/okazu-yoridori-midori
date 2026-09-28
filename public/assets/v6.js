document.addEventListener('DOMContentLoaded', () => {
  const q = document.querySelector('#siteSearch');
  const cards = [...document.querySelectorAll('.content-card')];
  const empty = document.querySelector('.site-search-empty');
  if (q && cards.length) {
    q.addEventListener('input', () => {
      const needle = q.value.trim().toLowerCase();
      let shown = 0;
      cards.forEach(card => {
        const ok = !needle || card.textContent.toLowerCase().includes(needle);
        card.classList.toggle('hidden', !ok);
        if (ok) shown++;
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
    });
  }

  const cfg = window.AFFILIATE_CONFIG || {};
  if (cfg.approved && cfg.affiliateId) {
    document.querySelectorAll('.affiliate-slot').forEach(el => el.style.display = 'block');
  }

  const entityMatch = location.pathname.match(/^\/ranking\/(genre|maker|actress)\/([^/]+)\/?$/);
  if (entityMatch && entityMatch[2] !== 'aliases') loadFullEntityCatalog(entityMatch[1], entityMatch[2]);

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[ch]);
  }

  function numberValue(value) {
    const digits = String(value == null ? '' : value).replace(/[^0-9]/g, '');
    return digits ? Number(digits) : Number.MAX_SAFE_INTEGER;
  }

  function productCard(item) {
    const discount = Number(item.discountRate || 0);
    const reviewCount = Number(item.reviewCount || 0);
    const actresses = Array.isArray(item.actresses) ? item.actresses.filter(Boolean).slice(0, 2).join(' / ') : '';
    const sub = [item.maker, actresses].filter(Boolean).join(' / ');
    const price = item.price || '公式で価格確認';
    const review = item.reviewAverage ? `★ ${esc(item.reviewAverage)}${reviewCount ? ` (${reviewCount})` : ''}` : '';
    const image = item.image ? `<img src="${esc(item.image)}" alt="${esc(item.title)}" loading="lazy" decoding="async">` : '';
    const badge = discount > 0 ? `<span class="entity-discount">${discount}%OFF</span>` : '';
    return `<a class="entity-product-card" href="/products/view/?id=${encodeURIComponent(item.id || '')}" data-product-id="${esc(item.id || '')}">
      <div class="entity-product-image">${badge}${image}</div>
      <div class="entity-product-body">
        <div class="entity-title">${esc(item.title || 'FANZA作品')}</div>
        ${sub ? `<div class="entity-sub">${esc(sub)}</div>` : ''}
        <div class="entity-meta"><span class="entity-price">${esc(price)}</span>${review ? `<span>${review}</span>` : ''}</div>
      </div>
    </a>`;
  }

  function sortItems(items, mode) {
    const out = [...items];
    if (mode === 'popular') {
      out.sort((a, b) => Number(b.reviewCount || 0) - Number(a.reviewCount || 0) || Number(b.reviewAverage || 0) - Number(a.reviewAverage || 0));
    } else if (mode === 'rating') {
      out.sort((a, b) => Number(b.reviewAverage || 0) - Number(a.reviewAverage || 0) || Number(b.reviewCount || 0) - Number(a.reviewCount || 0));
    } else if (mode === 'price') {
      out.sort((a, b) => numberValue(a.priceValue ?? a.price) - numberValue(b.priceValue ?? b.price));
    } else if (mode === 'sale') {
      out.sort((a, b) => Number(b.discountRate || 0) - Number(a.discountRate || 0) || String(b.date || '').localeCompare(String(a.date || '')));
    } else {
      out.sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')) || Number(b.reviewCount || 0) - Number(a.reviewCount || 0));
    }
    return out;
  }

  function uniqueSorted(values) {
    return [...new Set(values.map(x => String(x || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'ja'));
  }

  async function loadFullEntityCatalog(entityType, entityId) {
    const existingGrid = document.querySelector('.entity-product-grid, .fc-grid');
    if (!existingGrid || document.querySelector('[data-full-entity-catalog="1"]')) return;

    try {
      const res = await fetch(`/data/${entityType}-catalog/${encodeURIComponent(entityId)}.json?v=20260929-0825`, {cache: 'no-cache'});
      if (!res.ok) return;
      const data = await res.json();
      let items = Array.isArray(data.items) ? data.items : [];
      if (!items.length && Array.isArray(data.shards) && data.shards.length) {
        const parts = await Promise.all(data.shards.map(async shard => {
          const shardRes = await fetch(`${shard.file}?v=20260929-0825`, {cache: 'no-cache'});
          if (!shardRes.ok) throw new Error(`HTTP ${shardRes.status}: ${shard.file}`);
          const shardData = await shardRes.json();
          return Array.isArray(shardData.items) ? shardData.items : [];
        }));
        items = parts.flat();
      }
      if (!items.length) return;

      const PAGE_SIZE = 60;
      let page = 1;
      let filtered = [...items];

      const label = entityType === 'genre' ? 'ジャンル' : entityType === 'maker' ? 'メーカー' : '女優';
      const section = document.createElement('section');
      section.dataset.fullEntityCatalog = '1';
      section.dataset.entityType = entityType;
      section.dataset.entityId = entityId;
      section.className = 'genre-full-catalog';

      const makerOptions = uniqueSorted(items.map(x => x.maker));
      const genreOptions = uniqueSorted(items.flatMap(x => Array.isArray(x.genres) ? x.genres : []));
      const aliasText = Array.isArray(data.aliases) && data.aliases.length ? `別名義：${data.aliases.join(' / ')}` : '';

      section.innerHTML = `
        <div class="genre-full-head">
          <div><span class="update-badge">全カタログ集計</span><h2>${esc(data.name || `この${label}`)} 全${items.length.toLocaleString()}作品</h2>${aliasText ? `<p class="catalog-aliases">${esc(aliasText)}</p>` : ''}</div>
          <strong data-result-count>${items.length.toLocaleString()}作品</strong>
        </div>
        <p class="genre-full-copy">取得済みFANZAカタログ全体から、この${label}に該当する作品を表示しています。</p>
        <div class="catalog-controls">
          <label>並び順
            <select data-sort>
              <option value="new">新着順</option>
              <option value="popular">人気順</option>
              <option value="rating">評価順</option>
              <option value="price">価格順</option>
              <option value="sale">セール順</option>
            </select>
          </label>
          ${entityType !== 'actress' ? `<label>女優名<input type="search" data-actress placeholder="女優名で絞り込み"></label>` : ''}
          ${entityType !== 'maker' ? `<label>メーカー<select data-maker><option value="">すべてのメーカー</option>${makerOptions.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join('')}</select></label>` : ''}
          ${entityType !== 'genre' ? `<label>ジャンル<select data-genre><option value="">すべてのジャンル</option>${genreOptions.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join('')}</select></label>` : ''}
          <label class="catalog-sale-only"><input type="checkbox" data-sale-only> セール作品のみ</label>
        </div>
        <div class="entity-product-grid genre-full-grid"></div>
        <div class="catalog-empty" data-empty hidden>条件に一致する作品がありません。</div>
        <nav class="genre-pagination" aria-label="${label}作品ページ送り">
          <button type="button" data-prev>← 前へ</button>
          <span data-page></span>
          <button type="button" data-next>次へ →</button>
        </nav>`;

      existingGrid.insertAdjacentElement('afterend', section);
      const grid = section.querySelector('.genre-full-grid');
      const pageLabel = section.querySelector('[data-page]');
      const prev = section.querySelector('[data-prev]');
      const next = section.querySelector('[data-next]');
      const resultCount = section.querySelector('[data-result-count]');
      const sort = section.querySelector('[data-sort]');
      const actress = section.querySelector('[data-actress]');
      const maker = section.querySelector('[data-maker]');
      const genre = section.querySelector('[data-genre]');
      const saleOnly = section.querySelector('[data-sale-only]');
      const emptyBox = section.querySelector('[data-empty]');

      if (!document.querySelector('style[data-full-catalog-style]')) {
        const style = document.createElement('style');
        style.dataset.fullCatalogStyle = '1';
        style.textContent = `
          .genre-full-catalog{margin-top:38px;padding-top:30px;border-top:1px solid #e5e7eb}
          .genre-full-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-bottom:8px}
          .genre-full-head h2{margin:7px 0 0}
          .genre-full-head>strong{font-size:1.15rem;white-space:nowrap}
          .catalog-aliases{margin:6px 0 0;color:#7c3aed;font-weight:700;font-size:.88rem}
          .genre-full-copy{margin:0 0 18px;color:#64748b;line-height:1.7}
          .catalog-controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 20px;padding:14px;border:1px solid #e5e7eb;border-radius:14px;background:#f8fafc}
          .catalog-controls label{display:flex;flex-direction:column;gap:6px;font-size:.82rem;font-weight:800;color:#475569}
          .catalog-controls select,.catalog-controls input[type="search"]{width:100%;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:10px;background:#fff;padding:10px 11px;font:inherit;color:#0f172a}
          .catalog-controls .catalog-sale-only{flex-direction:row;align-items:center;align-self:end;min-height:41px}
          .genre-pagination{display:flex;align-items:center;justify-content:center;gap:14px;margin:26px 0 8px}
          .genre-pagination button{border:1px solid #d7dce4;border-radius:999px;background:#fff;padding:10px 16px;font-weight:800;cursor:pointer}
          .genre-pagination button:disabled{opacity:.35;cursor:not-allowed}
          .genre-pagination span{min-width:110px;text-align:center;font-weight:800;color:#334155}
          .catalog-empty{padding:28px;text-align:center;color:#64748b;border:1px dashed #cbd5e1;border-radius:14px}
          @media(max-width:900px){.catalog-controls{grid-template-columns:repeat(2,minmax(0,1fr))}}
          @media(max-width:620px){.genre-full-head{align-items:flex-start;flex-direction:column}.catalog-controls{grid-template-columns:1fr}.genre-pagination{gap:8px}.genre-pagination button{padding:9px 12px}}
        `;
        document.head.appendChild(style);
      }

      function applyFilters(track) {
        const actressNeedle = actress ? actress.value.trim().toLowerCase() : '';
        const makerNeedle = maker ? maker.value : '';
        const genreNeedle = genre ? genre.value : '';
        filtered = items.filter(item => {
          if (saleOnly && saleOnly.checked && Number(item.discountRate || 0) <= 0) return false;
          if (makerNeedle && String(item.maker || '') !== makerNeedle) return false;
          if (genreNeedle && !(Array.isArray(item.genres) ? item.genres : []).includes(genreNeedle)) return false;
          if (actressNeedle) {
            const hay = (Array.isArray(item.actresses) ? item.actresses : []).join(' ').toLowerCase();
            if (!hay.includes(actressNeedle)) return false;
          }
          return true;
        });
        filtered = sortItems(filtered, sort ? sort.value : 'new');
        page = 1;
        render(false);
        if (track && window.trackOpsEvent) {
          window.trackOpsEvent('catalog_filter', {
            page_type: entityType,
            program: data.name || '',
            actress: actress ? actress.value.trim() : (entityType === 'actress' ? data.name || '' : ''),
            maker: maker ? maker.value : (entityType === 'maker' ? data.name || '' : ''),
            genre: genre ? genre.value : (entityType === 'genre' ? data.name || '' : ''),
            placement: `sort=${sort ? sort.value : 'new'};sale=${saleOnly && saleOnly.checked ? 1 : 0}`,
            result_count: filtered.length,
          });
        }
      }

      function render(scrollToTop) {
        const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
        if (page > pages) page = pages;
        const start = (page - 1) * PAGE_SIZE;
        grid.innerHTML = filtered.slice(start, start + PAGE_SIZE).map(productCard).join('');
        resultCount.textContent = `${filtered.length.toLocaleString()}作品`;
        pageLabel.textContent = filtered.length ? `${page} / ${pages}` : '0 / 0';
        prev.disabled = page <= 1 || !filtered.length;
        next.disabled = page >= pages || !filtered.length;
        emptyBox.hidden = filtered.length > 0;
        if (scrollToTop) section.scrollIntoView({behavior: 'smooth', block: 'start'});
      }

      prev.addEventListener('click', () => {
        if (page > 1) { page--; render(true); }
      });
      next.addEventListener('click', () => {
        const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
        if (page < pages) { page++; render(true); }
      });
      sort.addEventListener('change', () => applyFilters(true));
      if (actress) actress.addEventListener('input', () => applyFilters(true));
      if (maker) maker.addEventListener('change', () => applyFilters(true));
      if (genre) genre.addEventListener('change', () => applyFilters(true));
      saleOnly.addEventListener('change', () => applyFilters(true));

      const summary = document.querySelector('.entity-summary');
      if (summary && !summary.querySelector('[data-full-count]')) {
        const chip = document.createElement('span');
        chip.className = 'entity-chip';
        chip.dataset.fullCount = '1';
        chip.textContent = `全カタログ ${items.length.toLocaleString()}作品`;
        summary.appendChild(chip);
      }

      applyFilters(false);
    } catch (err) {
      console.warn(`Full ${entityType} catalog load failed`, err);
    }
  }
});