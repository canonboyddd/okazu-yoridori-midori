(() => {
  const clickBase = 'https://cnt.affiliate.fc2.com/cgi-bin/click.cgi?aff_userid=356511&aff_siteid=348757&aff_shopid=';
  const bannerBase = 'https://cnt.affiliate.fc2.com/cgi-bin/banner.cgi?aff_siteid=348757&uid=356511&bid=';

  const programs = {
    sodSale: {name:'SOD select ポイント還元', shop:'419', desktop:'21050', mobile:'21053'},
    sodSub: {name:'SOD select 見放題', shop:'418', desktop:'21043', mobile:'21047'},
    fc2Sub: {name:'FC2動画 見放題', shop:'310', desktop:'20766', mobile:'20754'},
    favSub: {name:'FAV-tube 見放題', shop:'411', desktop:'20978', mobile:'20979'},
    nutsSub: {name:'NutsVideo 見放題', shop:'410', desktop:'20974', mobile:'20973'},
    afternoonSub: {name:'AfternoonX 見放題', shop:'413', desktop:'21017', mobile:'21021'},
    momoSub: {name:'桃ポルノ 見放題', shop:'414', desktop:'21024', mobile:'21023'},
    fc2Market: {name:'FC2コンテンツマーケット', shop:'158', desktop:'20781', mobile:'20777'},
    fc2Video: {name:'FC2動画', shop:'146', desktop:'20744', mobile:'20748'},
    fppv: {name:'FPPV.net', shop:'412', desktop:'20982', mobile:'20981'}
  };

  const style = document.createElement('style');
  style.textContent = `
    .fc2-aff-wrap{width:min(1100px,92vw);margin:28px auto;padding:18px;border:1px solid #e6e9f0;border-radius:18px;background:linear-gradient(135deg,#fff7fb 0%,#f5f7ff 48%,#f2fff8 100%);box-shadow:0 8px 24px rgba(15,23,42,.06)}
    .fc2-aff-label{display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:13px;font-weight:800;color:#9d174d}
    .fc2-aff-label span{display:inline-flex;padding:4px 8px;border-radius:999px;background:#ffe4ee;color:#be185d}
    .fc2-aff-copy{margin:0 0 14px;color:#344054;font-size:14px;font-weight:600;line-height:1.7}
    .fc2-aff-banner{display:flex;justify-content:center;align-items:center;text-decoration:none;overflow:hidden;border-radius:12px;background:#fff}
    .fc2-aff-banner img{display:block;max-width:100%;height:auto;border:0}
    .fc2-aff-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
    .fc2-aff-card{display:flex;flex-direction:column;gap:8px;padding:12px;background:#fff;border:1px solid #e6e9f0;border-radius:14px;text-decoration:none;color:#111827;box-shadow:0 4px 12px rgba(15,23,42,.04)}
    .fc2-aff-card strong{font-size:14px;line-height:1.5}
    .fc2-aff-card img{display:block;width:100%;height:auto;max-width:320px;margin:auto;border:0;border-radius:8px}
    @media(max-width:800px){.fc2-aff-grid{grid-template-columns:1fr}.fc2-aff-wrap{padding:14px}.fc2-aff-copy{font-size:13px}}
  `;
  document.head.appendChild(style);

  function track(name){
    const payload = {affiliate_service:'FC2 Affiliate',affiliate_target:name,page_path:location.pathname};
    if(typeof window.gtag === 'function') window.gtag('event','affiliate_click',payload);
    else if(Array.isArray(window.dataLayer)) window.dataLayer.push({event:'affiliate_click',...payload});
  }

  function makeBanner(p, compact=false){
    const mobile = compact || window.innerWidth <= 760;
    const bid = mobile ? p.mobile : p.desktop;
    const a = document.createElement('a');
    a.className = compact ? 'fc2-aff-card' : 'fc2-aff-banner';
    a.href = clickBase + encodeURIComponent(p.shop);
    a.target = '_blank';
    a.rel = 'sponsored nofollow noopener noreferrer';
    a.dataset.affiliateTarget = 'fc2-' + p.shop;
    a.addEventListener('click',()=>track(p.name));
    if(compact){
      const strong = document.createElement('strong');
      strong.textContent = p.name;
      a.appendChild(strong);
    }
    const img = document.createElement('img');
    img.src = bannerBase + encodeURIComponent(bid);
    img.alt = p.name + ' PR広告';
    img.loading = 'lazy';
    if(mobile){img.width=320;img.height=100;} else {img.width=728;img.height=90;}
    a.appendChild(img);
    return a;
  }

  function box(copy){
    const wrap = document.createElement('aside');
    wrap.className = 'fc2-aff-wrap';
    wrap.dataset.fc2Affiliate = '1';
    const label = document.createElement('div');
    label.className = 'fc2-aff-label';
    label.innerHTML = '<span>PR / 広告</span> FC2アフィリエイト提携広告';
    const p = document.createElement('p');
    p.className = 'fc2-aff-copy';
    p.textContent = copy;
    wrap.append(label,p);
    return wrap;
  }

  function insertAfterHero(node){
    const hero = document.querySelector('.hub-hero,.hero');
    if(hero){hero.insertAdjacentElement('afterend',node);return;}
    const main = document.querySelector('main');
    if(main){main.insertAdjacentElement('afterbegin',node);return;}
    document.body.appendChild(node);
  }

  const path = location.pathname;
  if(document.querySelector('[data-fc2-affiliate="1"]')) return;

  if(path.startsWith('/subscription')){
    const wrap = box('見放題サービスを比較するときは、料金・対象作品・更新条件を各公式ページで確認してください。');
    const grid = document.createElement('div');
    grid.className = 'fc2-aff-grid';
    [programs.sodSub,programs.fc2Sub,programs.favSub].forEach(p=>grid.appendChild(makeBanner(p,true)));
    wrap.appendChild(grid);
    insertAfterHero(wrap);
    return;
  }

  if(path.startsWith('/sale')){
    const wrap = box('セール・キャンペーンは条件や期間が変更される場合があります。最新情報はリンク先で確認してください。');
    wrap.appendChild(makeBanner(programs.sodSale));
    insertAfterHero(wrap);
    return;
  }

  const general = [programs.sodSale,programs.fc2Market,programs.fc2Video,programs.fppv];
  const seed = Array.from(path).reduce((n,ch)=>n+ch.charCodeAt(0),0);
  const selected = general[seed % general.length];
  const wrap = box('関連サービスの公式ページを確認できます。リンク先の料金・利用条件を確認してから利用してください。');
  wrap.appendChild(makeBanner(selected));

  if(path === '/' || path.startsWith('/ranking') || path.startsWith('/products') || path.startsWith('/reviews') || path.startsWith('/discover') || path.startsWith('/articles/')){
    insertAfterHero(wrap);
  }
})();
