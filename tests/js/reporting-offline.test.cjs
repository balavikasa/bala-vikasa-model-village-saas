const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('app/static/sw.js','utf8');
function boot(){
 let cachedReads=0;const handlers={};
 const context={importScripts(){},URL,Response,Request,fetch:async()=>{throw Error('offline')},
  caches:{match:async()=>{cachedReads++;return new Response('{"counts":{"villages_pending":99}}');}},
  self:{location:{origin:'https://fixture.invalid'},addEventListener:(k,f)=>handlers[k]=f},console};
 vm.createContext(context);vm.runInContext(source,context);
 // Real worker identity is normally supplied by the signed-in page. No DB/queue in this test.
 vm.runInContext("activeUser='fixture-user'",context);
 return {handlers,reads:()=>cachedReads};
}
test('offline reporting never presents a cached old period as fresh totals',async()=>{
 for(const path of ['/api/v1/coverage','/api/v1/dashboard/series','/api/v1/monitoring/map','/api/v1/reports']){
  const w=boot();let response;w.handlers.fetch({request:new Request('https://fixture.invalid'+path+'?period=today'),respondWith:p=>response=p});
  const result=await response;assert.equal(result.status,503);assert.equal(w.reads(),0);assert.match(await result.text(),/connection/i);
 }
});
test('reference data needed for offline entry retains its cached fallback',async()=>{
 const w=boot();let response;w.handlers.fetch({request:new Request('https://fixture.invalid/api/v1/attendance/villages'),respondWith:p=>response=p});
 assert.equal((await response).status,200);assert.equal(w.reads(),1);
});
