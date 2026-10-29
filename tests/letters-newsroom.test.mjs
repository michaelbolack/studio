import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

// A DOM transport double; the shipped Wix component and its rendering logic run unchanged.
class Element {
  constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {}; this.style = {}; this.className = ''; this._text = ''; this.listeners = {}; this.isConnected = true; }
  append(...nodes) { for (const node of nodes) { node.parent = this; this.children.push(node); } }
  replaceChildren(...nodes) { this.children = []; this._text = ''; this.append(...nodes); }
  set textContent(value) { this._text = value; this.children = []; }
  get textContent() { return this._text + this.children.map(node => node.textContent).join(''); }
  get classList() { return { add: (...names) => { this.className += ' ' + names.join(' '); }, contains: name => this.className.split(' ').includes(name) }; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  hasAttribute(key) { return key in this.attributes; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); }
  hasChildNodes() { return this.children.length > 0; }
  attachShadow() { this.shadowRoot = new Element(); }
  querySelectorAll(selector) { return this.children.flatMap(node => [ ...(selector.startsWith('.') ? node.classList.contains(selector.slice(1)) : node.tagName === selector.toUpperCase()) ? [node] : [], ...node.querySelectorAll(selector)]); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

async function fixture(articles = [], category = 'All', raw = null) {
 const html = await readFile(new URL('../newsroom.html', import.meta.url), 'utf8');
 let Component;
 const context = vm.createContext({URL, URLSearchParams, Date, Intl, console, HTMLElement:Element, document:{createElement:tag=>new Element(tag),querySelector:()=>new Element(),addEventListener(){}},window:{addEventListener(){},parent:{postMessage(){}}},customElements:{get(){},define(n,c){Component=c;}},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},AbortController,fetch:async()=>({ok:true,json:async()=>({items:[],ad:null})})});
 vm.runInContext([...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)][0][1],context);
 const component=new Component();component.setAttribute('category',category);component.setAttribute('data','[]');component.setAttribute('sunshine',JSON.stringify({title:'Sunshine story',url:'https://thomasaugustus.substack.com/p/test'}));
 if(raw){component.setAttribute('data',JSON.stringify(raw));component.render();return component.shadowRoot;}
 return component.landing(articles);
}
test('letters invitation remains available before any letters are published',async()=>{
 const main=await fixture([], 'Letters to the Editor');
 const section=main.querySelector('.letters-feature');assert.ok(section);
 const link=section.querySelector('a');assert.equal(link.href,'https://suite.ircmedia.net/letters/');assert.equal(link.target,'_blank');
});
test('letters section follows Sunshine and published letters remain in ordinary feed',async()=>{
 const main=await fixture([{id:'one',title:'Reader letter',category:'Letters to the Editor',reporterName:'Jane · Vero Beach',url:'/news/letter',date:'2026-10-29'},{id:'two',title:'Regular story',category:'Local',url:'/news/story'}]);
 const section=main.querySelector('.letters-feature');assert.ok(section);assert.equal(main.children.indexOf(section), main.children.indexOf(main.querySelector('.sunshine-feature'))+1);
 assert.match(section.textContent,/Reader letter/);assert.match(section.textContent,/Jane · Vero Beach/);assert.match(main.querySelector('.news-list-first').textContent,/Reader letter/);
 assert.ok(main.querySelector('.category-filters').children.some(x=>x.textContent==='Letters to the Editor'));
});

test('unpublished letters and private email do not reach the rendered feed', async()=>{
 const base={category:'Letters to the Editor',reporterName:'Jane · Vero Beach',email:'private@example.com',date:'2026-10-29','link-news-title':'/news/approved'};
 const root=await fixture([], 'All', [{...base,_id:'approved',_publishStatus:'PUBLISHED',title:'Approved letter'},{...base,_id:'draft',_publishStatus:'DRAFT',title:'Private draft letter'}]);
 assert.match(root.textContent,/Approved letter/);assert.doesNotMatch(root.textContent,/Private draft letter|private@example.com/);
});
test('letter browsing paginates the existing All feed and never substitutes unrelated stories', async()=>{
 const html=await readFile(new URL('../newsroom.html',import.meta.url),'utf8');
 const host=new Element(),sent=[];let receive;
 const context=vm.createContext({URL,URLSearchParams,Date,Intl,console,HTMLElement:Element,document:{createElement:tag=>new Element(tag),querySelector:()=>host,addEventListener(){}},window:{addEventListener(type,fn){if(type==='message')receive=fn;},parent:{postMessage(message){sent.push(message);}}},customElements:{get(){},define(){}},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},AbortController,fetch:async()=>({ok:true,json:async()=>({items:[],ad:null})})});
 vm.runInContext([...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)][0][1],context);
 host.listeners['irc-newsroom:request']({detail:{category:'Letters to the Editor',offset:0}});
 assert.equal(sent.at(-1).category,'All');
 receive({source:context.window.parent,data:{type:'irc-newsroom:data',category:'All',offset:0,hasMore:true,items:[{_id:'news',title:'Ordinary news',category:'Local'}]}});
 assert.equal(host.getAttribute('category'),'Letters to the Editor');assert.deepEqual(JSON.parse(host.getAttribute('data')),[]);assert.equal(sent.at(-1).offset,1);
 receive({source:context.window.parent,data:{type:'irc-newsroom:data',category:'All',offset:1,hasMore:true,items:[{_id:'letter',title:'Letter',category:'Letters to the Editor'}]}});
 assert.equal(JSON.parse(host.getAttribute('data'))[0]._id,'letter');
 host.listeners['irc-newsroom:request']({detail:{category:'Letters to the Editor',offset:1}});
 assert.equal(sent.at(-1).offset,2);
 host.listeners['irc-newsroom:request']({detail:{category:'Local',offset:0}});assert.equal(sent.at(-1).category,'Local');
});
