document.addEventListener("DOMContentLoaded", () => {
  const cfg = window.AFFILIATE_CONFIG || {};
  const links = cfg.links || {};

  const style = document.createElement("style");
  style.textContent = `
    .affiliate-live{margin:24px 0;padding:18px;border:1px solid #f1d5dc;border-radius:16px;background:#fff8fa}
    .affiliate-live>strong{display:inline-block;font-size:.78rem;letter-spacing:.04em;color:#a23b57;margin-bottom:6px}
    .affiliate-live p{margin:4px 0 12px}
    .affiliate-actions{display:flex;gap:10px;flex-wrap:wrap}
    .affiliate-cta{display:inline-flex;align-items:center;justify-content:center;padding:11px 16px;border-radius:999px;background:#111;color:#fff!important;text-decoration:none!important;font-weight:700}
    .affiliate-cta:hover{opacity:.86}
  `;
  document.head.appendChild(style);

  function button(url, text, target) {
    const a = document.createElement("a");
    a.href = url;
    a.textContent = text;
    a.className = "affiliate-cta";
    a.target = "_blank";
    a.rel = "sponsored nofollow noopener noreferrer";
    a.dataset.affiliateTarget = target;
    return a;
  }

  function fillSlot(slot, kind) {
    if (!slot || slot.dataset.affiliateLive === "1") return;
    slot.dataset.affiliateLive = "1";
    slot.classList.add("affiliate-live");
    slot.innerHTML = "";

    const label = document.createElement("strong");
    label.textContent = "PR / 広告";
    const p = document.createElement("p");
    const actions = document.createElement("div");
    actions.className = "affiliate-actions";

    if (kind === "sale") {
      p.textContent = "最新の価格・セール・キャンペーン条件はFANZA公式で確認してください。";
      actions.appendChild(button(links.video, "FANZA公式で最新情報を確認", "sale-video"));
    } else if (kind === "ranking") {
      p.textContent = "順位・価格・販売条件は変動するため、購入前にFANZA公式ランキングで確認してください。";
      actions.appendChild(button(links.ranking, "FANZA公式ランキングを見る", "ranking-video"));
    } else if (kind === "subscription") {
      p.textContent = "月額料金・対象作品・キャンペーン・解約条件は各公式ページの最新情報を確認してください。";
      actions.appendChild(button(links.monthly, "FANZA月額動画を公式で確認", "monthly"));
      actions.appendChild(button(links.premium, "FANZA TV / DMMプレミアムを確認", "premium"));
    } else {
      p.textContent = "価格・配信状況・販売条件はFANZA公式サイトの最新情報を確認してください。";
      actions.appendChild(button(links.video, "FANZA公式サイトで確認", "video-top"));
    }

    slot.append(label, p, actions);
  }

  const path = location.pathname;
  let kind = "default";
  if (path.startsWith("/sale")) kind = "sale";
  else if (path.startsWith("/ranking")) kind = "ranking";
  else if (path.startsWith("/subscription")) kind = "subscription";

  document.querySelectorAll(".affiliate-slot").forEach(slot => fillSlot(slot, kind));

  if (path === "/" && !document.querySelector("[data-home-affiliate='1']") && links.video) {
    const notice = document.querySelector(".hero .notice");
    if (notice) {
      const box = document.createElement("div");
      box.className = "affiliate-slot";
      box.dataset.homeAffiliate = "1";
      notice.insertAdjacentElement("afterend", box);
      fillSlot(box, "default");
      const actions = box.querySelector(".affiliate-actions");
      if (actions && links.monthly) {
        actions.appendChild(button(links.monthly, "見放題・月額プランを確認", "home-monthly"));
      }
    }
  }

  if (path.startsWith("/articles/") && !document.querySelector("[data-article-affiliate='1']") && links.video) {
    const main = document.querySelector("main");
    if (main) {
      const box = document.createElement("div");
      box.className = "affiliate-slot";
      box.dataset.articleAffiliate = "1";
      main.appendChild(box);
      fillSlot(box, "default");
    }
  }

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const replaces = [
    ["承認後に追加する収益導線", "FANZA公式への収益導線"],
    ["承認後のランキング枠", "FANZA公式ランキングへの導線"],
    ["承認後の商品導線", "広告・商品導線"],
    ["DMM審査通過後にアフィリエイトID/APIを設定すると、この位置に公式商品・キャンペーン導線を表示する設計です。", "FANZA公式ページへの広告リンクを掲載しています。"]
  ];
  while (walker.nextNode()) {
    let t = walker.currentNode.nodeValue;
    for (const [from, to] of replaces) t = t.replaceAll(from, to);
    walker.currentNode.nodeValue = t;
  }

  document.querySelectorAll("a[href]").forEach(a => {
    try {
      const u = new URL(a.href, location.href);
      const h = u.hostname.toLowerCase();
      const isDmm = [
        "dmm.co.jp",
        "dmm.com",
        "al.dmm.co.jp",
        "al.dmm.com",
        "fanza.co.jp",
        "affiliate.dmm.com"
      ].some(x => h === x || h.endsWith("." + x));
      if (!isDmm) return;

      const rel = new Set((a.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
      ["sponsored", "nofollow", "noopener", "noreferrer"].forEach(x => rel.add(x));
      a.setAttribute("rel", [...rel].join(" "));

      a.addEventListener("click", () => {
        const target = a.dataset.affiliateTarget || u.hostname;
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
    } catch (_) {}
  });

  const apiScript = document.createElement("script");
  apiScript.src = "/assets/fanza-products.js?v=20260925-2108";
  apiScript.async = true;
  document.body.appendChild(apiScript);
});
