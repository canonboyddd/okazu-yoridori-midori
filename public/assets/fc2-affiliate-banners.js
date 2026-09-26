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
    .fc2-aff-wrap{width:min(860px,92vw)!important;margin:22px auto!important;padding:14px 16px!important;border:1px solid #e6e9f0!important;border-radius:16px!important;background:linear-gradient(135deg,#fff7fb 0%,#f5f7ff 48%,#f2fff8 100%)!important;box-shadow:0 6px 18px rgba(15,23,42,.05)!important;min-height:0!important;height:auto!important;overflow:hidden!important}
    .fc2-aff-label{display:flex!important;align-items:center!important;gap:8px!important;margin:0 0 8px!important;font-size:12px!important;font-weight:800!important;color:#9d174d!important}
    .fc2-aff-label span{display:inline-flex!important;padding:3px 7px!important;border-radius:999px!important;background:#ffe4ee!important;color:#be185d!important}
    .fc2-aff-copy{margin:0 0 10px!important;color:#344054!important;font-size:13px!important;font-weight:600!important;line-height:1.55!important}
    .fc2-aff-banner{display:flex!important;justify-content:center!important;align-items:center!important;width:min(728px,100%)!important;height:auto!important;min-height:0!important;max-height:100px!important;margin:0 auto!important;padding:0!important;text-decoration:none!important;overflow:hidden!important;border-radius:10px!important;background:transparent!important;aspect-ratio:auto!important}
    .fc2-aff-banner img{display:block!important;width:auto!important;max-width:100%!important;height:90px!important;max-height:90px!important;min-height:0!important;margin:0 auto!important;padding:0!important;border:0!important;object-fit:contain!important;aspect-ratio:auto!important}
    .fc2-aff-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:12px!important}
    .fc2-aff-card{display:flex!important;flex-direction:column!important;gap:7px!important;padding:10px!important;background:#fff!important;border:1px solid #e6e9f0!important;border-radius:12px!important;text-decoration:none!important;color:#111827!important;box-shadow:0 3px 10px rgba(15,23,42,.04)!important;min-height:0!important;height:auto!important}
    .fc2-aff-card strong{font-size:13px!important;line-height:1.4!important}
    .fc2-aff-card img{display:block!important;width:auto!important;max-width:100%!important;height:100px!important;max-height:100px!important;margin:auto!important;border:0!important;border-radius:8px!important;object-fit:contain!important;aspect-ratio:auto!important}
    .fc2-aff-fallback{display:flex!important;align-items:center!important;justify-content:center!important;min-height:48px!important;padding:10px 14px!important;border-radius:10px!important;background:linear-gradient(135deg,#fce7f3,#ede9fe,#e0f2fe)!important;color:#1f2937!important;font-size:13px!important;font-weight:800!important;text-align:center!important}
    @media(max-width:800px){.fc2-aff-grid{grid-template-columns:1fr!important}.fc2-aff-wrap{padding:12px!important;margin:16px auto!important}.fc2-aff-copy{font-size:12px!important}.fc2-aff-banner{width:min(320px,100%)!important;max-height:100px!important}.fc2-aff-banner img{height:100px!important;max-height:100px!important}}
  `;
  document.head.appendChild(style);

  function track(name){
    const payload = {affiliate_service:'FC2 Affiliate',affiliate_target:name,page_path:location.pathname};
    if(typeof window.gtag === 'function') window.gtag('event','affiliate_click',payload);
    else if(Array.isArray(window.dataLayer)) window.dataLayer.push({event:'affiliate_click',...payload});
  }

  function fallback(a, p){
    const old = a.querySelector('img');
    if(old) old.remove();
    if(!a.querySelector('.fc2-aff-fallback')){
      const div = document.createElement('div');
      div.className = 'fc2-aff-fallback';
      div.textContent = p.name + ' の公式ページを見る';
      a.appendChild(div);
    }
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
    img.loading = 'eager';
    img.decoding = 'async';
    if(mobile){img.width=320;img.height=100;} else {img.width=728;img.height=90;}
    img.addEventListener('error',()=>fallback(a,p),{once:true});
    a.appendChild(img);
    setTimeout(()=>{
      if(!img.complete || img.naturalWidth === 0 || img.naturalHeight === 0) fallback(a,p);
    },3500);
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
