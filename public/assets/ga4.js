(function () {
  const cfg = window.GA4_CONFIG || {};
  const id = (cfg.measurementId || "").trim();
  const hasGa = /^G-[A-Z0-9]+$/i.test(id);
  const ATTR_KEY = "ops_origin_context";
  const ATTR_TTL_MS = 2 * 60 * 60 * 1000;

  window.dataLayer = window.dataLayer || [];
  if (!window.gtag) window.gtag = function(){ dataLayer.push(arguments); };

  if (hasGa) {
    const s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
    document.head.appendChild(s);
    gtag("js", new Date());
    gtag("config", id, {send_page_view: true, debug_mode: !!cfg.debugMode});
  }

  function uuid() {
    try { if (crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (_) {}
    return Date.now().toString(36) + "-" + Math.random().toString(36).slice(2) + "-" + Math.random().toString(36).slice(2);
  }

  function getStored(storage, key) {
    try {
      let value = storage.getItem(key);
      if (!value) { value = uuid(); storage.setItem(key, value); }
      return value;
    } catch (_) { return uuid(); }
  }

  const browserId = getStored(localStorage, "ops_browser_id");
  const sessionId = getStored(sessionStorage, "ops_session_id");

  function currentPath() { return location.pathname + location.search; }
  function deviceType() {
    const w = Math.max(window.innerWidth || 0, document.documentElement.clientWidth || 0);
    if (w <= 767) return "mobile";
    if (w <= 1100) return "tablet";
    return "desktop";
  }

  function textOf(selector) {
    const el = document.querySelector(selector);
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function detailValue(label) {
    const dts = [...document.querySelectorAll(".fc-detail dt")];
    const dt = dts.find(x => (x.textContent || "").trim() === label);
    return dt && dt.nextElementSibling ? (dt.nextElementSibling.textContent || "").replace(/\s+/g, " ").trim() : "";
  }

  function pageContext() {
    const path = location.pathname;
    const ctx = {page_type: "other", actress: "", genre: "", maker: "", product_id: ""};
    let m = path.match(/^\/ranking\/actress\/([^/]+)/);
    if (m && m[1] !== "aliases") { ctx.page_type = "actress"; ctx.actress = textOf("h1").replace(/\s+(AV作品一覧.*|人気作品.*|全[0-9,]+作品.*)$/i, ""); }
    m = path.match(/^\/ranking\/genre\/([^/]+)/);
    if (m) { ctx.page_type = "genre"; ctx.genre = textOf("h1").replace(/\s+(人気作品.*|全[0-9,]+作品.*)$/i, ""); }
    m = path.match(/^\/ranking\/maker\/([^/]+)/);
    if (m) { ctx.page_type = "maker"; ctx.maker = textOf("h1").replace(/\s+(人気作品.*|全[0-9,]+作品.*)$/i, ""); }
    m = path.match(/^\/products\/([^/]+)\/?$/);
    if (m && m[1] !== "view") { ctx.page_type = "product"; ctx.product_id = m[1]; }
    if (path.startsWith("/products/view")) { ctx.page_type = "product"; ctx.product_id = new URLSearchParams(location.search).get("id") || ""; }
    if (ctx.page_type === "product") {
      ctx.actress = detailValue("出演者");
      ctx.genre = detailValue("ジャンル");
      ctx.maker = detailValue("メーカー");
    }
    if (path.startsWith("/search/")) ctx.page_type = "search";
    else if (path.startsWith("/sale/")) ctx.page_type = "sale";
    else if (path === "/" || path === "") ctx.page_type = "home";
    else if (path.startsWith("/ranking/") && ctx.page_type === "other") ctx.page_type = "ranking";
    return ctx;
  }

  function rememberOriginContext(ctx) {
    if (!ctx || ctx.page_type === "product" || ctx.page_type === "other") return;
    try {
      sessionStorage.setItem(ATTR_KEY, JSON.stringify({
        ts: Date.now(),
        source_page: currentPath(),
        page_type: ctx.page_type || "",
        actress: ctx.actress || "",
        genre: ctx.genre || "",
        maker: ctx.maker || "",
      }));
    } catch (_) {}
  }

  function readOriginContext() {
    try {
      const raw = sessionStorage.getItem(ATTR_KEY);
      if (!raw) return null;
      const value = JSON.parse(raw);
      if (!value || !value.ts || Date.now() - Number(value.ts) > ATTR_TTL_MS) {
        sessionStorage.removeItem(ATTR_KEY);
        return null;
      }
      return value;
    } catch (_) { return null; }
  }

  function attributionParams() {
    const origin = readOriginContext();
    if (!origin) return {};
    return {
      origin_page_path: origin.source_page || "",
      origin_page_type: origin.page_type || "",
      origin_actress: origin.actress || "",
      origin_genre: origin.genre || "",
      origin_maker: origin.maker || "",
    };
  }

  function sendGa(name, params) {
    if (!hasGa) return;
    try { gtag("event", name, params || {}); } catch (_) {}
  }

  function sendOps(name, extra) {
    const ctx = pageContext();
    const payload = Object.assign({
      event_name: name,
      browser_id: browserId,
      session_id: sessionId,
      page_path: currentPath(),
      page_title: document.title,
      referrer: document.referrer || "",
      device_type: deviceType(),
      provider: "FANZA",
      page_type: ctx.page_type,
      actress: ctx.actress,
      genre: ctx.genre,
      maker: ctx.maker,
      product_id: ctx.product_id,
    }, extra || {});
    try {
      fetch("/api/ops-collect", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {});
    } catch (_) {}
  }

  window.trackOpsEvent = function(name, extra) {
    const params = Object.assign({page_path: currentPath(), page_title: document.title}, extra || {});
    sendGa(name, params);
    sendOps(name, extra || {});
  };

  const initialCtx = pageContext();
  sendOps("page_view", initialCtx.page_type === "product" ? attributionParams() : {});

  let scrolled90 = false;
  window.addEventListener("scroll", function () {
    if (scrolled90) return;
    const doc = document.documentElement;
    const max = Math.max(doc.scrollHeight - window.innerHeight, 1);
    if ((window.scrollY / max) * 100 >= 90) {
      scrolled90 = true;
      window.trackOpsEvent("scroll_90", {});
    }
  }, {passive:true});

  function ctaPosition(a) {
    const explicit = a.dataset.affiliateTarget || a.dataset.ctaPosition || "";
    if (explicit) return explicit.slice(0, 100);
    const text = (a.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (text.includes("ランキング")) return "ranking_cta";
    if (text.includes("月額") || text.includes("見放題")) return "subscription_cta";
    if (a.classList.contains("fc-cta")) {
      const all = [...document.querySelectorAll("a.fc-cta")];
      const i = all.indexOf(a);
      if (i === 0) return "product_top";
      if (i === all.length - 1) return "product_bottom";
      return "product_middle";
    }
    return "affiliate_link";
  }

  document.addEventListener("click", function (e) {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;

    let u;
    try { u = new URL(a.href, location.href); } catch (_) { return; }

    const text = (a.textContent || "").trim().replace(/\s+/g, " ").slice(0, 120);
    const params = {link_url: u.href, link_text: text, source_page: currentPath()};
    const host = u.hostname.toLowerCase();
    const path = u.pathname.toLowerCase();

    if (host.includes("dmm.co.jp") || host.includes("fanza.co.jp") || host.includes("al.fanza.co.jp") || host.includes("affiliate.dmm.com")) {
      const ctx = pageContext();
      const extra = Object.assign({}, params, ctx, attributionParams(), {
        outbound_domain: host,
        program: "FANZA",
        placement: a.dataset.affiliateTarget || text,
        cta_position: ctaPosition(a),
      });
      sendGa("affiliate_click", extra);
      sendOps("affiliate_click", extra);
      return;
    }

    if (u.origin === location.origin) {
      const internalExtra = Object.assign({}, params, {product_id: a.dataset.productId || ""});
      if (path.startsWith("/sale/")) window.trackOpsEvent("sale_click", internalExtra);
      else if (path.startsWith("/ranking/")) window.trackOpsEvent("ranking_click", internalExtra);
      else if (path.startsWith("/reviews/")) window.trackOpsEvent("review_click", internalExtra);
      else if (path.startsWith("/subscription/")) window.trackOpsEvent("subscription_click", internalExtra);
      else if (path.startsWith("/products/")) {
        rememberOriginContext(pageContext());
        window.trackOpsEvent("product_open", internalExtra);
      } else if (a.classList.contains("cta") || a.classList.contains("money-card") || a.classList.contains("intent-card") || a.classList.contains("mini-card")) {
        window.trackOpsEvent("internal_cta_click", internalExtra);
      }
    }
  }, true);
})();
