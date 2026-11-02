import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const script=html.match(/<script id="irc-dashboard-link-fix-20261028">([\s\S]*?)<\/script>/)[1];
// Removing county initialization recreates the dead House link on the landing view.
test('House navigation loads the default county before seeking a district target',async()=>{
 let listener, scrolled=false; const elements={'county-select':{value:''}};
 const context={currentCounty:null,window:{setCenterView(){}},document:{getElementById:id=>elements[id],addEventListener:(type,fn)=>listener=fn},history:{replaceState(){}},setTimeout:()=>{}};
 context.loadAll=async()=>{elements['representative-in-congress']={scrollIntoView(){scrolled=true;}};};
 vm.runInNewContext(script,context);
 listener({target:{closest:()=>({closest:()=>true,getAttribute:()=> '#representative-in-congress'})},preventDefault(){}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(context.currentCounty,'Indian River');
 assert.equal(elements['county-select'].value,'Indian River');
 assert.equal(scrolled,true);
});
test('every classic inline script parses',()=>{
 for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){
  if(!/type=["']module|src=/.test(match[1])) new vm.Script(match[2]);
 }
});
test('pending General Election notice precedes archive map after dashboard reordering',()=>{
 const order=['head','countdown','glance','toolbar','map','polls','stories','voter','board','status'];
 const node=name=>({insertAdjacentElement(position,other){order.splice(order.indexOf(other.name),1);order.splice(order.indexOf(name)+1,0,other.name);},name});
 const nodes=Object.fromEntries(order.map(name=>[name,node(name)]));
 const ids={'election-countdown':'countdown','toolbar-wrap':'toolbar','florida-heatmap':'map','latest-polls':'polls','election-stories':'stories','voter-information':'voter','shared-community-board':'board','general-results-status':'status'};
 const wrap={querySelector:()=>nodes.head};
 const document={readyState:'complete',getElementById:id=>nodes[ids[id]],querySelector:selector=>selector==='.election-at-a-glance'?nodes.glance:wrap};
 const reorder=html.match(/<script id="irc-dashboard-v31-script">([\s\S]*?)<\/script>/)[1];
 vm.runInNewContext(reorder,{document,setTimeout:fn=>fn()});
 assert.ok(order.indexOf('status')<order.indexOf('map'));
});
