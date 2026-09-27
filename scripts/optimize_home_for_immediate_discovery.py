from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path("public")
HOME = ROOT / "index.html"
PRODUCTS = ROOT / "data" / "fanza-products.json"
POPULAR_ACTRESSES = ROOT / "data" / "fanza-actress-popularity.json"
ENTITY_RANKINGS = ROOT / "data" / "fanza-entity-rankings.json"
CSS = "/assets/instant-discovery-v1.css?v=20260927-0105"

CHOOSER_CSS = r'''
<style id="instantChooserStyle">
.instant-chooser{width:min(1120px,94vw);margin:18px auto 34px;padding:18px;border:2px solid #f1c3d4;border-radius:22px;background:linear-gradient(135deg,#fff5f8,#f7f5ff 55%,#effbff);box-shadow:0 12px 30px rgba(15,23,42,.10)}
.instant-chooser-head{display:flex;align-items:end;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:14px}.instant-chooser-head h2{margin:0;font-size:clamp(1.35rem,5vw,2rem);font-weight:950;color:#111827}.instant-chooser-head p{margin:4px 0 0;color:#374151;font-weight:700}.instant-chooser-time{display:inline-flex;padding:7px 11px;border-radius:999px;background:#111827;color:#fff!important;font-size:.78rem;font-weight:900}
.instant-question{margin:14px 0}.instant-question b{display:block;margin-bottom:8px;font-size:.92rem;color:#111827}.instant-choice-row{display:flex;gap:8px;flex-wrap:wrap}.instant-choice{appearance:none;border:1px solid #cfd8e5!important;background:#fff!important;color:#1f2937!important;border-radius:999px!important;padding:9px 13px!important;font-size:.86rem!important;font-weight:850!important;box-shadow:0 2px 7px rgba(15,23,42,.05)}.instant-choice[aria-pressed="true"]{background:linear-gradient(135deg,#e11d74,#7c3aed)!important;color:#fff!important;border-color:transparent!important}
.instant-decide{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:16px}.instant-decide button{min-height:48px;padding:0 20px;border-radius:14px;background:linear-gradient(135deg,#e11d74,#7c3aed);color:#fff;font-weight:950;font-size:.98rem}.instant-decide span{font-size:.8rem;color:#475569;font-weight:700}
.instant-picks{margin-top:18px;display:none}.instant-picks.show{display:block}.instant-picks-head{display:flex;justify-content:space-between;align-items:end;gap:10px;flex-wrap:wrap;margin-bottom:10px}.instant-picks-head h3{margin:0;font-size:1.25rem}.instant-picks-head button{background:#fff!important;color:#334155!important;border:1px solid #cbd5e1!important;padding:7px 11px!important}.instant-pick-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.instant-pick{display:flex;flex-direction:column;overflow:hidden;border:1px solid #dbe3ed;border-radius:15px;background:#fff;box-shadow:0 5px 14px rgba(15,23,42,.07)}.instant-pick-img{position:relative;aspect-ratio:4/3;background:#f8fafc;overflow:hidden}.instant-pick-img img{width:100%;height:100%;object-fit:contain}.instant-pick-num{position:absolute;left:7px;top:7px;display:flex;min-width:30px;height:30px;padding:0 7px;border-radius:999px;align-items:center;justify-content:center;background:#111827;color:#fff!important;font-size:.72rem;font-weight:950}.instant-pick-body{display:flex;flex-direction:column;gap:7px;padding:10px;flex:1}.instant-pick-body strong{font-size:.83rem;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.instant-pick-meta{display:flex;justify-content:space-between;gap:6px;align-items:center;font-size:.75rem}.instant-pick-meta b{color:#b42318!important}.instant-pick-links{display:grid;grid-template-columns:1fr;gap:6px;margin-top:auto}.instant-pick-detail,.instant-pick-buy{display:flex;align-items:center;justify-content:center;min-height:38px;border-radius:10px;text-decoration:none!important;font-size:.76rem!important;font-weight:900!important}.instant-pick-detail{background:#f1f5f9;color:#334155!important}.instant-pick-buy{background:linear-gradient(135deg,#e11d48,#f97316);color:#fff!important}.instant-pick-note{margin:10px 0 0;font-size:.76rem;color:#64748b!important;font-weight:700!important}
@media(max-width:900px){.instant-pick-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:620px){.instant-chooser{padding:14px;margin-top:12px}.instant-choice-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.instant-choice{width:100%;padding:9px 7px!important;font-size:.79rem!important}.instant-decide button{width:100%}.instant-pick-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.instant-pick-body{padding:8px}.instant-pick-body strong{font-size:.79rem}.instant-pick-buy,.instant-pick-detail{font-size:.72rem!important}}
</style>
'''

