(() => {
  'use strict';
  const root=document.getElementById('visit-analytics');
  if(!root||!window.MV||!window.BVUI)return;
  const ui=window.BVUI, $=id=>document.getElementById(id);
  const fields={month:$('analytics-month'),cluster:$('analytics-cluster'),da:$('analytics-da'),village:$('analytics-village'),committee:$('analytics-committee')};
  fields.month.value=root.dataset.month;
  let result=null,token=0;
  const setOptions=(select,rows,label)=>{const current=select.value;select.replaceChildren(new Option(label,''));(rows||[]).forEach(row=>select.add(new Option(typeof row==='string'?row:row.name,typeof row==='string'?row:row.id)));if([...select.options].some(o=>o.value===current))select.value=current;};
  const render=data=>{
    const c=data.counts||{};
    root.querySelectorAll('[data-analytics-kpi]').forEach(el=>el.textContent=ui.fmt(c[el.dataset.analyticsKpi]));
    $('analytics-period').textContent=`${data.period?.label||data.month}: ${ui.fmt(c.visits)} submitted village visits`;
    $('analytics-completion').innerHTML=ui.ring(c.villages_done,c.villages,['Visited','Pending'],'No villages in this scope.',{total:true});
    const male=ui.num(data.gender?.Male),female=ui.num(data.gender?.Female);
    $('analytics-gender').innerHTML=ui.ring(male,male+female,['Male','Female'],'No attendance in this selection.',{gender:true});
    $('analytics-committees').innerHTML=ui.bars(Object.entries(data.committees||{}).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([label,value])=>({label,value})), 'No committee attendance recorded.');
    $('analytics-trend').innerHTML=ui.trend(data.trend);
    $('analytics-das').innerHTML=ui.daChart(data.das);
    const coverage=c.villages?Math.round(100*c.villages_done/c.villages):0;
    const top=Object.entries(data.committees||{}).sort((a,b)=>b[1]-a[1])[0];
    const insights=[
      ['chart',`${coverage}% of villages recorded: ${ui.fmt(c.villages_done)} of ${ui.fmt(c.villages)} in the selected scope.`],
      ['users',`${ui.fmt(c.people_attended)} attendances across ${ui.fmt(c.committees_recorded)} committee records.`],
      ['check',`${ui.fmt(c.new_members)} new members entered as village-wide totals.`],
      ...(top?[['leaf',`${top[0]} recorded the highest participation (${ui.fmt(top[1])} attendances).`]]:[]),
      ['pin',`${ui.fmt(c.villages_pending)} village${c.villages_pending===1?'':'s'} not visited in the selected period.`],
    ];
    $('analytics-insights').innerHTML=insights.map(([glyph,text])=>`<li><span class="ref-insight-icon">${ui.icon(glyph)}</span><span>${ui.esc(text)}</span></li>`).join('');
    $('analytics-pending').innerHTML=(data.pending||[]).slice(0,3).map(v=>`<a href="/directory/village/${Number(v.id)}">${ui.esc(v.name)} &rarr;</a>`).join('');
  };
  const load=async()=>{
    const id=++token;root.setAttribute('aria-busy','true');$('analytics-alert').classList.add('hidden');$('analytics-export').disabled=true;
    const params=window.BVReporting.params();Object.entries(fields).forEach(([key,field])=>{if(key!=='month'&&field.value)params.set(key,field.value);});
    try{
      const response=await window.MV.api(`/api/v1/monitoring/visit-analytics?${params}`);
      if(!response.ok)throw new Error('Unable to load attendance analytics. Please retry or check your access.');
      const data=await response.json();if(id!==token)return;
      if(!result){setOptions(fields.cluster,data.filters?.clusters,'All Clusters');setOptions(fields.da,data.filters?.das,'All DAs');setOptions(fields.village,data.filters?.villages,'All Villages');setOptions(fields.committee,data.filters?.committees,'All Committees');}
      result=data;render(data);$('analytics-export').disabled=false;
      ui.map($('analytics-map'),data.map_items||[]);
      $('analytics-map-note').textContent='Map status uses the same period and filters as these charts. GPS is the captured field location or village master location.';
      document.querySelectorAll('[data-analytics-kpi]').forEach(el=>{const card=el.closest('.ref-metric'),k=el.dataset.analyticsKpi;
        if(card){card.tabIndex=0;card.setAttribute('role','link');card.onclick=()=>{const p=window.BVReporting.params();Object.entries(fields).forEach(([key,f])=>{if(key!=='month'&&f.value)p.set(key,f.value);});p.set('status',k==='villages'?'all':k==='villages_pending'?'pending':'done');location.href='/coverage?'+p;};card.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();card.click();}};}});

    }catch(error){if(id!==token)return;$('analytics-alert').textContent=error.message;$('analytics-alert').classList.remove('hidden');$('analytics-period').textContent='Data unavailable.';
      result=null;
      root.querySelectorAll('[data-analytics-kpi]').forEach(el=>el.textContent='\u2014');
      ['analytics-completion','analytics-gender','analytics-committees','analytics-trend','analytics-das','analytics-map'].forEach(id=>$(id).innerHTML=ui.empty('Data unavailable. Retry this selection.'));
      $('analytics-insights').replaceChildren();$('analytics-pending').replaceChildren();}
    finally{if(id===token)root.removeAttribute('aria-busy');}
  };
  $('analytics-filters').addEventListener('submit',event=>{event.preventDefault();load();});
  Object.values(fields).forEach(field=>field.addEventListener('change',load));
  $('analytics-reset').addEventListener('click',()=>{Object.entries(fields).forEach(([key,field])=>field.value=key==='month'?root.dataset.month:'');load();});
  const csvCell=value=>{let text=String(value??'');if(/^\s*[=+\-@]/.test(text))text="'"+text;return `"${text.replaceAll('"','""')}"`;};
  $('analytics-export').addEventListener('click',()=>{
    if(!result)return;const p=window.BVReporting.params();Object.entries(fields).forEach(([k,f])=>{if(k!=='month'&&f.value)p.set(k,f.value);});location.href='/coverage/export.xlsx?'+p;
  });
  fields.month.addEventListener('change',()=>window.BVReporting.set({period:'month',month:fields.month.value}));
  document.addEventListener('bv:period-change',load);
  load();
})();
