(() => {
  const input = document.getElementById('siteSearch');
  const results = document.getElementById('siteSearchResults');
  const count = document.getElementById('siteSearchCount');
  if (!input || !results || !count) return;
  let rows = [];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function renderCard(row){
    if(row.type === 'actress'){
      const image = row.image ? `<div class="fc-img"><img src="${esc(row.image)}" alt="${esc(row.title)}" loading="lazy"></div>` : '';
      return `<a class="fc-card" href="/ranking/actress/${encodeURIComponent(row.id)}/">${image}<div class="fc-body"><strong>${esc(row.title)}</strong><span>${esc(row.ruby || '女優')}</span></div></a>`;
    }
    return `<a class="fc-card" href="/products/view/?id=${encodeURIComponent(row.id)}"><div class="fc-img"><img src="${esc(row.image)}" alt="${esc(row.title)}" loading="lazy"></div><div class="fc-body"><strong>${esc(row.title)}</strong><span>${esc(row.maker || '')}</span><b>${esc(row.price || '')}</b></div></a>`;
  }
  function render(){
    const q = input.value.trim().toLowerCase();
    if(!q){results.innerHTML=''; count.textContent=`${rows.length.toLocaleString('ja-JP')}件検索対象`; return;}
    const matched = rows.filter(row => {
      const hay = [row.title,row.ruby,row.maker,...(row.actresses||[]),...(row.genres||[])].join(' ').toLowerCase();
      return hay.includes(q);
    });
    results.innerHTML = matched.slice(0,200).map(renderCard).join('') || '<p>該当する結果がありません。</p>';
    count.textContent = `${matched.length.toLocaleString('ja-JP')}件該当${matched.length>200?'（先頭200件表示）':''}`;
  }
  fetch('/data/site-search-index.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{rows=Array.isArray(data)?data:[];count.textContent=`${rows.length.toLocaleString('ja-JP')}件検索対象`;input.addEventListener('input',render)}).catch(()=>{count.textContent='検索データを読み込めませんでした'});
})();