(() => {
  const CREDIT_HTML = 'Powered by <a href="https://affiliate.dmm.com/api/" target="_blank" rel="noopener">FANZA Webサービス</a>';

  function ensureStyles() {
    if (document.getElementById("fanzaApiStyles")) return;
    const style = document.createElement("style");
    style.id = "fanzaApiStyles";
    style.textContent = `
      .fanza-api-section{margin:34px 0;padding:22px;border:1px solid #ececec;border-radius:18px;background:#fff}
      .fanza-api-head{display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap;margin-bottom:16px}
      .fanza-api-head h2{margin:0}
      .fanza-api-note{font-size:.84rem;color:#666;margin:0}
      .fanza-product-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
      .fanza-product-card{position:relative;display:flex;flex-direction:column;min-width:0;border:1px solid #eee;border-radius:16px;overflow:hidden;background:#fff;text-decoration:none!important;color:inherit!important;transition:.18s ease}
      .fanza-product-card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,0,0,.08)}
      .fanza-product-image{aspect-ratio:3/4;background:#f6f6f6;overflow:hidden;position:relative}
      .fanza-product-image img{width:100%;height:100%;object-fit:cover;display:block}
      .fanza-rank-badge{position:absolute;top:10px;left:10px;z-index:2;min-width:34px;height:34px;padding:0 8px;display:flex;align-items:center;justify-content:center;border-radius:999px;background:#111;color:#fff;font-size:.82rem;font-weight:800;box-shadow:0 4px 12px rgba(0,0,0,.18)}
      .fanza-rank-badge.top1{background:linear-gradient(135deg,#c79b18,#f3cf64);color:#201700}.fanza-rank-badge.top2{background:linear-gradient(135deg,#929292,#dedede);color:#171717}.fanza-rank-badge.top3{background:linear-gradient(135deg,#a9632e,#d99a66);color:#fff}
      .fanza-discount-badge{position:absolute;top:10px;right:10px;z-index:2;padding:6px 9px;border-radius:999px;background:#d81b46;color:#fff;font-size:.74rem;font-weight:800}
      .fanza-product-body{padding:13px;display:flex;flex-direction:column;gap:8px;flex:1}
      .fanza-product-pr{font-size:.7rem;font-weight:800;color:#a23b57;letter-spacing:.03em}
      .fanza-product-title{font-size:.94rem;font-weight:800;line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
      .fanza-product-sub{font-size:.77rem;color:#777;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
      .fanza-product-meta{margin-top:auto;display:flex;justify-content:space-between;gap:8px;font-size:.83rem;color:#555;flex-wrap:wrap;align-items:center}
      .fanza-price{font-weight:800;color:#111}.fanza-list-price{text-decoration:line-through;color:#999;margin-right:6px;font-weight:500}
      .fanza-review{white-space:nowrap}.fanza-review strong{color:#111}
      .fanza-api-credit{margin-top:14px;font-size:.76rem;color:#777}.fanza-api-credit a{color:inherit}
      .ranking-dashboard{margin:0 0 28px}
      .ranking-toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin:18px 0 20px}
      .ranking-tabs{display:flex;gap:8px;flex-wrap:wrap}.ranking-tab{border:1px solid #ddd;background:#fff;border-radius:999px;padding:10px 15px;font-weight:800;cursor:pointer}.ranking-tab.active{background:#111;color:#fff;border-color:#111}
      .ranking-controls{display:flex;gap:8px;flex-wrap:wrap}.ranking-controls input,.ranking-controls select{border:1px solid #ddd;border-radius:10px;padding:10px 12px;background:#fff;min-height:42px}
      .ranking-controls input{min-width:220px}
      .ranking-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0 22px}.ranking-stat{padding:14px;border:1px solid #eee;border-radius:14px;background:#fafafa}.ranking-stat b{display:block;font-size:1.25rem}.ranking-stat span{font-size:.76rem;color:#666}
      .ranking-featured{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0 28px}.ranking-featured .fanza-product-card:nth-child(1){transform:translateY(-5px)}
      .ranking-featured .fanza-product-image{aspect-ratio:4/5}
      .ranking-empty{padding:28px;border:1px dashed #ddd;border-radius:14px;text-align:center;color:#777}
      .ranking-updated{font-size:.8rem;color:#777}
      .ranking-loadmore{display:flex;justify-content:center;margin-top:20px}.ranking-loadmore button{border:1px solid #111;background:#fff;border-radius:999px;padding:11px 18px;font-weight:800;cursor:pointer}.ranking-loadmore button:hover{background:#111;color:#fff}
      @media(max-width:900px){.fanza-product-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.ranking-summary{grid-template-columns:repeat(2,1fr)}}
      @media(max-width:700px){.ranking-featured{grid-template-columns:1fr 1fr}.ranking-featured .fanza-product-card:nth-child(3){display:none}.ranking-controls{width:100%}.ranking-controls input{flex:1;min-width:0}.ranking-controls select{flex:0 0 auto}}
      @media(max-width:640px){.fanza-product-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.fanza-api-section{padding:14px}.fanza-product-body{padding:10px}.ranking-summary{grid-template-columns:repeat(2,1fr)}.ranking-toolbar{align-items:stretch}.ranking-tabs{width:100%}.ranking-tab{flex:1;padding:9px 8px;font-size:.82rem}.ranking-controls{display:grid;grid-template-columns:1fr 120px}.ranking-featured{grid-template-columns:1fr 1fr}.fanza-product-title{font-size:.86rem}.fanza-product-sub{display:none}}
    `;
    document.head.appendChild(style);
  }

  function addCredit() {
    if (document.querySelector("[data-fanza-credit='1']")) return;
    const footerWrap = document.querySelector("footer .wrap") || document.querySelector("footer");
    if (!footerWrap) return;
    const credit = document.createElement("div");
    credit.className = "fanza-api-credit";
    credit.dataset.fanzaCredit = "1";
    credit.innerHTML = CREDIT_HTML;
    footerWrap.appendChild(credit);
  }

  function money(value) {
    const s = String(value || "").trim();
    if (!s) return "";
    const n = Number(s.replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(n)) return s;
    return `¥${Math.round(n).toLocaleString("ja-JP")}`;
  }

  function track(a, target) {
    a.dataset.affiliateTarget = target;
    a.rel = "sponsored nofollow noopener noreferrer";
    a.target = "_blank";
    a.addEventListener("click", () => {
      if (typeof window.gtag === "function") {
        window.gtag("event", "affiliate_click", {affiliate_service:"DMM/FANZA",affiliate_target:target,page_path:location.pathname});
      } else if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push({event:"affiliate_click",affiliate_service:"DMM/FANZA",affiliate_target:target,page_path:location.pathname});
      }
    });
  }

  function rankBadge(index) {
    const badge = document.createElement("span");
    badge.className = `fanza-rank-badge ${index===0?"top1":index===1?"top2":index===2?"top3":""}`;
    badge.textContent = `${index + 1}位`;
    return badge;
  }

  function productCard(item, targetPrefix, index, showRank = false) {
    const a = document.createElement("a");
    a.className = "fanza-product-card";
    a.href = item.affiliateURL;
    track(a, `${targetPrefix}-${index + 1}`);

    const media = document.createElement("div");
    media.className = "fanza-product-image";
    if (showRank) media.appendChild(rankBadge(index));
    if (Number(item.discountRate || 0) > 0) {
      const sale = document.createElement("span");
      sale.className = "fanza-discount-badge";
      sale.textContent = `${item.discountRate}%OFF`;
      media.appendChild(sale);
    }
    if (item.imageURL) {
      const img = document.createElement("img");
      img.src = item.imageURL;
      img.alt = item.title || "FANZA商品";
      img.loading = index < 3 ? "eager" : "lazy";
      img.decoding = "async";
      media.appendChild(img);
    }

    const body = document.createElement("div");
    body.className = "fanza-product-body";
    const pr = document.createElement("div"); pr.className = "fanza-product-pr"; pr.textContent = "PR / 広告";
    const title = document.createElement("div"); title.className = "fanza-product-title"; title.textContent = item.title || "FANZA商品";
    const sub = document.createElement("div"); sub.className = "fanza-product-sub";
    sub.textContent = [item.maker, ...(item.actresses || []).slice(0,2)].filter(Boolean).join(" / ") || (item.series || "");
    const meta = document.createElement("div"); meta.className = "fanza-product-meta";
    const priceWrap = document.createElement("span"); priceWrap.className = "fanza-price";
    if (item.listPrice && Number(item.discountRate || 0) > 0) priceWrap.innerHTML = `<span class="fanza-list-price">${money(item.listPrice)}</span>${money(item.price)}`;
    else priceWrap.textContent = money(item.price) || "公式で価格確認";
    const review = document.createElement("span"); review.className = "fanza-review";
    if (item.reviewAverage) review.innerHTML = `★ <strong>${item.reviewAverage}</strong>${item.reviewCount ? ` (${item.reviewCount})` : ""}`;
    meta.appendChild(priceWrap); if (item.reviewAverage) meta.appendChild(review);
    body.append(pr, title); if (sub.textContent) body.appendChild(sub); body.appendChild(meta);
    a.append(media, body);
    return a;
  }

  function makeSection(titleText, noteText, items, targetPrefix) {
    if (!Array.isArray(items) || !items.length) return null;
    const section = document.createElement("section"); section.className = "fanza-api-section"; section.dataset.fanzaApiSection = targetPrefix;
    const head = document.createElement("div"); head.className = "fanza-api-head";
    const title = document.createElement("h2"); title.textContent = titleText;
    const note = document.createElement("p"); note.className = "fanza-api-note"; note.textContent = noteText;
    head.append(title, note);
    const grid = document.createElement("div"); grid.className = "fanza-product-grid";
    items.slice(0, 8).forEach((item, i) => grid.appendChild(productCard(item, targetPrefix, i)));
    const credit = document.createElement("div"); credit.className = "fanza-api-credit"; credit.innerHTML = CREDIT_HTML;
    section.append(head, grid, credit); return section;
  }

  function placeSection(section, mode) {
    if (!section) return;
    if (mode === "home") { const hero = document.querySelector(".hero"); if (hero) hero.insertAdjacentElement("afterend", section); return; }
    const slot = document.querySelector(".affiliate-slot"); if (slot) { slot.insertAdjacentElement("afterend", section); return; }
    const main = document.querySelector("main"); if (main) main.appendChild(section);
  }

  function formatDate(iso) {
    try { return new Intl.DateTimeFormat("ja-JP", {year:"numeric",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"Asia/Tokyo"}).format(new Date(iso)); }
    catch (_) { return ""; }
  }

  function unique(items) {
    const seen = new Set(); return (items || []).filter(x => { const k = x.contentId || x.affiliateURL; if (!k || seen.has(k)) return false; seen.add(k); return true; });
  }

  function renderRankingDashboard(data) {
    const mount = document.getElementById("rankingApp");
    if (!mount) return;

    const datasets = {
      ranking: unique(data.ranking),
      latest: unique(data.latest),
      highRated: unique(data.highRated || []),
      deals: unique(data.deals || [])
    };
    let active = "ranking";
    let visible = 16;
    let query = "";
    let sortMode = "default";

    mount.innerHTML = `
      <div class="ranking-dashboard">
        <div class="ranking-summary">
          <div class="ranking-stat"><b>${datasets.ranking.length}</b><span>人気ランキング取得件数</span></div>
          <div class="ranking-stat"><b>${datasets.latest.length}</b><span>新着取得件数</span></div>
          <div class="ranking-stat"><b>${datasets.highRated.length}</b><span>高評価候補</span></div>
          <div class="ranking-stat"><b>${datasets.deals.length}</b><span>値引き確認できた商品</span></div>
        </div>
        <div id="rankingFeatured"></div>
        <div class="ranking-toolbar">
          <div class="ranking-tabs" role="tablist">
            <button class="ranking-tab active" data-tab="ranking">人気</button>
            <button class="ranking-tab" data-tab="latest">新着</button>
            <button class="ranking-tab" data-tab="highRated">高評価</button>
            <button class="ranking-tab" data-tab="deals">セール</button>
          </div>
          <div class="ranking-controls">
            <input id="rankingSearch" type="search" placeholder="作品名・女優・メーカーで検索">
            <select id="rankingSort" aria-label="並び替え">
              <option value="default">おすすめ順</option>
              <option value="review">評価順</option>
              <option value="reviews">レビュー件数順</option>
              <option value="priceAsc">価格が安い順</option>
              <option value="priceDesc">価格が高い順</option>
            </select>
          </div>
        </div>
        <div class="ranking-updated">APIデータ更新: ${formatDate(data.generatedAt)} JST</div>
        <div id="rankingGrid" class="fanza-product-grid" style="margin-top:12px"></div>
        <div id="rankingEmpty" class="ranking-empty" hidden>条件に一致する商品がありません。</div>
        <div class="ranking-loadmore"><button id="rankingMore" type="button">さらに表示</button></div>
        <div class="fanza-api-credit">${CREDIT_HTML}</div>
      </div>`;

    const grid = mount.querySelector("#rankingGrid");
    const featured = mount.querySelector("#rankingFeatured");
    const empty = mount.querySelector("#rankingEmpty");
    const more = mount.querySelector("#rankingMore");

    function filtered() {
      let list = [...(datasets[active] || [])];
      if (query) {
        const q = query.toLowerCase();
        list = list.filter(item => [item.title,item.maker,item.series,...(item.actresses||[]),...(item.genres||[])].filter(Boolean).join(" ").toLowerCase().includes(q));
      }
      if (sortMode === "review") list.sort((a,b) => Number(b.reviewAverage||0)-Number(a.reviewAverage||0));
      else if (sortMode === "reviews") list.sort((a,b) => Number(b.reviewCount||0)-Number(a.reviewCount||0));
      else if (sortMode === "priceAsc") list.sort((a,b) => Number(a.priceValue||99999999)-Number(b.priceValue||99999999));
      else if (sortMode === "priceDesc") list.sort((a,b) => Number(b.priceValue||0)-Number(a.priceValue||0));
      return list;
    }

    function drawFeatured() {
      featured.innerHTML = "";
      if (active !== "ranking" || query || sortMode !== "default") return;
      const top = datasets.ranking.slice(0,3);
      if (!top.length) return;
      const h = document.createElement("div"); h.className = "fanza-api-head"; h.innerHTML = '<div><span class="update-badge">TOP 3</span><h2 style="margin:.35rem 0 0">いま人気の上位3作品</h2></div><p class="fanza-api-note">FANZA Webサービスの人気順データを使用</p>';
      const box = document.createElement("div"); box.className = "ranking-featured";
      top.forEach((item,i) => box.appendChild(productCard(item,"api-ranking-top",i,true)));
      featured.append(h,box);
    }

    function draw() {
      const list = filtered();
      grid.innerHTML = "";
      list.slice(0,visible).forEach((item,i) => grid.appendChild(productCard(item,`api-ranking-${active}`,i,active==="ranking"&&sortMode==="default"&&!query)));
      empty.hidden = list.length !== 0;
      more.parentElement.style.display = list.length > visible ? "flex" : "none";
      drawFeatured();
    }

    mount.querySelectorAll(".ranking-tab").forEach(btn => btn.addEventListener("click", () => {
      active = btn.dataset.tab; visible = 16; query = ""; sortMode = "default";
      mount.querySelectorAll(".ranking-tab").forEach(x => x.classList.toggle("active", x === btn));
      mount.querySelector("#rankingSearch").value = ""; mount.querySelector("#rankingSort").value = "default"; draw();
      if (typeof window.gtag === "function") window.gtag("event","ranking_tab_change",{ranking_tab:active,page_path:location.pathname});
    }));
    mount.querySelector("#rankingSearch").addEventListener("input", e => { query = e.target.value.trim(); visible = 16; draw(); });
    mount.querySelector("#rankingSort").addEventListener("change", e => { sortMode = e.target.value; visible = 16; draw(); });
    more.addEventListener("click", () => { visible += 16; draw(); });
    draw();
  }

  async function init() {
    ensureStyles(); addCredit();
    let data; try { const res = await fetch("/data/fanza-products.json", { cache: "no-store" }); if (!res.ok) return; data = await res.json(); } catch (_) { return; }
    const path = location.pathname;
    if (path === "/") placeSection(makeSection("FANZA人気作品","商品情報はFANZA Webサービスから取得しています。価格・配信状況は公式ページで最終確認してください。",data.ranking,"api-home-rank"),"home");
    else if (path.startsWith("/ranking")) renderRankingDashboard(data);
    else if (path.startsWith("/discover") || path.startsWith("/latest")) placeSection(makeSection("FANZA新着作品","新着順で取得した商品情報です。",data.latest,"api-latest"),"latest");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true }); else init();
})();