CHOOSER_JS = r'''
<script id="instantChooserScript">
(() => {
  const root = document.getElementById('instantChooser');
  if (!root) return;
  const state = { priority: 'popular', taste: 'any', count: 5 };
  const pools = {ranking:[],latest:[],highRated:[],deals:[]};
  let loaded = false;

  const esc = v => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const safeId = v => String(v || '').replace(/[^0-9A-Za-z_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,120);
  const price = v => { const d=String(v||'').replace(/\D/g,''); return d ? '¥'+Number(d).toLocaleString('ja-JP') : '価格確認'; };

  const tasteWords = {
    any: [],
    vr: ['VR','8KVR','VR専用'],
    amateur: ['素人','ナンパ','一般人'],
    married: ['人妻','主婦','熟女'],
    cosplay: ['コスプレ','制服','衣装'],
    mature: ['熟女','美熟女'],
    bust: ['巨乳','爆乳']
  };

  root.querySelectorAll('[data-choice]').forEach(btn => btn.addEventListener('click', () => {
    const group = btn.dataset.group;
    root.querySelectorAll(`[data-group="${group}"]`).forEach(x => x.setAttribute('aria-pressed','false'));
    btn.setAttribute('aria-pressed','true');
    state[group] = group === 'count' ? Number(btn.dataset.choice) : btn.dataset.choice;
  }));

  async function load(){
    if (loaded) return;
    const res = await fetch('/data/fanza-products.json?v=chooser-20260927-1',{cache:'no-store'});
    if(!res.ok) throw new Error('products');
    const data = await res.json();
    for(const k of Object.keys(pools)) pools[k] = Array.isArray(data[k]) ? data[k] : [];
    loaded = true;
  }

  function merged(){
    const seen = new Set();
    const out = [];
    const order = state.priority === 'deal' ? ['deals','ranking','highRated','latest'] : state.priority === 'rated' ? ['highRated','ranking','deals','latest'] : state.priority === 'new' ? ['latest','ranking','highRated','deals'] : ['ranking','highRated','deals','latest'];
    order.forEach((poolName,poolIndex) => pools[poolName].forEach((x,index) => {
      const id = safeId(x.contentId || x.affiliateURL);
      if(!id || seen.has(id) || !x.imageURL) return;
      seen.add(id);
      out.push({...x,_pool:poolName,_poolIndex:poolIndex,_index:index});
    }));
    return out;
  }

  function tasteMatch(x){
    const words = tasteWords[state.taste] || [];
    if(!words.length) return true;
    const hay = [...(x.genres||[]),...(x.actresses||[]),x.title||'',x.maker||'',x.series||''].join(' ').toLowerCase();
    return words.some(w => hay.includes(w.toLowerCase()));
  }

  function score(x){
    let s = 100 - x._poolIndex*14 - Math.min(40,x._index||0);
    if(state.priority === 'deal') s += Number(x.discountRate||0)*2;
    if(state.priority === 'rated') s += Number(x.reviewAverage||0)*18 + Math.min(25,Number(x.reviewCount||0)/2);
    if(state.priority === 'new') s += x._pool === 'latest' ? 55 : 0;
    if(state.priority === 'popular') s += x._pool === 'ranking' ? 55 : 0;
    if(state.taste !== 'any' && tasteMatch(x)) s += 100;
    return s;
  }

  function pick(){
    let rows = merged();
    if(state.taste !== 'any') {
      const matched = rows.filter(tasteMatch);
      if(matched.length >= 3) rows = matched;
    }
    return rows.sort((a,b)=>score(b)-score(a)).slice(0,state.count);
  }

  function track(target){
    const payload={affiliate_service:'DMM/FANZA',affiliate_target:target,page_path:location.pathname};
    if(typeof window.gtag==='function') window.gtag('event','affiliate_click',payload);
    else if(Array.isArray(window.dataLayer)) window.dataLayer.push({event:'affiliate_click',...payload});
  }

  function render(rows){
    const grid = document.getElementById('instantPickGrid');
    const area = document.getElementById('instantPicks');
    grid.innerHTML = rows.map((x,i) => {
      const id = safeId(x.contentId);
      const affiliate = esc(x.affiliateURL || '#');
      const discount = Number(x.discountRate||0);
      return `<article class="instant-pick"><div class="instant-pick-img"><span class="instant-pick-num">${i+1}</span><img src="${esc(x.imageURL)}" alt="${esc(x.title)}" loading="lazy"></div><div class="instant-pick-body"><strong>${esc(x.title)}</strong><div class="instant-pick-meta"><b>${esc(price(x.price))}</b><span>${discount?discount+'%OFF':''}</span></div><div class="instant-pick-links"><a class="instant-pick-detail" href="/products/view/?id=${encodeURIComponent(id)}">詳細を見る</a><a class="instant-pick-buy" href="${affiliate}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-direct-fanza="${i+1}">FANZAで見る</a></div></div></article>`;
    }).join('');
    grid.querySelectorAll('[data-direct-fanza]').forEach(a=>a.addEventListener('click',()=>track('home-chooser-'+a.dataset.directFanza)));
    area.classList.add('show');
    area.scrollIntoView({behavior:'smooth',block:'nearest'});
  }

  async function decide(){
    const button = document.getElementById('instantDecide');
    button.disabled = true;
    button.textContent = 'おすすめを選んでいます…';
    try{
      await load();
      const rows = pick();
      if(!rows.length) throw new Error('empty');
      render(rows);
      button.textContent = 'おすすめを選び直す';
    }catch(_){
      button.textContent = '読み込みに失敗しました。もう一度';
    }finally{
      button.disabled = false;
    }
  }

  document.getElementById('instantDecide').addEventListener('click',decide);
  document.getElementById('instantShuffle').addEventListener('click',decide);
})();
</script>
'''


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_id(value: str) -> str:
    s = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-")
    return s[:120] or "item"


