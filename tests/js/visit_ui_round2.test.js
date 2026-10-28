"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const source = (filename) => fs.readFileSync(path.join(root,"app/static/js",filename),"utf8");
const element = () => ({textContent:"",innerHTML:"",classList:{values:new Set(),add(n){this.values.add(n)},remove(n){this.values.delete(n)},toggle(n,enabled){if(enabled)this.add(n);else this.remove(n)}},dataset:{}});
const escapeHtml = (str) => String(str).replace(/[&<>\"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
async function tick(){await new Promise((resolve) => setImmediate(resolve));}
(async()=>{
  const nodes={"#monitor-status-list":element(),"#monitor-updated":element(),"#village-map":element(),"#map-no-coordinates":element(),"#monitor-unmapped":element()};
  const document={querySelector:(q)=>nodes[q]||null,querySelectorAll:()=>[]};
  const context={window:{MV:{escapeHtml,api:async (url)=>({ok:true,json:async()=>url.endsWith('summary')?{counts:{villages:1},status_breakdown:{Done:0,'Not done':1}}:{items:[{id:7,name:'Village <script>',latitude:null,longitude:null,committee_count:8,status:'Not visited',cluster:'CSRB',da_name:'DA'}]}})},addEventListener:()=>{}},document,setTimeout};
  vm.runInNewContext(source('monitoring.js'),context);
  await tick(); await tick();
  assert(nodes['#village-map'].classList.values.has('hidden'), 'Unmapped village should not appear as 0,0 marker');
  assert.match(nodes['#monitor-unmapped'].innerHTML,/without GPS/);
  assert.match(nodes['#monitor-unmapped'].innerHTML,/Village &lt;script&gt;/);
  assert.doesNotMatch(nodes['#monitor-unmapped'].innerHTML,/<script>/);

  const analyticsNodes={"analytics-completion":element(),"analytics-gender":element(),"analytics-clusters":element(),"analytics-committees":element(),"analytics-alert":element()};
  const page={querySelector:()=>null};
  const analyticDoc={getElementById:(q)=>q==='visit-analytics'?page:analyticsNodes[q]||null};
  const context2={window:{MV:{escapeHtml,api:async()=>({ok:true,json:async()=>({counts:{people_attended:0},status_breakdown:{Done:0,'Not done':0},gender_distribution:{Male:0,Female:0},cluster_breakdown:{},committee_aggregates:{}})})}},document:analyticDoc};
  vm.runInNewContext(source('visit-analytics.js'),context2);
  await tick();await tick();
  assert.match(analyticsNodes['analytics-gender'].innerHTML,/No attendance submitted this month/);
  assert.match(analyticsNodes['analytics-completion'].innerHTML,/No villages in scope/);
  console.log('PASS monitoring missing GPS, escaped labels, and analytics zero-data fallback');
})().catch((error)=>{console.error(error);process.exitCode=1});
