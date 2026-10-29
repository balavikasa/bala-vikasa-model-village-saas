(() => {
 'use strict';
 const root=document.getElementById('bv-coverage');if(!root)return;
 const $=id=>document.getElementById(id),ui=window.BVUI,esc=window.MV.escapeHtml,period=window.BVReporting;
 const form=$('coverage-filters'),query=new URLSearchParams(location.search);
 let page=Number(query.get('page')||1),status=query.get('status')||'all',token=0,optionsReady=false;
 const keys=['cluster','pc','da','submitted_da','village','committee','q'];
 function args(){const a={status,page,page_size:$('coverage-size').value};keys.forEach(k=>{const value=form.elements.namedItem(k)?.value;if(value)a[k]=value;});return a;}
 function parameters(){return period.params(args());}
 function f(n){return n===null||n===undefined?'\u2014':Number(n).toLocaleString('en-IN');}
 function chip(s){return `<span class="ref-status ${s==='Pending'?'pending':''}">${esc(s)}</span>`;}
 function setOptions(data){const map={cluster:'clusters',pc:'pcs',da:'das',submitted_da:'submitters',village:'villages',committee:'committees'};
   Object.entries(map).forEach(([field,key])=>{const el=form.elements.namedItem(field),value=optionsReady?el.value:query.get(field)||'',label=el.options[0].textContent;el.replaceChildren(new Option(label,''));(data[key]||[]).forEach(item=>el.add(new Option(typeof item==='string'?item:item.name,typeof item==='string'?item:item.id)));if(value&&![...el.options].some(o=>o.value===value))el.add(new Option('Selected filter (unavailable)',value));el.value=value;});
   if(!optionsReady){form.elements.namedItem('q').value=query.get('q')||'';optionsReady=true;}
 }
 function rows(items){
   if(!items.length){$('coverage-rows').innerHTML=ui.empty('No villages match this selection. Change the status, search or period.');return;}
   $('coverage-rows').innerHTML=`<div class="bv-table-scroll bv-desktop-villages"><table class="bv-report-table"><thead><tr><th>Village / cluster</th><th>Assigned DA / PC</th><th>Status</th><th>Visit / last visit</th><th>Submitted by</th><th>Male</th><th>Female</th><th>Total</th><th>New</th><th>Report</th></tr></thead><tbody>${items.map(v=>`<tr><td><strong>${esc(v.name)}</strong><small>${esc(v.cluster)}</small></td><td>${esc(v.assigned_da)}<small>${esc(v.pc)}</small></td><td>${chip(v.status)}</td><td>${esc(v.visit_date||'\u2014')}<small>Last: ${esc(v.last_visit||'No visit')}</small></td><td>${esc(v.submitted_by||'\u2014')}</td><td class="num">${f(v.male)}</td><td class="num">${f(v.female)}</td><td class="num">${f(v.people_attended)}</td><td class="num">${f(v.new_members)}</td><td>${v.report_url?`<a href="${esc(v.report_url)}">Open report</a>`:'\u2014'}</td></tr>`).join('')}</tbody></table></div>
   <div class="bv-mobile-villages">${items.map(v=>`<article class="bv-village-row"><header><strong>${esc(v.name)}</strong>${chip(v.status)}</header><small>${esc(v.cluster)} &middot; ${esc(v.assigned_da)}</small><dl><dt>Visit date</dt><dd>${esc(v.visit_date||'\u2014')}</dd><dt>Last visit</dt><dd>${esc(v.last_visit||'No visit')}</dd><dt>Male / Female</dt><dd>${f(v.male)} / ${f(v.female)}</dd><dt>Total attendances</dt><dd>${f(v.people_attended)}</dd><dt>New members</dt><dd>${f(v.new_members)}</dd><dt>Submitted by</dt><dd>${esc(v.submitted_by||'\u2014')}</dd></dl>${v.report_url?`<a class="button ghost wide" href="${esc(v.report_url)}">Open report</a>`:''}</article>`).join('')}</div>`;
 }
 function table(host,columns,data){$(host).innerHTML=data.length?`<div class="bv-table-scroll"><table class="bv-report-table"><thead><tr>${columns.map(([k,label])=>`<th>${esc(label)}</th>`).join('')}</tr></thead><tbody>${data.map(r=>`<tr>${columns.map(([k])=>`<td>${typeof r[k]==='number'?f(r[k]):esc(r[k]||'\u2014')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:ui.empty('No staff match this scope.');}
 function invalidate(){const id=++token;root.setAttribute('aria-busy','true');['coverage-csv','coverage-excel'].forEach(k=>{$(k).setAttribute('aria-disabled','true');$(k).removeAttribute('href');});$('coverage-prev').disabled=true;$('coverage-next').disabled=true;return id;}
 async function load(){const id=invalidate();$('coverage-error').classList.add('hidden');
   try{let p=parameters();if(!optionsReady)keys.forEach(k=>{if(query.get(k))p.set(k,query.get(k));});
     const response=await window.MV.api('/api/v1/coverage?'+p),data=await response.json();if(id!==token)return;if(!response.ok)throw Error(data.error||'Could not load village coverage.');
     setOptions(data.options||{});const c=data.counts||{},s=data.selection_counts||{};
     root.querySelectorAll('[data-coverage-kpi]').forEach(el=>el.textContent=f(c[el.dataset.coverageKpi]));
     const counts={all:c.villages,done:c.villages_done,pending:c.villages_pending,other:c.other_villages_visited};
     root.querySelectorAll('[data-status-count]').forEach(el=>el.textContent=f(counts[el.dataset.statusCount]));
     root.querySelectorAll('.bv-status-tabs [data-coverage-status]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.coverageStatus===status)));
     $('coverage-period-label').textContent=data.period.label+' | Current active assignments';
     $('coverage-month-pending').textContent=`Monthly context (${data.current_month.month}): ${f(data.current_month.done)} Done / ${f(data.current_month.pending)} Pending.`;
     $('coverage-history-note').textContent=`${f(data.legacy_committee_records)} historical standalone committee records are excluded from complete-village coverage. ${form.elements.submitted_da.value?'Done is restricted to the selected submitting DA.':''}`;
     $('coverage-selection-summary').textContent=`This selection: ${f(s.villages)} villages | ${f(s.visits)} submissions | Male ${f(s.male)} + Female ${f(s.female)} = ${f(s.people_attended)} attendances | ${f(s.new_members)} new members`;
     rows(data.items||[]);
     table('coverage-team',[['name','DA'],['pc','PC'],['assigned','Assigned'],['done',form.elements.submitted_da.value?'Done (selected DA)':'Done (any DA)'],['pending','Pending'],['visits','Actual submissions'],['male','Male'],['female','Female'],['people_attended','Attendances'],['new_members','New members'],['other_visits','Other visits']],data.team||[]);
     table('coverage-months',[['month','Month'],['villages','Active villages'],['done','Done'],['pending','Pending']],data.monthly_coverage||[]);
     $('coverage-page-label').textContent=`Page ${data.page} of ${data.pages} | ${f(data.total)} matching villages`;
     $('coverage-prev').disabled=page<=1;$('coverage-next').disabled=page>=data.pages;
     const final=p;['coverage-csv','coverage-excel'].forEach(k=>{$(k).href=`/coverage/export.${k==='coverage-csv'?'csv':'xlsx'}?${final}`;$(k).setAttribute('aria-disabled','false');});
     history.replaceState({},'',location.pathname+'?'+final);
   }catch(e){if(id!==token)return;$('coverage-error').textContent=e.message;$('coverage-error').classList.remove('hidden');$('coverage-rows').innerHTML=ui.empty('Data unavailable. Apply the filters again to retry.');root.querySelectorAll('[data-coverage-kpi]').forEach(el=>el.textContent='\u2014');$('coverage-selection-summary').textContent='No valid result loaded.';['coverage-team','coverage-months'].forEach(k=>$(k).innerHTML=ui.empty('Data unavailable.'));root.querySelectorAll('[data-status-count]').forEach(el=>el.textContent='');$('coverage-page-label').textContent='';$('coverage-month-pending').textContent='';$('coverage-history-note').textContent='';}
   finally{if(id===token)root.removeAttribute('aria-busy');}
 }
 root.querySelectorAll('[data-coverage-status]').forEach(b=>b.addEventListener('click',()=>{status=b.dataset.coverageStatus;page=1;load();}));
 let timer;form.addEventListener('input',e=>{if(e.target.name==='q'){invalidate();$('coverage-selection-summary').textContent='Updating search...';clearTimeout(timer);timer=setTimeout(()=>{page=1;load();},250);}});
 form.addEventListener('change',e=>{if(e.target.name!=='q'){page=1;load();}});form.addEventListener('submit',e=>{e.preventDefault();page=1;load();});
 form.addEventListener('reset',()=>{setTimeout(()=>{page=1;status='all';load();},0);});
 $('coverage-prev').addEventListener('click',()=>{page--;load();});$('coverage-next').addEventListener('click',()=>{page++;load();});$('coverage-size').addEventListener('change',()=>{page=1;load();});
 document.addEventListener('bv:period-change',()=>{page=1;load();});if(['10','25','50','100'].includes(query.get('page_size')))$('coverage-size').value=query.get('page_size');load();
})();