def yen(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"¥{int(digits):,}" if digits else "価格を確認"


def product_href(item: dict) -> str:
    cid = safe_id(str(item.get("contentId") or ""))
    static = ROOT / "products" / cid / "index.html"
    return f"/products/{cid}/" if static.exists() else f"/products/view/?id={html.escape(cid, quote=True)}"


def product_card(item: dict, rank: int | None = None) -> str:
    title = html.escape(str(item.get("title") or "FANZA作品"))
    image = html.escape(str(item.get("imageURL") or ""), quote=True)
    href = product_href(item)
    discount = int(item.get("discountRate") or 0)
    actresses = [str(x) for x in (item.get("actresses") or [])[:2] if x]
    maker = str(item.get("maker") or "")
    sub = " / ".join(actresses) or maker
    review = str(item.get("reviewAverage") or "").strip()
    badges = []
    if rank:
        badges.append(f'<span class="instant-rank">{rank}位</span>')
    if discount > 0:
        badges.append(f'<span class="instant-discount">{discount}%OFF</span>')
    badge_html = "".join(badges)
    img_html = f'<img src="{image}" alt="{title}" loading="lazy" decoding="async">' if image else '<div class="instant-noimage">画像なし</div>'
    review_html = f'<span class="instant-review">★ {html.escape(review)}</span>' if review else ""
    return f'''<a class="instant-product-card" href="{href}">
<div class="instant-product-image">{badge_html}{img_html}</div>
<div class="instant-product-body"><strong>{title}</strong>{f'<span class="instant-sub">{html.escape(sub)}</span>' if sub else ''}<div class="instant-product-meta"><b>{html.escape(yen(item.get("price")))}</b>{review_html}</div></div>
</a>'''


def actress_card(row: dict) -> str:
    aid = html.escape(str(row.get("id") or ""), quote=True)
    name = html.escape(str(row.get("name") or ""))
    image = html.escape(str(row.get("imageURL") or ""), quote=True)
    rank = int(row.get("popularityRank") or 0)
    img_html = f'<img src="{image}" alt="{name}" loading="lazy" decoding="async">' if image else '<div class="instant-noimage">画像なし</div>'
    return f'''<a class="instant-actress-card" href="/ranking/actress/{aid}/"><div class="instant-actress-photo">{img_html}<span>{rank}位</span></div><strong>{name}</strong></a>'''


def genre_card(row: dict) -> str:
    gid = html.escape(str(row.get("id") or ""), quote=True)
    name = html.escape(str(row.get("name") or ""))
    count = int(row.get("itemCount") or 0)
    return f'<a class="instant-genre" href="/ranking/genre/{gid}/"><strong>{name}</strong><span>人気 {count}作品</span></a>'


def choose_rows(data: list[dict], limit: int, image_required: bool = True) -> list[dict]:
    out = []
    seen = set()
    for row in data:
        key = str(row.get("contentId") or row.get("id") or row.get("name") or "")
        if not key or key in seen:
            continue
        if image_required and not row.get("imageURL"):
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def chooser_html() -> str:
    return '''<section class="instant-chooser" id="instantChooser">
<div class="instant-chooser-head"><div><h2>30秒で今日見る作品を決める</h2><p>3つ選ぶだけで、候補を5〜10本まで絞ります。</p></div><span class="instant-chooser-time">迷う時間を短縮</span></div>
<div class="instant-question"><b>1. 何を優先する？</b><div class="instant-choice-row">
<button class="instant-choice" data-choice="popular" data-group="priority" aria-pressed="true">人気</button><button class="instant-choice" data-choice="rated" data-group="priority" aria-pressed="false">高評価</button><button class="instant-choice" data-choice="new" data-group="priority" aria-pressed="false">新作</button><button class="instant-choice" data-choice="deal" data-group="priority" aria-pressed="false">安さ・セール</button>
</div></div>
<div class="instant-question"><b>2. 今の好みは？</b><div class="instant-choice-row">
<button class="instant-choice" data-choice="any" data-group="taste" aria-pressed="true">おまかせ</button><button class="instant-choice" data-choice="vr" data-group="taste" aria-pressed="false">VR</button><button class="instant-choice" data-choice="amateur" data-group="taste" aria-pressed="false">素人系</button><button class="instant-choice" data-choice="married" data-group="taste" aria-pressed="false">人妻・熟女</button><button class="instant-choice" data-choice="cosplay" data-group="taste" aria-pressed="false">コスプレ</button><button class="instant-choice" data-choice="bust" data-group="taste" aria-pressed="false">巨乳</button>
</div></div>
<div class="instant-question"><b>3. 候補は何本まで？</b><div class="instant-choice-row"><button class="instant-choice" data-choice="5" data-group="count" aria-pressed="true">5本に絞る</button><button class="instant-choice" data-choice="10" data-group="count" aria-pressed="false">10本見る</button></div></div>
<div class="instant-decide"><button id="instantDecide" type="button">おすすめを出す</button><span>結果から直接FANZA公式へ移動できます。</span></div>
<div class="instant-picks" id="instantPicks"><div class="instant-picks-head"><div><h3>あなた向け候補</h3><span>迷ったら上から見ればOKです。</span></div><button id="instantShuffle" type="button">選び直す</button></div><div class="instant-pick-grid" id="instantPickGrid"></div><p class="instant-pick-note">PR：FANZAへのリンクにはアフィリエイト広告を含みます。価格・販売状況は公式ページでご確認ください。</p></div>
</section>'''


def build_main() -> str:
    product_data = load_json(PRODUCTS)
    actress_data = load_json(POPULAR_ACTRESSES)
    entity_data = load_json(ENTITY_RANKINGS)

    ranking = choose_rows(product_data.get("ranking") or [], 8)
    deals = choose_rows(product_data.get("deals") or [], 6)
    high_rated = choose_rows(product_data.get("highRated") or [], 4)
    actresses = choose_rows(actress_data.get("actresses") or [], 8)
    groups = entity_data.get("groups") or {}
    genres = (groups.get("genre") or [])[:12]

    ranking_html = "".join(product_card(row, i) for i, row in enumerate(ranking, 1)) or '<p>ランキングを更新中です。</p>'
    deals_html = "".join(product_card(row) for row in deals) or '<p>セール情報を更新中です。</p>'
    actress_html = "".join(actress_card(row) for row in actresses) or '<p>人気女優データを更新中です。</p>'
    genre_html = "".join(genre_card(row) for row in genres) or '<a class="instant-genre" href="/ranking/genre/"><strong>ジャンル一覧</strong></a>'
    high_html = "".join(product_card(row) for row in high_rated)
    high_section = ""
    if high_html:
        high_section = f'''<section class="instant-section"><div class="instant-wrap"><div class="instant-section-head"><div><span>評価から選ぶ</span><h2>高評価作品</h2></div><a href="/ranking/">ほかのランキング →</a></div><div class="instant-product-grid instant-small-grid">{high_html}</div></div></section>'''

    return f'''<main class="instant-home">
{CHOOSER_CSS}
<section class="instant-hero"><div class="instant-wrap">
<div class="instant-eyebrow">18+ / すぐ決める作品ナビ</div>
<h1>探すより、候補を絞ってもらう。</h1>
<p>何千作品も見る必要はありません。今の気分を3つ選べば、候補を数本まで絞ります。</p>
<div class="instant-actions"><a class="primary" href="#instantChooser">30秒で決める</a><a href="/ranking/actress/popular/">人気女優から探す</a><a href="/search/">作品名・女優名で検索</a></div>
<div class="instant-shortcuts"><a href="/ranking/">ランキング</a><a href="/sale/">セール</a><a href="/ranking/actress/">女優50音</a><a href="/ranking/genre/">ジャンル</a><a href="/fc2-adult/">FC2</a></div>
</div></section>

{chooser_html()}

<section class="instant-section" id="popular-now"><div class="instant-wrap">
<div class="instant-section-head"><div><span>まだ迷うならここ</span><h2>人気作品</h2></div><a href="/ranking/">ランキングを全部見る →</a></div>
<div class="instant-product-grid">{ranking_html}</div>
</div></section>

<section class="instant-section instant-soft"><div class="instant-wrap">
<div class="instant-section-head"><div><span>顔から決めたい人向け</span><h2>人気女優から探す</h2></div><a href="/ranking/actress/popular/">人気女優を全部見る →</a></div>
<div class="instant-actress-grid">{actress_html}</div>
<div class="instant-under-links"><a href="/ranking/actress/">50音から女優を探す</a><a href="/search/">女優名を検索する</a></div>
</div></section>

<section class="instant-section"><div class="instant-wrap">
<div class="instant-section-head"><div><span>好みが決まっている人向け</span><h2>ジャンルから探す</h2></div><a href="/ranking/genre/">ジャンル一覧 →</a></div>
<div class="instant-genre-grid">{genre_html}</div>
</div></section>

<section class="instant-section instant-sale"><div class="instant-wrap">
<div class="instant-section-head"><div><span>安く見つけたい人向け</span><h2>セール作品</h2></div><a href="/sale/">セールを全部見る →</a></div>
<div class="instant-product-grid">{deals_html}</div>
</div></section>

{high_section}

<section class="instant-section instant-more"><div class="instant-wrap">
<h2>ほかの探し方</h2>
<div class="instant-more-grid"><a href="/products/"><strong>作品一覧</strong><span>新着から幅広く見る</span></a><a href="/search/"><strong>サイト内検索</strong><span>作品名・女優名から探す</span></a><a href="/subscription/"><strong>見放題比較</strong><span>月額でまとめて見たい</span></a><a href="/reviews/"><strong>レビュー</strong><span>評価を見てから決める</span></a><a href="/fc2-adult/"><strong>FC2アダルト</strong><span>FC2系から探す</span></a><a href="/guide/"><strong>初心者ガイド</strong><span>使い方を確認したい人向け</span></a></div>
<details class="instant-info"><summary>このサイトについて・PR表記</summary><p>商品情報・価格・販売状況は変動するため、購入前にリンク先の公式情報をご確認ください。当サイトにはアフィリエイト広告が含まれます。</p></details>
</div></section>
{CHOOSER_JS}
</main>'''


def main() -> None:
    if not HOME.exists():
        print("Homepage not found; skipped")
        return
    text = HOME.read_text(encoding="utf-8")
    before = text

    text = re.sub(r'<link\s+rel="stylesheet"\s+href="/assets/instant-discovery-v1\.css(?:\?v=[^"]*)?"\s*/?>', '', text, flags=re.I)
    if "</head>" in text:
        text = text.replace("</head>", f'<link rel="stylesheet" href="{CSS}"></head>', 1)

    text = re.sub(r'<main\b.*?</main>', build_main(), text, count=1, flags=re.S)
    text = re.sub(r'<title>.*?</title>', '<title>30秒で好みの作品を決める | オカズはよりどりみどり</title>', text, count=1, flags=re.S)
    text = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="人気・高評価・新作・セールと好みを選ぶだけで、FANZA作品を5〜10本まで絞れる成人向け作品ナビ。">', text, count=1)

    if text != before:
        HOME.write_text(text, encoding="utf-8")
        print("Homepage optimized for 30-second recommendation discovery")
    else:
        print("Homepage already optimized")


if __name__ == "__main__":
    main()
