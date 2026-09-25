
(function(){
  const key='nightchoice_age_ok';
  const modal=document.getElementById('ageModal');
  if(modal && localStorage.getItem(key)!=='1'){ modal.classList.add('show'); }
  const yes=document.getElementById('ageYes');
  if(yes){ yes.addEventListener('click',()=>{localStorage.setItem(key,'1');modal.classList.remove('show');}); }
})();
(()=>{if(window.__opsLoader)return;window.__opsLoader=true;const s=document.createElement('script');s.src='https://factory-career-site.pages.dev/assets/central-tracker.js?v=20260926-2';s.dataset.site='okazu';s.async=true;document.head.appendChild(s);})();
