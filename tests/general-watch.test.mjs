import test from 'node:test';import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateSnapshot,watchState,createWatchStore} from '../assets/general-watch.mjs';
const fixture=JSON.parse(readFileSync(new URL('../data/general-watch.json',import.meta.url)));
test('pending remains pending before publication',()=>{assert.equal(watchState({...fixture,fetchedAt:'2026-11-02T11:59:00Z'},{},new Date('2026-11-02T12:00:00Z')),'pending');});
test('wrong election and malformed candidate totals fail closed',()=>{
 assert.throws(()=>validateSnapshot({...fixture,electionId:'2026-fl-primary'}));
 const bad=structuredClone(fixture);bad.races[0].candidates[0].votes=-1;assert.throws(()=>validateSnapshot(bad));
});
test('stale snapshots and failed sources show delayed updates',()=>{
 assert.equal(watchState({...fixture,fetchedAt:'2026-11-04T01:00:00Z'},{},new Date('2026-11-04T02:00:00Z')),'delayed');
 assert.equal(watchState(fixture,{state:{status:'error'}},new Date(fixture.fetchedAt)),'delayed');
});
test('refresh preserves selected scope and failed refresh preserves last valid snapshot',()=>{
 const store=createWatchStore();store.select('florida');store.accept(fixture);assert.equal(store.scope,'florida');
 assert.throws(()=>store.accept({}));assert.equal(store.snapshot,fixture);assert.equal(store.scope,'florida');
});
test('full district totals cannot be mistaken for Indian River totals',()=>{
 validateSnapshot(fixture);assert.ok(fixture.races.some(r=>r.scope==='district'&&r.countiesIncluded>1));
});
test('county unofficial returns are visible after seven Eastern before statewide release',()=>{
 const data=structuredClone(fixture);data.fetchedAt='2026-11-04T00:20:00Z';data.races.find(r=>r.scope==='local').status='unofficial';
 assert.equal(watchState(data,{},new Date('2026-11-04T00:22:00Z')),'unofficial');
});
test('unavailable health cannot be treated as a healthy refresh',async()=>{
 const {readWatchResponses}=await import('../assets/general-watch.mjs');
 await assert.rejects(()=>readWatchResponses({ok:true,json:async()=>fixture},{ok:false}),/health/i);
});
test('primary navigation targets General watch coverage while archive links remain separate',async()=>{
 const {watchDestination}=await import('../assets/general-watch.mjs');
 assert.equal(watchDestination('#united-states-senator').scope,'florida');
 assert.equal(watchDestination('#local-races').scope,'local');
 assert.equal(watchDestination('#prediction-markets'),null);
});
