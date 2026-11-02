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
