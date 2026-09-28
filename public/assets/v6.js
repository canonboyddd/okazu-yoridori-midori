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

  const genreMatch = location.pathname.match(/^\/ranking\/genre\/([^/]+)\/?$/);
  if (genreMatch) loadFullGenreCatalog(genreMatch[1]);

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[ch]);
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
    return `<a class="entity-product-card" href="/products/view/?id=${encodeURIComponent(item.id || '')}">
      <div class="entity-product-image">${badge}${image}</div>
      <div class="entity-product-body">
        <div class="entity-title">${esc(item.title || 'FANZA作品')}</div>
        ${sub ? `<div class="entity-sub">${esc(sub)}</div>` : ''}
        <div class="entity-meta"><span class="entity-price">${esc(price)}</span>${review ? `<span>${review}</span>` : ''}</div>
      </div>
    </a>`;
  }

  async function loadFullGenreCatalog(genreId) {
    const existingGrid = document.querySelector('.entity-product-grid');
    if (!existingGrid || document.querySelector('[data-full-genre-catalog="1"]')) return;

    try {
      const res = await fetch(`/data/genre-catalog/${encodeURIComponent(genreId)}.json?v=20260928-1317`, {cache: 'no-cache'});
      if (!res.ok) return;
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) return;

      const PAGE_SIZE = 60;
      let page = 1;
      const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));

      const section = document.createElement('section');
      section.dataset.fullGenreCatalog = '1';
      section.className = 'genre-full-catalog';
      section.innerHTML = `
        <div class="genre-full-head">
          <div><span class="update-badge">全カタログ集計</span><h2>${esc(data.name || 'このジャンル')}の全作品</h2></div>
          <strong>${items.length.toLocaleString()}作品</strong>
        </div>
        <p class="genre-full-copy">約5万作品の取得済みFANZAカタログ全体から、このジャンルに該当する作品を新着順で表示しています。</p>
        <div class="entity-product-grid genre-full-grid"></div>
        <nav class="genre-pagination" aria-label="ジャンル作品ページ送り">
          <button type="button" data-prev>← 前へ</button>
          <span data-page></span>
          <button type="button" data-next>次へ →</button>
        </nav>`;

      existingGrid.insertAdjacentElement('afterend', section);
      const grid = section.querySelector('.genre-full-grid');
      const pageLabel = section.querySelector('[data-page]');
      const prev = section.querySelector('[data-prev]');
      const next = section.querySelector('[data-next]');

      const style = document.createElement('style');
      style.textContent = `
        .genre-full-catalog{margin-top:38px;padding-top:30px;border-top:1px solid #e5e7eb}
        .genre-full-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-bottom:8px}
        .genre-full-head h2{margin:7px 0 0}
        .genre-full-head>strong{font-size:1.15rem;white-space:nowrap}
        .genre-full-copy{margin:0 0 20px;color:#64748b;line-height:1.7}
        .genre-pagination{display:flex;align-items:center;justify-content:center;gap:14px;margin:26px 0 8px}
        .genre-pagination button{border:1px solid #d7dce4;border-radius:999px;background:#fff;padding:10px 16px;font-weight:800;cursor:pointer}
        .genre-pagination button:disabled{opacity:.35;cursor:not-allowed}
        .genre-pagination span{min-width:110px;text-align:center;font-weight:800;color:#334155}
        @media(max-width:620px){.genre-full-head{align-items:flex-start;flex-direction:column}.genre-pagination{gap:8px}.genre-pagination button{padding:9px 12px}}
      `;
      document.head.appendChild(style);

      function render(scrollToTop) {
        const start = (page - 1) * PAGE_SIZE;
        grid.innerHTML = items.slice(start, start + PAGE_SIZE).map(productCard).join('');
        pageLabel.textContent = `${page} / ${pages}`;
        prev.disabled = page <= 1;
        next.disabled = page >= pages;
        if (scrollToTop) section.scrollIntoView({behavior: 'smooth', block: 'start'});
      }

      prev.addEventListener('click', () => {
        if (page > 1) { page--; render(true); }
      });
      next.addEventListener('click', () => {
        if (page < pages) { page++; render(true); }
      });

      const summary = document.querySelector('.entity-summary');
      if (summary && !summary.querySelector('[data-full-count]')) {
        const chip = document.createElement('span');
        chip.className = 'entity-chip';
        chip.dataset.fullCount = '1';
        chip.textContent = `全カタログ ${items.length.toLocaleString()}作品`;
        summary.appendChild(chip);
      }

      render(false);
    } catch (err) {
      console.warn('Full genre catalog load failed', err);
    }
  }
});
