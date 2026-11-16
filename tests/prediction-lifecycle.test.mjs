import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync('index.html','utf8');
const fn=html.split('function predictionMarketsDisplaySafe',2)[1].split('function compactContracts',1)[0];
const safe=vm.runInNewContext('(function predictionMarketsDisplaySafe'+fn.trim()+')');
const readiness=JSON.parse(fs.readFileSync('data/prediction-markets-readiness.json','utf8'));
const data=JSON.parse(fs.readFileSync('data/prediction-markets.json','utf8'));
test('active long-range markets remain visible after core markets close',()=>{
 const s={...data,events:[],generatedAt:new Date().toISOString()};
 assert.equal(safe(readiness,s),true);
 assert.equal(safe(readiness,{...s,longRangeEvents:[]}),false);
 assert.equal(safe(readiness,{...s,generatedAt:'2020-01-01T00:00:00Z'}),false);
});
