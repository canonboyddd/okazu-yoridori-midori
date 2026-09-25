
document.addEventListener('DOMContentLoaded', () => {
  const q = document.querySelector('#siteSearch');
  const cards = [...document.querySelectorAll('.content-card')];
  const empty = document.querySelector('.site-search-empty');
  if (q && cards.length) {
    q.addEventListener('input', () => {
      const needle = q.value.trim().toLowerCase();
      let shown = 0;
      cards.forEach(card => {
        const ok = !needle || card.textContent.toLowerCase().includes(needle);
        card.classList.toggle('hidden', !ok);
        if (ok) shown++;
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
    });
  }
  const cfg = window.AFFILIATE_CONFIG || {};
  if (cfg.approved && cfg.affiliateId) {
    document.querySelectorAll('.affiliate-slot').forEach(el => el.style.display = 'block');
  }
});
