(() => {
  'use strict';
  const keys=['period','date','month','year','from','to'];
  const current=new URLSearchParams(window.location.search);
  let state={};
  const explicitPeriod=keys.some(k=>current.has(k));
  if(explicitPeriod){keys.forEach(k=>{if(current.has(k))state[k]=current.get(k);});}
  else {try{state=JSON.parse(sessionStorage.getItem('bv-report-period-v34')||'{}');}catch(_){state={};}}
  if(!state||typeof state!=='object'||Array.isArray(state))state={};
  if(!state.period)state.period=state.month?'month':'this_month';
  const forms=[...document.querySelectorAll('[data-reporting-period]')];
  function params(extra={}){const p=new URLSearchParams();keys.forEach(k=>{if(state[k])p.set(k,state[k]);});Object.entries(extra).forEach(([k,v])=>{if(v!==null&&v!==undefined&&v!=='')p.set(k,v);});return p;}
  function link(path,extra={}){const u=new URL(path,location.origin);keys.forEach(k=>u.searchParams.delete(k));params(extra).forEach((v,k)=>u.searchParams.set(k,v));return u.pathname+u.search+u.hash;}
  function sync(){
    forms.forEach(form=>{keys.forEach(k=>{const f=form.elements.namedItem(k);if(f&&state[k])f.value=state[k];});
      form.querySelectorAll('[data-period-input]').forEach(el=>{el.hidden=!el.dataset.periodInput.split(' ').includes(state.period);el.querySelectorAll('input,select').forEach(input=>input.disabled=el.hidden);});});
    document.querySelectorAll('a[data-report-link]').forEach(a=>{a.dataset.reportBase=a.dataset.reportBase||a.getAttribute('href');a.href=link(a.dataset.reportBase);});
  }
  function set(next,notify=true){state={period:next.period||'this_month'};const fields={day:['date'],week:['date'],month:['month'],year:['year'],custom:['from','to']}[state.period]||[];fields.forEach(k=>{if(next[k])state[k]=next[k];});
    try{sessionStorage.setItem('bv-report-period-v34',JSON.stringify(state));}catch(_){}
    const url=new URL(location.href);keys.forEach(k=>url.searchParams.delete(k));params().forEach((v,k)=>url.searchParams.set(k,v));history.replaceState({},'',url);sync();if(notify)document.dispatchEvent(new Event('bv:period-change'));
  }
  forms.forEach(form=>{
    form.addEventListener('submit',e=>{e.preventDefault();const next=Object.fromEntries(new FormData(form));set(next);});
    form.elements.namedItem('period')?.addEventListener('change',()=>{const key=form.elements.namedItem('period').value;form.querySelectorAll('[data-period-input]').forEach(el=>{el.hidden=!el.dataset.periodInput.split(' ').includes(key);el.querySelectorAll('input,select').forEach(input=>input.disabled=el.hidden);});if(!['custom','day','week','month','year'].includes(key))set({period:key});});
  });
  document.addEventListener('bv:period-change',()=>{if(document.querySelector('[data-profile-period]'))location.reload();});
  window.BVReporting={params,link,set,state:()=>({...state})};sync();
  if(document.querySelector('[data-profile-period]')&&!explicitPeriod&&state.period!=='this_month'){location.replace(link(location.pathname+location.search));}
})();
