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
