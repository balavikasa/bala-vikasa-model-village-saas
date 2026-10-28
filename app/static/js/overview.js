(() => {
  'use strict';
  const root=document.getElementById('ref-dashboard');
  if(!root||!window.MV||!window.BVUI)return;
  const ui=window.BVUI,$=id=>document.getElementById(id);
  async function get(path){const response=await window.MV.api(path);if(!response.ok)throw new Error('Dashboard data is unavailable. Please refresh or check your connection.');return response.json();}
  async function load(){
    try{
      const [data,activity]=await Promise.all([get('/api/v1/dashboard/series'),get('/api/v1/monitoring/recent')]);
      const c=data.counts||{};
      root.querySelectorAll('[data-kpi]').forEach(el=>el.textContent=ui.fmt(c[el.dataset.kpi]));
      $('dashboard-coverage').innerHTML=ui.ring(c.villages_done,c.villages,['Visited','Pending'],'No assigned villages yet.');
      $('dashboard-coverage-note').textContent=`${ui.fmt(c.villages_pending)} villages remaining in your assigned scope.`;
      $('dashboard-trend').innerHTML=ui.trend(data.daily_trend||[]);
      $('dashboard-gender').innerHTML=ui.bars(Object.entries(data.gender_distribution||{}).map(([label,value])=>({label,value})), 'No attendance recorded this month.');
      const totalByCluster=data.cluster_breakdown||{};
      $('dashboard-clusters').innerHTML=ui.bars(Object.keys(totalByCluster).map(name=>({label:`${name} (${data.status_by_cluster?.[name]?.Done||0}/${totalByCluster[name]})`,value:data.status_by_cluster?.[name]?.Done||0})), 'No village visits recorded in these clusters.');
      const recent=activity.recent||[],pending=activity.pending||[];
      $('renewal-recent-visits').innerHTML=recent.length?recent.slice(0,5).map(v=>`<a class="ref-list-row" href="/reports/village/${Number(v.id)}"><span class="ref-list-icon">${ui.icon('users')}</span><span class="ref-list-name"><strong>${ui.esc(v.village)}</strong><small>${ui.esc(v.date)}${v.outside_assignment?' &middot; Other village':''}</small></span><span class="ref-list-value">${ui.fmt(v.people)} people</span><span class="ref-status">Recorded</span><span aria-hidden="true">&rsaquo;</span></a>`).join(''):ui.empty('No attendance submissions yet.');
      $('renewal-pending-villages').innerHTML=pending.length?pending.slice(0,5).map(v=>`<a class="ref-list-row" href="/directory/village/${Number(v.id)}"><span class="ref-list-icon coral">${ui.icon('pin')}</span><span class="ref-list-name"><strong>${ui.esc(v.name)}</strong><small>Not recorded this month</small></span><span class="ref-status pending">Pending</span></a>`).join(''):ui.empty('No pending villages in this scope.');
      try{const payload=await get('/api/v1/monitoring/map');ui.map($('dashboard-map'),payload.items||payload.markers||[]);}catch(_){$('dashboard-map').innerHTML=ui.empty('Map unavailable. Open Map to retry.');}
    }catch(error){$('dashboard-error').textContent=error.message;$('dashboard-error').classList.remove('hidden');}
  }
  load();
})();
