
(function(){
  const key='nightchoice_age_ok';
  const modal=document.getElementById('ageModal');
  if(modal && localStorage.getItem(key)!=='1'){ modal.classList.add('show'); }
  const yes=document.getElementById('ageYes');
  if(yes){ yes.addEventListener('click',()=>{localStorage.setItem(key,'1');modal.classList.remove('show');}); }
})();

(()=>{
  if(window.__okazuCentralTracking)return;
  window.__okazuCentralTracking=true;
  const endpoint='https://factory-career-site.pages.dev/api/central/collect';
  const uuid=()=>crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random().toString(36).slice(2)}`;
  let browser='';let session='';
  try{browser=localStorage.getItem('okazu_ops_browser')||'';if(!browser){browser=uuid();localStorage.setItem('okazu_ops_browser',browser)}}catch{browser=uuid()}
  try{session=sessionStorage.getItem('okazu_ops_session')||'';if(!session){session=uuid();sessionStorage.setItem('okazu_ops_session',session)}}catch{session=uuid()}
  const device=/Mobi|Android/i.test(navigator.userAgent)?'mobile':(/Tablet|iPad/i.test(navigator.userAgent)?'tablet':'desktop');
  const pending=[];
  function send(eventName,extra={}){
    try{
      const q=new URLSearchParams({site_key:'okazu',event_name:eventName,browser_id:browser,session_id:session,page_path:location.pathname,page_title:document.title,referrer:document.referrer||'',device_type:device,program:extra.program||'',placement:extra.placement||'',outbound_domain:extra.outbound_domain||''});
      const img=new Image(1,1);pending.push(img);img.onload=img.onerror=()=>{const i=pending.indexOf(img);if(i>=0)pending.splice(i,1)};img.src=endpoint+'?'+q.toString();
    }catch{}
  }
  send('page_view');
  document.addEventListener('click',e=>{
    const a=e.target.closest('a[href]');if(!a)return;
    let u;try{u=new URL(a.href,location.href)}catch{return}
    if(u.origin===location.origin)return;
    const href=u.href;let program='';
    if(/affiliate\.dmm|dmm\.co\.jp|fanza/i.test(href))program='dmm-fanza';
    else if(/afi-b\.com|afb/i.test(href))program='afb';
    else if(/accesstrade/i.test(href))program='accesstrade';
    else if(/fc2/i.test(href))program='fc2';
    else if(/rakuten/i.test(href))program='rakuten';
    else if(/a8\.net|px\.a8\.net/i.test(href))program='a8';
    if(program)send('affiliate_click',{program,placement:(a.textContent||a.getAttribute('aria-label')||'').trim().slice(0,160),outbound_domain:u.hostname});
  },{capture:true});
})();
