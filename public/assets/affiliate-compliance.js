
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("a[href]").forEach(a => {
    try {
      const u = new URL(a.href, location.href);
      const h = u.hostname.toLowerCase();
      if (
        h.includes("dmm.co.jp") ||
        h.includes("fanza.co.jp") ||
        h.includes("al.fanza.co.jp") ||
        h.includes("affiliate.dmm.com")
      ) {
        const rel = new Set((a.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
        ["sponsored","nofollow","noopener"].forEach(x => rel.add(x));
        a.setAttribute("rel", [...rel].join(" "));
      }
    } catch (_) {}
  });
});
