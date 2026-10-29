const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const file = 'app/static/js/reference-ui.js';
function load() {
 const ctx = { window: {}, document: {querySelectorAll:()=>[], getElementById:()=>null}, console, URL, URLSearchParams };
 vm.createContext(ctx); vm.runInContext(fs.readFileSync(file, 'utf8'), ctx); return ctx.window.BVUI;
}
test('map coordinates reject missing and nonnumeric data instead of inventing a pin', () => {
 const ui=load(); for (const val of [null, undefined, '', ' ', 'abc']) assert.equal(ui.coordinates(val, 79), null);
 assert.equal(ui.coordinates(91, 79), null); assert.equal(ui.coordinates(18, 181), null);
 assert.equal(ui.coordinates(0, 0).lat, 0); assert.equal(ui.coordinates('18.1','79.5').lng,79.5);
});
test('charts escape user supplied names and handle zero data honestly', () => {
 const ui=load(); assert.ok(ui.bars([{label:'<img src=x onerror=alert(1)>',value:4}]).includes('&lt;img'));
 assert.ok(!ui.bars([{label:'<img src=x>',value:4}]).includes('<img'));
 assert.match(ui.ring(0,0,['Visited','Not visited'],'No villages'),/No villages/);
 assert.match(ui.trend([]),/No submitted visits/);
});
test('coverage ring handles pending subset without negative percentages', () => {
 const ui=load(); assert.match(ui.ring(3,5,['Visited','Not visited']),/60%/);
 assert.match(ui.ring(8,5,['Visited','Not visited']),/100%/);
});
test('low-count charts use distinct integer count-axis ticks',()=>{
  const ui=load();
  const html=ui.trend([{label:'Oct',visits:1,people:2}]);
  // A single visit must not produce five tick labels rounded to 0,0,1,1,1.
  const left=[...html.matchAll(/<text x="29"[^>]*>(\d+)<\/text>/g)].map(m=>m[1]);
  assert.equal(new Set(left).size,5);
});
test('a selected month remains readable without 31 overlapping axis dates',()=>{
 const ui=load();const rows=Array.from({length:31},(_,i)=>({date:`2026-10-${String(i+1).padStart(2,'0')}`,visits:1,people:5}));
 const svg=ui.trend(rows);const labels=[...svg.matchAll(/<text [^>]*y="177"[^>]*>(.*?)<\/text>/g)].map(m=>m[1]);
 assert.ok(labels.length>=2&&labels.length<=9);assert.ok(labels.some(l=>l.includes('Oct')));
 assert.ok(svg.includes('2026-10-31: 1 visits'));
});
test('a historical last visit does not override Pending for the selected period',()=>{
 const ui=load();const element={clientWidth:400,clientHeight:230,innerHTML:'',querySelectorAll:()=>[]};
 ui.map(element,[{id:7,name:'Previously visited',status:'Not visited',last_visit_date:'2026-09-20',latitude:17.98,longitude:79.52}]);
 assert.match(element.innerHTML,/ref-map-pin pending/);assert.doesNotMatch(element.innerHTML,/ref-map-pin visited/);
});
test('an Other-village marker opens authorized evidence rather than a forbidden profile',()=>{
 const ui=load();const element={clientWidth:400,clientHeight:230,innerHTML:'',querySelectorAll:()=>[]};
 ui.map(element,[{id:7,name:'Other village',status:'Visited',outside_assignment:true,report_url:'/reports/village/9',latitude:17.98,longitude:79.52}]);
 assert.match(element.innerHTML,/href="\/reports\/village\/9"/);
});
