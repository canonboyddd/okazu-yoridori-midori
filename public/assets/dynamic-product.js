(() => {
  const root = document.getElementById('dynamicProduct');
  if(!root) return;
  const id = new URLSearchParams(location.search).get('id') || '';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  async function find(){
    const manifest = await fetch('/data/full-catalog-manifest.json',{cache:'no-store'}).then(r=>r.json());
    for(const shard of manifest.shards || []){
      const rows = await fetch(shard.file,{cache:'no-store'}).then(r=>r.json());
      const hit = rows.find(x => String(x.contentId || '').replace(/[^0-9A-Za-z_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,120) === id);
      if(hit) return hit;
    }
    return null;
  }
  find().then(x=>{
    if(!x){root.innerHTML='<h1>作品が見つかりませんでした</h1>';return;}
    const actresses=(x.actressEntities||[]).map(a=>`<a href="/ranking/actress/${encodeURIComponent(a.id)}/">${esc(a.name)}</a>`).join('、')||'情報なし';
    const genres=(x.genreEntities||[]).slice(0,12).map(g=>`<a href="/ranking/genre/${encodeURIComponent(g.id)}/">${esc(g.name)}</a>`).join('、')||'情報なし';
    root.innerHTML=`<div class="fc-breadcrumb"><a href="/">トップ</a> › <a href="/products/">作品一覧</a> › ${esc(x.title)}</div><div class="fc-detail"><div><img class="fc-cover" src="${esc(x.imageURL)}" alt="${esc(x.title)}"></div><div><h1>${esc(x.title)}</h1><div class="fc-price">${esc(x.price||'公式で確認')}</div><dl><dt>出演者</dt><dd>${actresses}</dd><dt>メーカー</dt><dd>${esc(x.maker||'情報なし')}</dd><dt>ジャンル</dt><dd>${genres}</dd><dt>レビュー</dt><dd>★ ${esc(x.reviewAverage||'-')}（${Number(x.reviewCount||0)}件）</dd><dt>配信日</dt><dd>${esc(x.date||'-')}</dd></dl><a class="fc-cta" href="${esc(x.affiliateURL)}" target="_blank" rel="sponsored nofollow noopener noreferrer">FANZA公式で確認</a></div></div><p class="fc-pr">PR：当ページにはアフィリエイト広告を含みます。</p>`;
  }).catch(()=>{root.innerHTML='<h1>作品情報を読み込めませんでした</h1>'});
})();