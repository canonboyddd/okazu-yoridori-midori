
(function(){
  const key='nightchoice_age_ok';
  const modal=document.getElementById('ageModal');
  if(modal && localStorage.getItem(key)!=='1'){ modal.classList.add('show'); }
  const yes=document.getElementById('ageYes');
  if(yes){ yes.addEventListener('click',()=>{localStorage.setItem(key,'1');modal.classList.remove('show');}); }
})();
