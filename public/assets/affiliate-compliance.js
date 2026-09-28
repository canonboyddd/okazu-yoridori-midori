document.addEventListener("DOMContentLoaded", () => {
  const cfg = window.AFFILIATE_CONFIG || {};
  const links = cfg.links || {};
  const API_AFFILIATE_ID = cfg.apiAffiliateId || "okazumidori-990";

  function repairFanzaAffiliateUrl(raw) {
    if (!raw) return raw;
    try {
      const u = new URL(raw, location.href);
      const host = u.hostname.toLowerCase();
      const isAffiliateHost = ["al.dmm.co.jp", "al.dmm.com", "al.fanza.co.jp", "al.fanza.com"].includes(host);
      if (!isAffiliateHost) return raw;

      const afId = u.searchParams.get("af_id") || "";
      const channel = u.searchParams.get("ch") || "";
      if (afId === "okazumidori-001" && channel === "link_tool") {
        u.searchParams.set("af_id", API_AFFILIATE_ID);
        u.searchParams.set("ch", "api");
        u.searchParams.delete("ch_id");
        return u.toString();
      }
    } catch (_) {}
    return raw;
  }

  window.repairFanzaAffiliateUrl = repairFanzaAffiliateUrl;
  Object.keys(links).forEach(key => {
    links[key] = repairFanzaAffiliateUrl(links[key]);
  });

  const style = document.createElement("style");
  style.textContent = `
    .affiliate-live{margin:24px 0;padding:18px;border:1px solid #f1d5dc;border-radius:16px;background:#fff8fa}
    .affiliate-live>strong{display:inline-block;font-size:.78rem;letter-spacing:.04em;color:#a23b57;margin-bottom:6px}
    .affiliate-live p{margin:4px 0 12px}
    .affiliate-actions{display:flex;gap:10px;flex-wrap:wrap}
    .affiliate-cta{display:inline-flex;align-items:center;justify-content:center;padding:11px 16px;border-radius:999px;background:#111;color:#fff!important;text-decoration:none!important;font-weight:700}
    .affiliate-cta:hover{opacity:.86}
    .fc-description{margin:18px 0 16px;padding:18px 20px;border:1px solid #e7d7ee;border-radius:16px;background:linear-gradient(135deg,#fff8fb,#f8f7ff)}
    .fc-description-title{font-size:1rem;font-weight:800;color:#111827;margin-bottom:8px}
    .fc-description-text{margin:0;color:#374151;line-height:1.8;font-size:.95rem}
    .fc-description-note{margin:8px 0 0;color:#6b7280;font-size:.76rem;line-height:1.6}
  `;
  document.head.appendChild(style);

  function button(url, text, target) {
    const a = document.createElement("a");
    a.href = repairFanzaAffiliateUrl(url);
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

  function detailValue(label) {
    const terms = document.querySelectorAll(".fc-detail dl dt");
    for (const dt of terms) {
      if ((dt.textContent || "").trim() === label) {
        return (dt.nextElementSibling?.textContent || "").replace(/\s+/g, " ").trim();
      }
    }
    return "";
  }

  function ensureProductDescription() {
    if (!path.startsWith("/products/") || document.querySelector(".fc-description")) return;
    const detail = document.querySelector(".fc-detail");
    if (!detail) return;
    const title = (detail.querySelector("h1")?.textContent || "").replace(/\s+/g, " ").trim();
    if (!title) return;

    const actress = detailValue("出演者");
    const maker = detailValue("メーカー");
    const genre = detailValue("ジャンル");
    const pieces = [];
    if (actress && actress !== "情報なし") pieces.push(`${actress}出演`);
    if (maker && maker !== "情報なし") pieces.push(`${maker}の作品`);

    let text = `「${title}」は`;
    if (pieces.length) text += `${pieces.join("、")}です。`;
    else text += "FANZAで配信されている作品です。";
    if (genre && genre !== "情報なし") text += ` ジャンルは${genre}。`;
    text += " 出演者・メーカー・ジャンル・レビュー・配信日など、作品選びに必要な情報をこのページでまとめています。";

    const box = document.createElement("section");
    box.className = "fc-description";
    box.setAttribute("aria-label", "作品紹介");
    box.innerHTML = `<div class="fc-description-title">作品紹介</div><p class="fc-description-text"></p><p class="fc-description-note">商品内容・価格・配信状況はFANZA公式の最新情報もあわせてご確認ください。</p>`;
    box.querySelector(".fc-description-text").textContent = text;

    const dl = detail.querySelector("dl");
    const cta = detail.querySelector(".fc-cta");
    if (dl) dl.insertAdjacentElement("afterend", box);
    else if (cta) cta.insertAdjacentElement("beforebegin", box);
  }

  ensureProductDescription();

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

  function isDmmHost(hostname) {
    const h = String(hostname || "").toLowerCase();
    return [
      "dmm.co.jp",
      "dmm.com",
      "al.dmm.co.jp",
      "al.dmm.com",
      "fanza.co.jp",
      "al.fanza.co.jp",
      "affiliate.dmm.com"
    ].some(x => h === x || h.endsWith("." + x));
  }

  function prepareAffiliateAnchor(a) {
    if (!a || !a.href) return;
    try {
      const repaired = repairFanzaAffiliateUrl(a.href);
      if (repaired && repaired !== a.href) a.href = repaired;

      const u = new URL(a.href, location.href);
      if (!isDmmHost(u.hostname)) return;

      const rel = new Set((a.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
      ["sponsored", "nofollow", "noopener", "noreferrer"].forEach(x => rel.add(x));
      a.setAttribute("rel", [...rel].join(" "));
      a.dataset.affiliateTrackingReady = "1";
    } catch (_) {}
  }

  document.querySelectorAll("a[href]").forEach(prepareAffiliateAnchor);

  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches("a[href]")) prepareAffiliateAnchor(node);
        node.querySelectorAll?.("a[href]").forEach(prepareAffiliateAnchor);
      }
    }
  });
  observer.observe(document.body, {childList: true, subtree: true});

  document.addEventListener("click", event => {
    const a = event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (a) prepareAffiliateAnchor(a);
  }, true);

  const apiScript = document.createElement("script");
  apiScript.src = "/assets/fanza-products.js?v=20260928-0115";
  apiScript.async = true;
  document.body.appendChild(apiScript);

  const fc2Script = document.createElement("script");
  fc2Script.src = "/assets/fc2-affiliate-banners.js?v=20260926-1032";
  fc2Script.async = true;
  document.body.appendChild(fc2Script);
});
