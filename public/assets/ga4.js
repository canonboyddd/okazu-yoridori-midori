
(function () {
  const cfg = window.GA4_CONFIG || {};
  const id = (cfg.measurementId || "").trim();

  if (!/^G-[A-Z0-9]+$/i.test(id)) {
    console.info("[GA4] Measurement ID is not configured yet.");
    return;
  }

  window.dataLayer = window.dataLayer || [];
  window.gtag = function(){ dataLayer.push(arguments); };

  const s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
  document.head.appendChild(s);

  gtag("js", new Date());
  gtag("config", id, {
    send_page_view: true,
    debug_mode: !!cfg.debugMode
  });

  function send(name, params) {
    try { gtag("event", name, params || {}); } catch (_) {}
  }

  function currentPath() {
    return location.pathname + location.search;
  }

  let scrolled90 = false;
  window.addEventListener("scroll", function () {
    if (scrolled90) return;
    const doc = document.documentElement;
    const max = Math.max(doc.scrollHeight - window.innerHeight, 1);
    if ((window.scrollY / max) * 100 >= 90) {
      scrolled90 = true;
      send("scroll_90", {
        page_path: currentPath(),
        page_title: document.title
      });
    }
  }, {passive:true});

  document.addEventListener("click", function (e) {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;

    let u;
    try { u = new URL(a.href, location.href); } catch (_) { return; }

    const text = (a.textContent || "").trim().replace(/\s+/g, " ").slice(0, 120);
    const params = {
      link_url: u.href,
      link_text: text,
      source_page: currentPath()
    };

    const host = u.hostname.toLowerCase();
    const path = u.pathname.toLowerCase();

    if (
      host.includes("dmm.co.jp") ||
      host.includes("fanza.co.jp") ||
      host.includes("al.fanza.co.jp") ||
      host.includes("affiliate.dmm.com")
    ) {
      send("affiliate_click", params);
      return;
    }

    if (u.origin === location.origin) {
      if (path.startsWith("/sale/")) send("sale_click", params);
      else if (path.startsWith("/ranking/")) send("ranking_click", params);
      else if (path.startsWith("/reviews/")) send("review_click", params);
      else if (path.startsWith("/subscription/")) send("subscription_click", params);
      else if (
        a.classList.contains("cta") ||
        a.classList.contains("money-card") ||
        a.classList.contains("intent-card") ||
        a.classList.contains("mini-card")
      ) {
        send("internal_cta_click", params);
      }
    }
  }, true);
})();
