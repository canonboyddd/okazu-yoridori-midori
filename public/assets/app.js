
(function(){
  const key='nightchoice_age_ok';
  const information=/^\/(?:about|privacy|editorial-policy)(?:\.html)?\/?$/.test(location.pathname);
  let modal=document.getElementById('ageModal');
  // Several generated directory/search footers omit the shared dialog. Direct
  // entry to those pages must have the same age restriction as product pages.
  if(!modal&&!information){
    modal=document.createElement('div');modal.id='ageModal';modal.className='age-modal';modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-labelledby','ageQuestion');
    modal.innerHTML='<div class="age-box"><h2 id="ageQuestion">18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes" type="button">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div><p class="small">年齢確認はこのブラウザ内に保存されます。</p></div>';
    document.body.appendChild(modal);
  }
  let accepted=false;try{accepted=localStorage.getItem(key)==='1'}catch{}
  const locked=new Map();let originalOverflow='';
  function lock(node){if(node instanceof HTMLElement&&node!==modal&&!['SCRIPT','STYLE','LINK'].includes(node.tagName)){if(!locked.has(node))locked.set(node,node.inert);node.inert=true}}
  if(modal&&!information&&!accepted){
    modal.classList.add('show');modal.style.zIndex='100000';originalOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
    [...document.body.children].forEach(lock);
    const additions=new MutationObserver(records=>{if(!modal.classList.contains('show'))return additions.disconnect();for(const record of records)for(const node of record.addedNodes)lock(node)});
    additions.observe(document.body,{childList:true});
    modal.querySelector('button')?.focus();
  }
  const yes=document.getElementById('ageYes');
  if(yes){ yes.addEventListener('click',()=>{try{localStorage.setItem(key,'1')}catch{}modal.classList.remove('show');document.body.style.overflow=originalOverflow;for(const [node,wasInert] of locked)node.inert=wasInert;locked.clear();}); }
})();
