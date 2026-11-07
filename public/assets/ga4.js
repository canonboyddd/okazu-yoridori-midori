(function () {
  if(window.__okazuRevenueAnalytics)return;window.__okazuRevenueAnalytics=true;
  // Apply the same exclusion before both GA4 and first-party collection.
  const blocked=()=>navigator.webdriver===true||/bot|crawler|spider|slurp|preview|inspection|lighthouse|pagespeed|headless|phantom|selenium|puppeteer|playwright|uptime|pingdom|monitor|revenueqa/i.test(navigator.userAgent||'')||new URLSearchParams(location.search).get('ops_qa')==='1'||new URLSearchParams(location.search).get('qa')==='1'||/(?:^|;\s*)ops_owner_excluded=1(?:;|$)/.test(document.cookie||'')||(()=>{try{return localStorage.getItem('ops_owner_excluded')==='1'}catch{return false}})();
  if(blocked()){window.trackOpsEvent=()=>{};return;}

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
    gtag("config", id, {send_page_view: false, debug_mode: !!cfg.debugMode, allow_google_signals:false,page_location:location.origin+currentPath(),page_referrer:referrerHost()});
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

  function currentPath() { return location.pathname; }
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
    if (path.startsWith("/products/view")) { ctx.page_type = "product"; const id=new URLSearchParams(location.search).get("id")||'';ctx.product_id=/^[A-Za-z0-9_-]{1,120}$/.test(id)?id:''; }
    if (/^\/products\/?$/.test(path)) ctx.page_type='catalog';
    if (path.startsWith('/subscription')) ctx.page_type='subscription';
    if (path.startsWith('/fc2-adult')) ctx.page_type='fc2';
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
    if (!hasGa || blocked()) return;
    const allowed={};for(const key of ['page_type','product_id','provider','program','placement','cta_position','outbound_domain','device_type','variant','result_count','origin_page_type'])if(params?.[key]!=null)allowed[key]=safeDimension(params[key]);
    allowed.page_location=location.origin+currentPath();allowed.page_referrer=referrerHost();
    try { gtag("event", name, allowed); } catch (_) {}
  }

  function safeDimension(value){if(typeof value==='number')return Number.isSafeInteger(value)&&value>=0?value:0;const text=String(value||'');return /@|CM-[A-F0-9]{48}|eyJ[A-Za-z0-9_-]+\./i.test(text)?'':text.replace(/[^a-zA-Z0-9_.:/|+-]/g,'-').slice(0,160)}


  // D1 analytics only; keep GA4 behavior separate.
  function skipOpsAnalytics() {
    if (navigator.webdriver === true || /bot|crawler|spider|slurp|bingpreview|google-inspectiontool|lighthouse|pagespeed|headless|phantom|selenium|puppeteer|playwright|facebookexternalhit|twitterbot|linkedinbot|discordbot|uptimerobot|pingdom|monitor/i.test(String(navigator.userAgent || ""))) return true;
    try { if (localStorage.getItem("ops_owner_excluded") === "1") return true; } catch (_) {}
    return /(?:^|;\s*)ops_owner_excluded=1(?:;|$)/.test(document.cookie || "");
  }

  function sendOps(name, extra) {
    if (blocked() || skipOpsAnalytics()) return;
    const ctx = pageContext();
    const dimensions={};
    for(const key of ['provider','program','placement','cta_position','outbound_domain','variant','result_count','product_id','origin_page_path','origin_page_type'])if(extra?.[key]!=null)dimensions[key]=safeDimension(extra[key]);
    const payload = Object.assign({
      event_name: name,
      browser_id: browserId,
      session_id: sessionId,
      page_path: currentPath(),
      referrer: referrerHost(),
      device_type: deviceType(),
      provider: "",
      page_type: ctx.page_type,
      product_id: ctx.product_id,
    }, dimensions);
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

  function referrerHost(){try{return document.referrer?new URL(document.referrer).hostname:''}catch{return ''}}
  const initialCtx = pageContext();
  sendGa('page_view',initialCtx);
  let detailSeen=false,listSeen=false;
  function contentViews(){
    if(document.visibilityState!=='visible'||document.getElementById('ageModal')?.classList.contains('show'))return;
    const ctx=pageContext();
    if(!listSeen&&['home','catalog','ranking','actress','genre','maker','sale','search','subscription','fc2'].includes(ctx.page_type)&&document.querySelector('main h1')){listSeen=true;sendOps('catalog_list_view',{});sendGa('catalog_list_view',ctx)}
    if(!detailSeen&&ctx.page_type==='product'&&document.querySelector('.fc-detail h1')){detailSeen=true;sendOps('product_detail_view',{});sendGa('product_detail_view',ctx)}
  }
  new MutationObserver(contentViews).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
  document.addEventListener('visibilitychange',contentViews);contentViews();
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

  function affiliateProvider(a){try{const host=new URL(a.href,location.href).hostname.toLowerCase();if(['al.dmm.co.jp','al.dmm.com','al.fanza.co.jp','al.fanza.com'].includes(host))return 'FANZA';if(host==='cnt.affiliate.fc2.com')return 'FC2';}catch{}return '';}
  const impressionSeen=new Set(),timers=new Map();
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(entries=>{for(const entry of entries){const a=entry.target;clearTimeout(timers.get(a));timers.delete(a);
      if(!entry.isIntersecting||entry.intersectionRatio<.5||document.visibilityState!=='visible'||document.getElementById('ageModal')?.classList.contains('show'))continue;
      timers.set(a,setTimeout(()=>{timers.delete(a);if(document.visibilityState!=='visible'||document.getElementById('ageModal')?.classList.contains('show'))return;const provider=affiliateProvider(a),position=ctaPosition(a),key=provider+'|'+position+'|'+a.href;if(!provider||impressionSeen.has(key))return;impressionSeen.add(key);const extra={provider,program:provider,placement:position,cta_position:position};sendOps('affiliate_impression',extra);sendGa('affiliate_impression',extra);io.unobserve(a)},1000));
    }},{threshold:[0,.5]});
    const scan=()=>document.querySelectorAll('a[href]').forEach(a=>{if(affiliateProvider(a)&&!a.dataset.revenueObserved){a.dataset.revenueObserved='1';io.observe(a)}});
    new MutationObserver(scan).observe(document.body,{subtree:true,childList:true});scan();
    document.getElementById('ageYes')?.addEventListener('click',()=>{document.querySelectorAll('a[data-revenue-observed]').forEach(a=>{io.unobserve(a);io.observe(a)})});
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState!=='visible'){for(const t of timers.values())clearTimeout(t);timers.clear()}else document.querySelectorAll('a[data-revenue-observed]').forEach(a=>{io.unobserve(a);io.observe(a)})});
  }
  function onClick(e) {
    if(!e.isTrusted||(e.type==='auxclick'&&e.button!==1))return;
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;

    let u;
    try { u = new URL(a.href, location.href); } catch (_) { return; }

    const text = (a.textContent || "").trim().replace(/\s+/g, " ").slice(0, 120);
    const params = {link_url: u.href, link_text: text, source_page: currentPath()};
    const host = u.hostname.toLowerCase();
    const path = u.pathname.toLowerCase();

    if (affiliateProvider(a)) {
      const ctx = pageContext();
      const extra = Object.assign({}, params, ctx, attributionParams(), {
        outbound_domain: host,
        program: affiliateProvider(a),
        provider: affiliateProvider(a),
        placement: ctaPosition(a),
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
  }
  document.addEventListener("click",onClick,true);
  document.addEventListener("auxclick",onClick,true);
})();

