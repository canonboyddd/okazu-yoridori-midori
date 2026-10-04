(() => {
  const root = document.getElementById('dynamicProduct');
  if (!root) return;

  const id = new URLSearchParams(location.search).get('id') || '';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const safeId = v => String(v || '').replace(/[^0-9A-Za-z_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 120);
  const uniq = values => [...new Set((values || []).filter(Boolean))];

  function ensureStyles() {
    if (document.getElementById('dynamic-product-v2-style')) return;
    const style = document.createElement('style');
    style.id = 'dynamic-product-v2-style';
    style.textContent = '.dp-facts{margin:20px 0;padding:16px;border:1px solid #e5e7eb;border-radius:16px;background:#fff}.dp-facts h2,.dp-related h2{margin:0 0 10px;font-size:1.15rem}.dp-facts p{margin:0;color:#4b5563;line-height:1.75}.dp-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.dp-chip{display:inline-flex;padding:7px 10px;border-radius:999px;background:#f3f4f6;color:#374151;font-size:.82rem;font-weight:750}.dp-related{margin:30px 0}.dp-related-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:12px}.dp-related-head a{font-weight:800}.dp-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.dp-card{display:block;text-decoration:none!important;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;background:#fff}.dp-card img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block}.dp-card-body{padding:10px}.dp-card strong{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;color:#111827;line-height:1.45}.dp-card span,.dp-card small{display:block;margin-top:5px;color:#6b7280}.dp-card b{display:block;margin-top:6px;color:#111827}.dp-sale{display:inline-flex!important;width:auto!important;margin:0 0 5px!important;padding:3px 7px;border-radius:999px;background:#dc2626;color:#fff!important;font-weight:850;font-size:.72rem}.dp-muted{color:#6b7280}@media(max-width:800px){.dp-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.dp-related-head{align-items:start;flex-direction:column}}';
    document.head.appendChild(style);
  }

  async function fetchJson(url, timeoutMs = 6000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url, { cache: 'no-store', signal: ctrl.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  function findInRows(rows) {
    return (rows || []).find(x => safeId(x.contentId) === id) || null;
  }

  function cleanComment(raw) {
    if (!raw) return '';
    const normalized = String(raw).replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, ' ');
    const box = document.createElement('textarea');
    box.innerHTML = normalized;
    return box.value.replace(/\s+/g, ' ').trim();
  }

  function excerptComment(raw, max = 360) {
    const text = cleanComment(raw);
    if (text.length <= max) return text;
    const cut = text.slice(0, max);
    const best = Math.max(...['。', '！', '？', '!', '?'].map(ch => cut.lastIndexOf(ch)));
    return best >= 120 ? cut.slice(0, best + 1) : cut.replace(/[ 、，。！？!?]+$/g, '') + '…';
  }

  function entityLink(type, entity) {
    const eid = safeId(entity?.id);
    const name = String(entity?.name || '').trim();
    if (!eid || !name) return '';
    return `<a href="/ranking/${type}/${encodeURIComponent(eid)}/">${esc(name)}</a>`;
  }

  function priceText(x) {
    return String(x?.price || '').trim() || '公式で確認';
  }

  function factSummary(x) {
    const facts = [];
    const actressNames = (x.actressEntities || []).map(a => String(a.name || '').trim()).filter(Boolean);
    const maker = String((x.makerEntities || [])[0]?.name || x.maker || '').trim();
    const genreNames = (x.genreEntities || []).map(g => String(g.name || '').trim()).filter(Boolean);
    if (actressNames.length) facts.push(`出演者は${actressNames.slice(0, 3).join('、')}`);
    if (maker) facts.push(`メーカーは${maker}`);
    if (genreNames.length) facts.push(`主なジャンルは${genreNames.slice(0, 4).join('、')}`);
    if (x.date) facts.push(`配信日は${String(x.date).slice(0, 10)}`);
    if (Number(x.reviewCount || 0) > 0 && x.reviewAverage) facts.push(`レビューは★${x.reviewAverage}（${Number(x.reviewCount || 0)}件）`);
    if (Number(x.discountRate || 0) > 0) facts.push(`${Number(x.discountRate)}%OFF情報あり`);
    return facts.length ? `${facts.join('。')}。` : 'このページでは、取得できたFANZA作品データを掲載しています。';
  }

  function featureChips(x) {
    const chips = [];
    for (const a of (x.actressEntities || []).slice(0, 3)) if (a?.name) chips.push(a.name);
    for (const g of (x.genreEntities || []).slice(0, 5)) if (g?.name) chips.push(g.name);
    if (x.maker) chips.push(x.maker);
    if (Number(x.discountRate || 0) > 0) chips.push(`${Number(x.discountRate)}%OFF`);
    if (x.reviewAverage && Number(x.reviewCount || 0) > 0) chips.push(`★${x.reviewAverage} / ${Number(x.reviewCount)}件`);
    if (x.date) chips.push(`配信 ${String(x.date).slice(0, 10)}`);
    return uniq(chips).slice(0, 10).map(v => `<span class="dp-chip">${esc(v)}</span>`).join('');
  }

  function relatedCard(item) {
    const rid = safeId(item?.id || item?.contentId);
    if (!rid || rid === id) return '';
    const title = String(item?.title || 'FANZA作品');
    const image = String(item?.image || item?.imageURL || '');
    const maker = String(item?.maker || 'FANZA');
    const discount = Number(item?.discountRate || 0);
    const review = item?.reviewAverage ? `★ ${esc(item.reviewAverage)}${Number(item.reviewCount || 0) ? `（${Number(item.reviewCount)}件）` : ''}` : '';
    const sale = discount > 0 ? `<span class="dp-sale">${discount}%OFF</span>` : '';
    return `<a class="dp-card" href="/products/view/?id=${encodeURIComponent(rid)}"><img src="${esc(image)}" alt="${esc(title)}" loading="lazy" decoding="async"><div class="dp-card-body">${sale}<strong>${esc(title)}</strong><span>${esc(maker)}</span><b>${esc(item?.price || '公式で確認')}</b>${review ? `<small>${review}</small>` : ''}</div></a>`;
  }

  async function loadEntityItems(type, entityId, limit = 8) {
    if (!entityId) return [];
    try {
      const payload = await fetchJson(`/data/${type}-catalog/${encodeURIComponent(entityId)}.json`, 6000);
      const direct = Array.isArray(payload?.items) ? payload.items : [];
      if (direct.length) return direct.filter(x => safeId(x?.id) !== id).slice(0, limit);
      const shards = Array.isArray(payload?.shards) ? payload.shards : [];
      const out = [];
      for (const shard of shards.slice(0, 3)) {
        if (out.length >= limit) break;
        const file = String(shard?.file || '');
        if (!file) continue;
        const data = await fetchJson(file, 6000);
        for (const item of (data?.items || [])) {
          if (safeId(item?.id) === id) continue;
          out.push(item);
          if (out.length >= limit) break;
        }
      }
      return out.slice(0, limit);
    } catch (_) {
      return [];
    }
  }

  function relatedSection(title, moreHref, items) {
    const cards = (items || []).map(relatedCard).filter(Boolean).slice(0, 4).join('');
    if (!cards) return '';
    return `<section class="dp-related"><div class="dp-related-head"><h2>${esc(title)}</h2><a href="${esc(moreHref)}">一覧を見る</a></div><div class="dp-grid">${cards}</div></section>`;
  }

  async function renderRelated(x) {
    const target = document.getElementById('dynamicProductRelated');
    if (!target) return;
    const actress = (x.actressEntities || [])[0] || null;
    const maker = (x.makerEntities || [])[0] || null;
    const genre = (x.genreEntities || [])[0] || null;
    const tasks = [];
    if (actress?.id) tasks.push(loadEntityItems('actress', safeId(actress.id), 6).then(items => relatedSection(`${actress.name}の関連作品`, `/ranking/actress/${encodeURIComponent(safeId(actress.id))}/`, items)));
    if (maker?.id) tasks.push(loadEntityItems('maker', safeId(maker.id), 6).then(items => relatedSection(`${maker.name}の関連作品`, `/ranking/maker/${encodeURIComponent(safeId(maker.id))}/`, items)));
    if (genre?.id) tasks.push(loadEntityItems('genre', safeId(genre.id), 6).then(items => relatedSection(`「${genre.name}」の関連作品`, `/ranking/genre/${encodeURIComponent(safeId(genre.id))}/`, items)));
    if (!tasks.length) return;
    const sections = (await Promise.all(tasks)).filter(Boolean);
    target.innerHTML = sections.join('');
  }

  async function findQuick() {
    try {
      const quick = await fetchJson('/data/fanza-products.json', 4000);
      for (const rows of [quick.ranking, quick.latest, quick.highRated, quick.deals]) {
        const hit = findInRows(rows);
        if (hit) return hit;
      }
    } catch (_) {}
    return null;
  }

  async function findIndexed() {
    try {
      root.textContent = '作品情報を検索中です…';
      const lookup = await fetchJson('/data/catalog-lookup.json?v=20260927-0945', 6000);
      const shardNo = Number(lookup?.items?.[id] || 0);
      if (!shardNo) return null;
      const file = `/data/catalog/catalog-${String(shardNo).padStart(4, '0')}.json`;
      return findInRows(await fetchJson(file, 6000));
    } catch (_) {
      return null;
    }
  }

  async function findFallback() {
    const manifest = await fetchJson('/data/full-catalog-manifest.json', 6000);
    const shards = manifest.shards || [];
    const batchSize = 20;
    for (let i = 0; i < shards.length; i += batchSize) {
      root.textContent = `作品情報を検索中です… ${Math.min(i + batchSize, shards.length)}/${shards.length}`;
      const batch = shards.slice(i, i + batchSize);
      const settled = await Promise.allSettled(batch.map(s => fetchJson(s.file, 5000)));
      for (const result of settled) {
        if (result.status !== 'fulfilled') continue;
        const hit = findInRows(result.value);
        if (hit) return hit;
      }
    }
    return null;
  }

  function render(x) {
    ensureStyles();
    const actresses = (x.actressEntities || []).map(a => entityLink('actress', a)).filter(Boolean).join('、') || '情報なし';
    const genres = (x.genreEntities || []).slice(0, 12).map(g => entityLink('genre', g)).filter(Boolean).join('、') || '情報なし';
    const makerEntities = x.makerEntities || [];
    const makerHtml = makerEntities.length ? makerEntities.map(m => entityLink('maker', m)).filter(Boolean).join('、') : esc(x.maker || '情報なし');
    const series = (x.seriesEntities || []).map(s => esc(s.name || '')).filter(Boolean).join('、');
    const affiliate = esc(x.affiliateURL || '');
    const comment = excerptComment(x.comment || '');
    const commentBlock = comment ? `<section class="fc-description" aria-label="作品紹介"><div class="fc-description-title">作品紹介</div><p class="fc-description-text">${esc(comment)}</p><p class="fc-description-note">FANZA Webサービスの商品説明から、作品選びに必要な範囲を抜粋しています。</p></section>` : '';
    const ctaTop = affiliate ? `<a class="fc-cta fc-cta-top" href="${affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product-top">FANZAでこの作品を見る</a>` : '';
    const ctaBottom = affiliate ? `<a class="fc-cta" href="${affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product-bottom">FANZA公式で確認</a>` : '';
    const discount = Number(x.discountRate || 0) > 0 ? ` <span>${Number(x.discountRate)}%OFF</span>` : '';
    const seriesRow = series ? `<dt>シリーズ</dt><dd>${series}</dd>` : '';
    const facts = `<section class="dp-facts" aria-label="作品データの要点"><h2>作品データの要点</h2><p>${esc(factSummary(x))}</p><div class="dp-chips">${featureChips(x)}</div></section>`;

    document.title = `${String(x.title || '作品情報')}｜作品情報｜オカズはよりどりみどり`;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.setAttribute('content', `${String(x.title || 'FANZA作品')}の価格・出演者・メーカー・ジャンル・配信日・レビュー情報を確認できます。`);

    root.innerHTML = `<div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/products/">作品一覧</a> › ${esc(x.title)}</div><div class="fc-detail"><div><img class="fc-cover" src="${esc(x.imageURL)}" alt="${esc(x.title)}"></div><div><h1>${esc(x.title)}</h1><div class="fc-price">${esc(priceText(x))}${discount}</div>${ctaTop}<dl><dt>出演者</dt><dd>${actresses}</dd><dt>メーカー</dt><dd>${makerHtml}</dd><dt>ジャンル</dt><dd>${genres}</dd>${seriesRow}<dt>レビュー</dt><dd>★ ${esc(x.reviewAverage || '-')}（${Number(x.reviewCount || 0)}件）</dd><dt>配信日</dt><dd>${esc(x.date || '-')}</dd></dl>${facts}${commentBlock}${ctaBottom}</div></div><div id="dynamicProductRelated"><p class="dp-muted">関連作品を読み込み中です…</p></div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p>`;
    renderRelated(x).catch(() => {
      const target = document.getElementById('dynamicProductRelated');
      if (target) target.innerHTML = '';
    });
  }

  async function main() {
    if (!id) {
      root.innerHTML = '<h1>作品IDが見つかりませんでした</h1><p><a href="/products/">作品一覧へ戻る</a></p>';
      return;
    }
    root.textContent = '作品情報を読み込み中です…';
    const indexed = await findIndexed();
    if (indexed) return render(indexed);
    const quick = await findQuick();
    if (quick) return render(quick);
    const fallback = await findFallback();
    if (fallback) return render(fallback);
    root.innerHTML = '<h1>作品が見つかりませんでした</h1><p><a href="/products/">作品一覧へ戻る</a> / <a href="/search/">検索する</a></p>';
  }

  main().catch(() => {
    root.innerHTML = '<h1>作品情報を読み込めませんでした</h1><p>通信状態を確認して、もう一度お試しください。</p><p><button onclick="location.reload()">再読み込み</button> <a href="/products/">作品一覧へ戻る</a></p>';
  });
})();
