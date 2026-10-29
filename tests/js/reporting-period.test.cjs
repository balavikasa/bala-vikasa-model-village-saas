const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function boot({query='',stored='{}',profile=false}={}){
 const listeners={},urls=[],storage={};
 const location={origin:'https://fixture.invalid',pathname:'/coverage',search:query,href:'https://fixture.invalid/coverage'+query,replace:u=>urls.push(u)};
 const anchor={dataset:{},getAttribute:()=>'/coverage?status=pending'};
 const document={querySelectorAll:s=>s==='[data-reporting-period]'?[]:[anchor],querySelector:()=>profile?{}:null,
  addEventListener:(k,f)=>listeners[k]=f,dispatchEvent:e=>listeners[e.type]?.(e)};
 const context={window:{location},location,document,sessionStorage:{getItem:()=>stored,setItem:(k,v)=>storage[k]=v},
  history:{replaceState:(_,__,url)=>{location.href=String(url);}},URL,URLSearchParams,Event:class{constructor(type){this.type=type;}}};
 vm.runInNewContext(fs.readFileSync('app/static/js/reporting-period.js','utf8'),context);
 return {api:context.window.BVReporting,anchor,urls,storage};
}
test('URL period wins over previously stored month',()=>{
 const b=boot({query:'?period=custom&from=2026-09-01&to=2026-09-30',stored:JSON.stringify({period:'today'})});
 assert.equal(b.api.params().get('period'),'custom');assert.equal(b.api.params().get('from'),'2026-09-01');
 assert.equal(new URL(b.anchor.href,'https://fixture.invalid').searchParams.get('status'),'pending');
});
test('switching to Today removes stale month/range parameters',()=>{
 const b=boot({query:'?period=custom&from=2026-09-01&to=2026-09-30'});b.api.set({period:'today'});
 assert.equal(b.api.params().toString(),'period=today');
});
test('server-rendered profile restores saved period by a single scoped navigation',()=>{
 const b=boot({stored:JSON.stringify({period:'month',month:'2026-09'}),profile:true});
 assert.equal(b.urls.length,1);assert.ok(b.urls[0].includes('month=2026-09'));
 const already=boot({query:'?period=month&month=2026-09',profile:true});assert.equal(already.urls.length,0);
});
test('regular data-driven page does not force navigation for saved period',()=>{
 const b=boot({stored:JSON.stringify({period:'last_week'})});assert.equal(b.urls.length,0);assert.equal(b.api.params().get('period'),'last_week');
});
