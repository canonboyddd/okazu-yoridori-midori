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
      .fanza-product-card{display:flex;flex-direction:column;min-width:0;border:1px solid #eee;border-radius:14px;overflow:hidden;background:#fff;text-decoration:none!important;color:inherit!important}
      .fanza-product-card:hover{transform:translateY(-2px);box-shadow:0 8px 22px rgba(0,0,0,.07)}
      .fanza-product-image{aspect-ratio:3/4;background:#f6f6f6;overflow:hidden}
      .fanza-product-image img{width:100%;height:100%;object-fit:cover;display:block}
      .fanza-product-body{padding:12px;display:flex;flex-direction:column;gap:7px;flex:1}
      .fanza-product-pr{font-size:.72rem;font-weight:700;color:#a23b57}
      .fanza-product-title{font-size:.92rem;font-weight:700;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
      .fanza-product-meta{margin-top:auto;display:flex;justify-content:space-between;gap:8px;font-size:.82rem;color:#555;flex-wrap:wrap}
      .fanza-api-credit{margin-top:14px;font-size:.76rem;color:#777}
      .fanza-api-credit a{color:inherit}
      @media(max-width:900px){.fanza-product-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
      @media(max-width:640px){.fanza-product-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.fanza-api-section{padding:14px}.fanza-product-body{padding:9px}}
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
        window.gtag("event", "affiliate_click", {
          affiliate_service: "DMM/FANZA",
          affiliate_target: target,
          page_path: location.pathname
        });
      } else if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push({
          event: "affiliate_click",
          affiliate_service: "DMM/FANZA",
          affiliate_target: target,
          page_path: location.pathname
        });
      }
    });
  }

  function productCard(item, targetPrefix, index) {
    const a = document.createElement("a");
    a.className = "fanza-product-card";
    a.href = item.affiliateURL;
    track(a, `${targetPrefix}-${index + 1}`);

    const media = document.createElement("div");
    media.className = "fanza-product-image";
    if (item.imageURL) {
      const img = document.createElement("img");
      img.src = item.imageURL;
      img.alt = item.title || "FANZA商品";
      img.loading = "lazy";
      img.decoding = "async";
      media.appendChild(img);
    }

    const body = document.createElement("div");
    body.className = "fanza-product-body";

    const pr = document.createElement("div");
    pr.className = "fanza-product-pr";
    pr.textContent = "PR / 広告";

    const title = document.createElement("div");
    title.className = "fanza-product-title";
    title.textContent = item.title || "FANZA商品";

    const meta = document.createElement("div");
    meta.className = "fanza-product-meta";
    const price = money(item.price);
    if (price) {
      const p = document.createElement("span");
      p.textContent = price;
      meta.appendChild(p);
    }
    if (item.reviewAverage) {
      const r = document.createElement("span");
      r.textContent = `★ ${item.reviewAverage}`;
      meta.appendChild(r);
    }

    body.append(pr, title, meta);
    a.append(media, body);
    return a;
  }

  function makeSection(titleText, noteText, items, targetPrefix) {
    if (!Array.isArray(items) || !items.length) return null;
    const section = document.createElement("section");
    section.className = "fanza-api-section";
    section.dataset.fanzaApiSection = targetPrefix;

    const head = document.createElement("div");
    head.className = "fanza-api-head";
    const title = document.createElement("h2");
    title.textContent = titleText;
    const note = document.createElement("p");
    note.className = "fanza-api-note";
    note.textContent = noteText;
    head.append(title, note);

    const grid = document.createElement("div");
    grid.className = "fanza-product-grid";
    items.slice(0, 8).forEach((item, i) => grid.appendChild(productCard(item, targetPrefix, i)));

    const credit = document.createElement("div");
    credit.className = "fanza-api-credit";
    credit.innerHTML = CREDIT_HTML;

    section.append(head, grid, credit);
    return section;
  }

  function placeSection(section, mode) {
    if (!section) return;
    if (mode === "home") {
      const hero = document.querySelector(".hero");
      if (hero) hero.insertAdjacentElement("afterend", section);
      return;
    }
    const slot = document.querySelector(".affiliate-slot");
    if (slot) {
      slot.insertAdjacentElement("afterend", section);
      return;
    }
    const main = document.querySelector("main");
    if (main) main.appendChild(section);
  }

  async function init() {
    ensureStyles();
    addCredit();
    let data;
    try {
      const res = await fetch("/data/fanza-products.json", { cache: "no-store" });
      if (!res.ok) return;
      data = await res.json();
    } catch (_) {
      return;
    }

    const path = location.pathname;
    if (path === "/") {
      placeSection(
        makeSection("FANZA人気作品", "商品情報はFANZA Webサービスから取得しています。価格・配信状況は公式ページで最終確認してください。", data.ranking, "api-home-rank"),
        "home"
      );
    } else if (path.startsWith("/ranking")) {
      placeSection(
        makeSection("FANZA人気ランキング", "ランキング順で取得した商品情報です。順位・価格は変動します。", data.ranking, "api-ranking"),
        "ranking"
      );
    } else if (path.startsWith("/discover") || path.startsWith("/latest")) {
      placeSection(
        makeSection("FANZA新着作品", "新着順で取得した商品情報です。", data.latest, "api-latest"),
        "latest"
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
