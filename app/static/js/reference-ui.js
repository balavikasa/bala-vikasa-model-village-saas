/* Shared, dependency-free presentation for the reference design. No sample data. */
(() => {
  'use strict';
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = (v) => Math.max(0, Number(v) || 0);
  const fmt = (v) => num(v).toLocaleString('en-IN');
  const paths = {
    home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-9h6v9"/>',
    users:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 4v3"/>',
    check:'<path d="m5 12 4 4L19 6"/>', chart:'<path d="M5 21V12m7 9V3m7 18V8"/>',
    pin:'<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    leaf:'<path d="M20 3C7 1 1 7 5 15s17 7 15-12Z"/><path d="M4 21 16 9M9 16v-5m0 5h5"/>',
    heart:'<path d="M20 5a5 5 0 0 0-8 1 5 5 0 0 0-8-1c-5 5 8 15 8 15S25 10 20 5Z"/>',
    water:'<path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z"/>',
    gear:'<circle cx="12" cy="12" r="3"/><path d="m9 3-1 3-3 1-2 3 2 3-1 3 3 2 3-1 3 2 3-2 1-3 3-1v-4l-3-1-1-3-3-1-3 1Z"/>',
    building:'<path d="m2 8 10-6 10 6ZM4 11v8m5-8v8m6-8v8m5-8v8M2 22h20"/>',
    light:'<path d="M9 18h6m-5 3h4M8 15a7 7 0 1 1 8 0l-1 3H9Z"/>',
    report:'<path d="M6 2h8l5 5v15H5V2Zm8 0v6h5M8 12h8m-8 4h8"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  };
  const icon = (name) => `<svg class="ref-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.users}</svg>`;
  const empty = (text) => `<div class="ref-empty">${icon('chart')}<p>${esc(text)}</p></div>`;
  const ring = (good, total, labels = ['Visited','Not visited'], message='No records in this scope.', options={}) => {
    total=num(total); good=Math.min(total,num(good));
    if (!total) return empty(message);
    const percent=Math.round(100*good/total), remaining=total-good;
    return `<div class="ref-ring-row"><div class="ref-ring ${options.gender?'ref-ring-gender':''}" style="--fill:${percent}%" role="img" aria-label="${esc(labels[0])}: ${fmt(good)} of ${fmt(total)}"><span><strong>${options.total?fmt(total):percent+'%'}</strong><small>${esc(options.total?'Total villages':labels[0])}</small></span></div><div class="ref-ring-legend"><div><i></i><span><strong>${fmt(good)}</strong><small>${esc(labels[0])}<br>(${percent}%)</small></span></div><div><i></i><span><strong>${fmt(remaining)}</strong><small>${esc(labels[1])}<br>(${100-percent}%)</small></span></div></div></div>`;
  };
  const bars = (items, message='No attendance recorded.', options={}) => {
    if (!items?.length || items.every(item=>!num(item.value))) return empty(message);
    const max=Math.max(1,...items.map(item=>num(item.value)));
    return `<div class="ref-bars">${items.map((item,i)=>`<div class="ref-bar-row"><span title="${esc(item.label)}">${esc(item.label)}</span><div class="ref-bar-track"><i class="ref-bar-fill ref-bar-tone-${i%6}" style="width:${Math.min(100,100*num(item.value)/(options.percent?100:max))}%"></i></div><strong>${fmt(item.value)}${options.percent?'%':''}</strong></div>`).join('')}</div>`;
  };
  const niceMax=(n)=> {if(n<=4)return 4;const step=10**Math.floor(Math.log10(n));return Math.ceil(n/step)*step;};
  const trend=(rows, opts={})=>{
    if(!rows?.length || rows.every(row=>!num(row.visits)&&!num(row.people))) return empty('No submitted visits in this period.');
    const w=640,h=190,l=38,r=50,t=19,b=39,cw=w-l-r,ch=h-t-b;
    const mv=niceMax(Math.max(1,...rows.map(row=>num(row.visits))));
    const mp=niceMax(Math.max(1,...rows.map(row=>num(row.people))));
    const step=cw/rows.length;
    const grid=[0,.25,.5,.75,1].map(f=>`<line x1="${l}" y1="${t+ch*(1-f)}" x2="${w-r}" y2="${t+ch*(1-f)}" stroke="#e9eeeb"/><text x="${l-9}" y="${t+ch*(1-f)+4}" text-anchor="end">${Math.round(mv*f)}</text><text x="${w-r+9}" y="${t+ch*(1-f)+4}">${Math.round(mp*f)}</text>`).join('');
    const columns=rows.map((row,i)=>{const bh=ch*num(row.visits)/mv;return `<rect x="${l+step*(i+.2)}" y="${t+ch-bh}" width="${Math.max(3,step*.57)}" height="${bh}" rx="2" fill="#168a88"><title>${esc(row.month||row.date||row.label)}: ${fmt(row.visits)} visits</title></rect>`;}).join('');
    const points=rows.map((row,i)=>`${l+step*(i+.5)},${t+ch-ch*num(row.people)/mp}`).join(' ');
    const dots=rows.map((row,i)=>`<circle cx="${l+step*(i+.5)}" cy="${t+ch-ch*num(row.people)/mp}" r="3.6" fill="#fb7b68"><title>${esc(row.month||row.date||row.label)}: ${fmt(row.people)} attendances</title></circle>`).join('');
    const labels=rows.map((row,i)=>`<text x="${l+step*(i+.5)}" y="${h-13}" text-anchor="middle">${esc((row.label||row.month||row.date||'').split(' ')[0])}</text>`).join('');
    return `<svg class="ref-svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Visits and attendance trend. Visits use the left axis; attendance uses the right axis.">${grid}${columns}<polyline points="${points}" fill="none" stroke="#fb7b68" stroke-width="2"/>${dots}${labels}<text x="${l}" y="10">Visits</text><text x="${w-r}" y="10" text-anchor="end">Attendances</text></svg>`;
  };
  const daChart=(rows)=>{
    if(!rows?.length || rows.every(row=>!num(row.villages)&&!num(row.people)))return empty('No DA submissions in this period.');
    const data=rows.slice(0,6),w=600,h=190,l=36,r=48,t=17,b=48,cw=w-l-r,ch=h-t-b;
    const vm=niceMax(Math.max(1,...data.map(d=>num(d.villages))));
    const pm=niceMax(Math.max(1,...data.map(d=>num(d.people)))); const step=cw/data.length;
    let svg=[0,.25,.5,.75,1].map(f=>`<line x1="${l}" y1="${t+ch*(1-f)}" x2="${w-r}" y2="${t+ch*(1-f)}" stroke="#e9eeeb"/><text x="${l-7}" y="${t+ch*(1-f)+4}" text-anchor="end">${Math.round(vm*f)}</text><text x="${w-r+8}" y="${t+ch*(1-f)+4}">${Math.round(pm*f)}</text>`).join('');
    svg+=data.map((d,i)=>{const x=l+step*(i+.23);return `<rect x="${x}" y="${t+ch-ch*num(d.villages)/vm}" width="${step*.25}" height="${ch*num(d.villages)/vm}" rx="2" fill="#168a88"/><rect x="${x+step*.29}" y="${t+ch-ch*num(d.people)/pm}" width="${step*.25}" height="${ch*num(d.people)/pm}" rx="2" fill="#fb7b68"/><text x="${l+step*(i+.5)}" y="${h-21}" text-anchor="middle">${esc(d.name.length>17?d.name.slice(0,16)+'...':d.name)}</text><title>${esc(d.name)}: ${fmt(d.villages)} villages, ${fmt(d.people)} attendances</title>`;}).join('');
    return `<svg class="ref-svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="DA contributions. Villages use the left axis, attendances use the right axis.">${svg}</svg>`;
  };
  const coordinates=(latitude,longitude)=>{
    if(latitude==null||longitude==null||String(latitude).trim()===''||String(longitude).trim()==='')return null;
    const lat=Number(latitude),lng=Number(longitude);
    return Number.isFinite(lat)&&Number.isFinite(lng)&&Math.abs(lat)<=90&&Math.abs(lng)<=180 ? {lat,lng} : null;
  };
  const project=(lat,lng,z)=>{const p=Math.max(-85.05112878,Math.min(85.05112878,lat))*Math.PI/180,n=256*2**z;return{x:(lng+180)/360*n,y:(1-Math.log(Math.tan(p)+1/Math.cos(p))/Math.PI)/2*n};};
  const map=(element,rows,options={})=>{
    if(!element)return;
    const valid=(rows||[]).map(row=>({...row,point:coordinates(row.latitude,row.longitude)})).filter(row=>row.point);
    if(!valid.length){element.innerHTML=empty('No captured GPS locations available.');return;}
    let zoom=options.zoom||10;
    const center={lat:valid.reduce((s,v)=>s+v.point.lat,0)/valid.length,lng:valid.reduce((s,v)=>s+v.point.lng,0)/valid.length};
    const draw=()=>{
      const width=Math.max(250,element.clientWidth),height=Math.max(175,element.clientHeight),c=project(center.lat,center.lng,zoom);
      const left=c.x-width/2,top=c.y-height/2;
      let tiles='';
      for(let tx=Math.floor(left/256);tx<=Math.floor((left+width)/256);tx++)for(let ty=Math.floor(top/256);ty<=Math.floor((top+height)/256);ty++){
        const n=2**zoom;if(ty<0||ty>=n)continue;
        tiles+=`<img class="ref-map-tile" alt="" aria-hidden="true" src="https://tile.openstreetmap.org/${zoom}/${((tx%n)+n)%n}/${ty}.png" style="left:${tx*256-left}px;top:${ty*256-top}px" loading="lazy" referrerpolicy="strict-origin-when-cross-origin">`;
      }
      const markers=valid.map(row=>{const p=project(row.point.lat,row.point.lng,zoom),x=p.x-left,y=p.y-top;
        if(x < -15||x>width+15||y< -15||y>height+15)return '';
        const visited=row.status==='Visited'||row.visited||row.last_visit_date;
        const href=row.url||(row.id?`/directory/village/${Number(row.id)}`:`https://www.openstreetmap.org/?mlat=${row.point.lat}&mlon=${row.point.lng}#map=16/${row.point.lat}/${row.point.lng}`);
        return `<a class="ref-map-pin ${visited?'visited':'pending'}" style="left:${x}px;top:${y}px" href="${esc(href)}" title="${esc(row.name||'Captured GPS location')}${row.last_visit_date?' - '+esc(row.last_visit_date):''}" aria-label="${esc(row.name||'Captured GPS location')}"><span></span></a>`;
      }).join('');
      element.innerHTML=`<div class="ref-tile-layer">${tiles}</div><div class="ref-map-offline" hidden>Map tiles unavailable. Captured locations remain in the reports.</div>${markers}<div class="ref-map-controls"><button type="button" data-map-zoom="1" aria-label="Zoom in">+</button><button type="button" data-map-zoom="-1" aria-label="Zoom out">&#8722;</button></div><div class="ref-map-legend"><span><i></i>Visited</span><span><i></i>Not visited</span></div><a class="ref-map-attribution" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">&copy; OpenStreetMap contributors</a>`;
      element.querySelectorAll('[data-map-zoom]').forEach(button=>button.addEventListener('click',()=>{zoom=Math.min(17,Math.max(3,zoom+Number(button.dataset.mapZoom)));draw();}));
      let loaded=0,failed=0;const imgs=element.querySelectorAll('.ref-map-tile');
      imgs.forEach(img=>{img.addEventListener('load',()=>{loaded++;});img.addEventListener('error',()=>{img.style.visibility='hidden';failed++;if(failed===imgs.length&&!loaded){element.querySelector('.ref-map-offline').hidden=false;}});});
    };
    const width=element.clientWidth||400,height=element.clientHeight||230;
    if(!options.zoom&&valid.length>1){for(zoom=13;zoom>3;zoom--){const ps=valid.map(v=>project(v.point.lat,v.point.lng,zoom));if(Math.max(...ps.map(p=>p.x))-Math.min(...ps.map(p=>p.x))<width*.78&&Math.max(...ps.map(p=>p.y))-Math.min(...ps.map(p=>p.y))<height*.75)break;}}
    draw();
  };
  window.BVUI={esc,num,fmt,icon,empty,ring,bars,trend,daChart,coordinates,map};
  document.querySelectorAll('[data-print-report]').forEach(button=>button.addEventListener('click',()=>window.print()));
  document.querySelectorAll('[data-single-map]').forEach(el=>map(el,[{name:el.dataset.label,latitude:el.dataset.latitude,longitude:el.dataset.longitude,visited:true}],{zoom:14}));
  document.querySelectorAll('[data-evidence-photo]').forEach(img=>img.addEventListener('error',()=>{const fallback=document.createElement('p');fallback.className='ref-empty';fallback.textContent='Evidence photo unavailable. The submitted record is preserved.';img.replaceWith(fallback);}));
  const profile=document.getElementById('profile-visual-data');
  if(profile){try{const data=JSON.parse(profile.textContent);document.getElementById('profile-trend').innerHTML=trend(data.trend);document.getElementById('profile-coverage').innerHTML=ring(data.done,data.total,['Recorded','Not recorded'],'No active committees.');}catch(error){console.error('Village chart data unavailable',error);}}
  const note=document.getElementById('village-notes'),counter=document.getElementById('visit-note-count');
  if(note&&counter){const count=()=>{counter.textContent=`${note.value.length}/500`;};note.addEventListener('input',count);count();}
})();
