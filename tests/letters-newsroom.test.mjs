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
 const link=section.querySelector('a');assert.equal(link.href,'https://irc-article-audio.michaelbolack.chatgpt.site/letters/');assert.equal(link.target,'_blank');
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
