(() => {
  'use strict';
  const root = document.getElementById('visit-analytics');
  if (!root || !window.MV) return;
  const esc = window.MV.escapeHtml;
  const num = (value) => Math.max(0, Number(value) || 0);
  const fmt = (value) => num(value).toLocaleString('en-IN');
  const $ = (id) => document.getElementById(id);
  const fields = {month: $('analytics-month'), cluster: $('analytics-cluster'),
    da: $('analytics-da'), village: $('analytics-village'), committee: $('analytics-committee')};
  let result = null;
  let loadToken = 0;
  const pageMonth = new Date();
  fields.month.value = `${pageMonth.getFullYear()}-${String(pageMonth.getMonth() + 1).padStart(2, '0')}`;

  const setOptions = (select, rows, fallback) => {
    const selected = select.value;
    select.replaceChildren(new Option(fallback, ''));
    rows.forEach((row) => {
      const id = typeof row === 'string' ? row : String(row.id);
      const title = typeof row === 'string' ? row : row.name;
      select.add(new Option(title, id));
    });
    if ([...select.options].some((option) => option.value === selected)) select.value = selected;
  };
  const empty = (message) => `<p class="analytics-empty">${esc(message)}</p>`;
  const bars = (items, message) => {
    if (!items.length || items.every((item) => num(item.value) === 0)) return empty(message);
    const max = Math.max(1, ...items.map((item) => num(item.value)));
    return `<div class="analytics-bars">${items.map((item) =>
      `<div class="analytics-bar-row"><div><span>${esc(item.label)}</span><strong>${fmt(item.value)}</strong></div><span class="analytics-bar-track"><i style="width:${100 * num(item.value) / max}%"></i></span></div>`).join('')}</div>`;
  };
  const donut = (good, total, labels, words) => {
    if (!total) return empty(words);
    const percent = Math.min(100, (100 * good / total));
    return `<div class="analytics-donut-row"><div class="analytics-donut" style="--percent:${percent}%"><span><strong>${Math.round(percent)}%</strong><small>${esc(labels[0])}</small></span></div><div class="analytics-donut-legend"><span><i></i>${esc(labels[0])}<b>${fmt(good)}</b></span><span><i></i>${esc(labels[1])}<b>${fmt(total - good)}</b></span></div></div>`;
  };
  const trend = (rows) => {
    if (!rows?.length || rows.every((d) => !num(d.visits) && !num(d.people))) return empty('No submitted visits in this six-month window.');
    const width = 620, height = 238, left = 39, right = 14, bottom = 37, top = 16;
    const chartW = width - left - right, chartH = height - top - bottom;
    const max = Math.max(1, ...rows.map((d) => num(d.people)));
    const maxVisits = Math.max(1, ...rows.map((d) => num(d.visits)));
    const step = chartW / rows.length;
    const points = rows.map((d,i) => `${left + step * (i + .5)},${top + chartH - chartH * num(d.people) / max}`).join(' ');
    const labels = rows.map((d,i) => `<text x="${left + step*(i+.5)}" y="${height-7}" text-anchor="middle" font-size="12" fill="#56757e">${esc(d.month.split(' ')[0])}</text>`).join('');
    const columns = rows.map((d,i) => {
      const v = num(d.visits), bh = v / maxVisits * chartH;
      return `<rect x="${left+step*(i+.5)-15}" y="${top+chartH-bh}" width="30" height="${bh}" rx="4" fill="#168b8a"><title>${esc(d.month)}: ${fmt(v)} village visits</title></rect>`;
    }).join('');
    const grid = [0,.25,.5,.75,1].map((n) => `<line x1="${left}" y1="${top+chartH*(1-n)}" x2="${width-right}" y2="${top+chartH*(1-n)}" stroke="#e2eeee"/><text x="${left-7}" y="${top+chartH*(1-n)+4}" text-anchor="end" font-size="11" fill="#66818a">${Math.round(n*maxVisits)}</text>`).join('');
    const circles = rows.map((d,i) => `<circle cx="${left+step*(i+.5)}" cy="${top+chartH - chartH*num(d.people)/max}" r="4" fill="#ed7967"><title>${esc(d.month)}: ${fmt(d.people)} people attended</title></circle>`).join('');
    return `<svg class="analytics-spark" viewBox="0 0 ${width} ${height}" role="img" aria-label="Six month trend. Teal bars show village visits and coral line shows total people attending.">${grid}${columns}<polyline points="${points}" fill="none" stroke="#ed7967" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>${circles}${labels}</svg><div class="analytics-graph-label"><i class="analytics-key"></i>Village visits <i class="analytics-key coral"></i>People attended (line; separate scale) <span>Peak ${fmt(max)} people</span></div>`;
  };
  const table = (rows, columns, emptyMessage) => {
    if (!rows.length) return empty(emptyMessage);
    return `<div class="ledger-table-wrap"><table class="analytics-data-table"><thead><tr>${columns.map(c=>`<th>${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(c=>`<td>${c.format?c.format(row[c.key]):esc(String(row[c.key]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  };
  const render = (data) => {
    root.querySelectorAll('[data-analytics-kpi]').forEach((el) => {
      el.textContent = fmt(data.counts?.[el.dataset.analyticsKpi]);
    });
    $('analytics-period').textContent = `${data.month} · Based on completed village visit submissions · ${fmt(data.counts.visits)} visit${num(data.counts.visits)===1?'':'s'}`;
    $('analytics-completion').innerHTML = donut(num(data.counts.villages_done),num(data.counts.villages),['Visited','Not visited'],'No villages are available in this scope.');
    $('analytics-gender').innerHTML = donut(num(data.gender.Male),num(data.counts.people_attended),['Male','Female'],'No attendance recorded for this selection.');
    $('analytics-trend').innerHTML = trend(data.trend);
    $('analytics-committees').innerHTML = bars(Object.entries(data.committees||{}).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([label,value])=>({label,value})), 'No committee attendance recorded.');
    $('analytics-clusters').innerHTML = data.clusters?.length
      ? bars(data.clusters.map(c => ({label:`${c.name}: ${c.done} of ${c.total}`,value:c.done})), 'No villages visited in these clusters.')
      : empty('No clusters are available for this selection.');
    $('analytics-das').innerHTML = table(data.das.slice(0,9),[{key:'name',label:'Development Associate'},{key:'villages',label:'Villages'},{key:'people',label:'People',format:fmt}], 'No DA visits in the selected month.');
    $('analytics-pending').innerHTML = !data.pending.length ? empty('All villages in this scope have been visited this month.')
      : `<div class="analytics-pending-list">${data.pending.map((v) => `<a href="/directory/village/${Number(v.id)}" class="analytics-pending-link"><span><strong>${esc(v.name)}</strong><small>${esc(v.cluster)}</small></span><span>View village ↗</span></a>`).join('')}</div>`;
    const coverage = data.counts.villages ? Math.round(100*data.counts.villages_done/data.counts.villages):0;
    const more = data.counts.villages_pending > data.pending.length ? `${fmt(data.counts.villages_pending - data.pending.length)} more pending villages in this filter.` : '';
    $('analytics-insights').innerHTML = [
      `${coverage}% village coverage: ${fmt(data.counts.villages_done)} of ${fmt(data.counts.villages)} villages visited.`,
      `${fmt(data.counts.people_attended)} people attended across ${fmt(data.counts.committees_recorded)} committee records.`,
      `${fmt(data.counts.new_members)} new members entered as village-wide totals.`,
      more,
    ].filter(Boolean).map(text=>`<li>${esc(text)}</li>`).join('');
  };
  const fetchData = async (withOptions = false) => {
    const token=++loadToken;
    $('analytics-alert').classList.add('hidden');
    $('analytics-period').textContent='Loading attendance analytics…';
    const query = new URLSearchParams();
    for (const [key,field] of Object.entries(fields)) if (field.value) query.set(key,field.value);
    try {
      const res=await window.MV.api(`/api/v1/monitoring/visit-analytics?${query.toString()}`);
      if (!res.ok) throw new Error('Analytics data could not be loaded. Check your access and try again.');
      const data=await res.json();
      if (token!==loadToken) return;
      if(withOptions || !result) {
        setOptions(fields.cluster,data.filters.clusters,'All clusters');
        setOptions(fields.da,data.filters.das,'All DAs');
        setOptions(fields.village,data.filters.villages,'All villages');
        setOptions(fields.committee,data.filters.committees,'All committees');
      }
      result=data; render(data);
    } catch(error) {
      if (token!==loadToken) return;
      $('analytics-period').textContent='Unable to load live data.';
      $('analytics-alert').textContent=error.message;
      $('analytics-alert').classList.remove('hidden');
    }
  };
  $('analytics-filters').addEventListener('submit',(e)=>{e.preventDefault();fetchData();});
  Object.values(fields).forEach((field)=>field.addEventListener('change',()=>fetchData()));
  $('analytics-reset').addEventListener('click',()=>{
    fields.cluster.value=''; fields.da.value=''; fields.village.value=''; fields.committee.value='';
    fields.month.value=`${pageMonth.getFullYear()}-${String(pageMonth.getMonth()+1).padStart(2,'0')}`;
    fetchData();
  });
  const csvCell = (value) => {
    let t=String(value??'');
    if (/^[\s]*[=+\-@]/.test(t)) t=`'${t}`;
    return `"${t.replaceAll('"','""')}"`;
  };
  $('analytics-export').addEventListener('click',()=>{
    if(!result) return;
    const records=[['Section','Name','Villages','People','Visits']];
    for (const row of result.das) records.push(['DA',row.name,row.villages,row.people,row.visits]);
    for (const row of result.clusters) records.push(['Cluster',row.name,row.done,'',row.total]);
    for (const [name,people] of Object.entries(result.committees)) records.push(['Committee',name,'',people,'']);
    for (const row of result.trend) records.push(['Month',row.month,row.villages,row.people,row.visits]);
    const blob = new Blob([`\uFEFF${records.map(r=>r.map(csvCell).join(',')).join('\r\n')}\r\n`],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');
    a.href=url;a.download=`BV_Village_Analytics_${result.month}.csv`;
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  fetchData(true);
})();
