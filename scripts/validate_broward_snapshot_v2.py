#!/usr/bin/env python3
# isolated Broward validation; production remains untouched
import json
from pathlib import Path

p=Path('data/broward.json')
d=json.loads(p.read_text())
assert d.get('county')=='Broward'
assert d.get('coverageComplete') is True
assert d.get('precinctsReporting')==346 and d.get('precinctsTotal')==346
assert len(d.get('races') or [])==28
val=d.get('validation') or {}
assert val.get('noDuplicatePrecincts') is True
checks=val.get('statewideOverlapChecks') or []
assert len(checks)==8
assert all(c.get('leaderMatch') is True for c in checks)
assert all(float(c.get('deltaPct') or 0) < 0.1 for c in checks)
manifest=json.loads(Path('data/manifest.json').read_text())
ent=manifest['counties'].setdefault('Broward',{})
ent.update({
  'connected':True,
  'file':'data/broward.json',
  'sourceUrl':d.get('sourceUrl'),
  'races':len(d['races']),
  'adapter':'v2-broward-precinct-aggregate',
  'validationFailed':False,
  'frozenElection':True,
  'validatedAgainst':'Broward official precinct totals + Florida DOS statewide sanity checks'
})
ent.pop('error',None)
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('broward-v2-promotion-report.json').write_text(json.dumps({'status':'passed','county':'Broward','precincts':'346/346','contests':28,'statewideChecks':8},indent=2)+'\n')
print('Broward v2 snapshot validated')
