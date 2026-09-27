(() => {
  const root = document.getElementById('dynamicProduct');
  if (!root) return;

  const id = new URLSearchParams(location.search).get('id') || '';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const safeId = v => String(v || '').replace(/[^0-9A-Za-z_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 120);

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
    const normalized = String(raw)
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, ' ');
    const box = document.createElement('textarea');
    box.innerHTML = normalized;
    return box.value.replace(/\s+/g, ' ').trim();
  }

  function excerptComment(raw, max = 360) {
    const text = cleanComment(raw);
    if (text.length <= max) return text;
    const cut = text.slice(0, max);
    const ends = ['。', '！', '？', '!', '?'].map(ch => cut.lastIndexOf(ch));
    const best = Math.max(...ends);
    return best >= 120 ? cut.slice(0, best + 1) : cut.replace(/[ 、，。！？!?]+$/g, '') + '…';
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
    const actresses = (x.actressEntities || []).map(a => `<a href="/ranking/actress/${encodeURIComponent(a.id)}/">${esc(a.name)}</a>`).join('、') || '情報なし';
    const genres = (x.genreEntities || []).slice(0, 12).map(g => `<a href="/ranking/genre/${encodeURIComponent(g.id)}/">${esc(g.name)}</a>`).join('、') || '情報なし';
    const affiliate = esc(x.affiliateURL || '');
    const comment = excerptComment(x.comment || '');
    const commentBlock = comment ? `<section class="fc-description" aria-label="作品紹介"><div class="fc-description-title">作品紹介</div><p class="fc-description-text">${esc(comment)}</p><p class="fc-description-note">FANZA Webサービスの商品説明から、作品選びに必要な範囲を抜粋しています。</p></section>` : '';
    const ctaTop = affiliate ? `<a class="fc-cta fc-cta-top" href="${affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product">FANZAでこの作品を見る</a>` : '';
    const ctaBottom = affiliate ? `<a class="fc-cta" href="${affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate-target="product">FANZA公式で確認</a>` : '';
    root.innerHTML = `<div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/products/">作品一覧</a> › ${esc(x.title)}</div><div class="fc-detail"><div><img class="fc-cover" src="${esc(x.imageURL)}" alt="${esc(x.title)}"></div><div><h1>${esc(x.title)}</h1><div class="fc-price">${esc(x.price || '公式で確認')}</div>${ctaTop}<dl><dt>出演者</dt><dd>${actresses}</dd><dt>メーカー</dt><dd>${esc(x.maker || '情報なし')}</dd><dt>ジャンル</dt><dd>${genres}</dd><dt>レビュー</dt><dd>★ ${esc(x.reviewAverage || '-')}（${Number(x.reviewCount || 0)}件）</dd><dt>配信日</dt><dd>${esc(x.date || '-')}</dd></dl>${commentBlock}${ctaBottom}</div></div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p>`;
  }

  async function main() {
    if (!id) {
      root.innerHTML = '<h1>作品IDが見つかりませんでした</h1><p><a href="/products/">作品一覧へ戻る</a></p>';
      return;
    }
    root.textContent = '作品情報を読み込み中です…';

    // Prefer the full-catalog indexed record because it carries the product comment.
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
