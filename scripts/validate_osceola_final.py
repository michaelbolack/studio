import json,re
from pathlib import Path

def key(s):
    s=str(s or '').lower().replace('and gwen graham','')
    return re.sub(r'[^a-z0-9]','',s)

data=json.loads(Path('data/osceola.json').read_text())
state=json.loads(Path('data/statewide.json').read_text())
d9=json.loads(Path('data/district-9.json').read_text())
manifest=json.loads(Path('data/manifest.json').read_text())
assert data.get('county')=='Osceola'
assert len(data.get('races',[]))==23
checks=[]
for race in data['races']:
    src=race['sourceContestName']
    if not (src.startswith('REP ') or src.startswith('DEM ')):
        continue
    if not any(x in src for x in ['United States Senator','Governor and Lieutenant Governor','Chief Financial Officer','Commissioner of Agriculture']):
        continue
    sr=next((x for x in state['races'] if x['name']==src),None)
    assert sr,src
    geo=next((g for g in sr.get('geography',[]) if g.get('county')=='Osceola'),None)
    assert geo,src
    dos={key(n):int(v) for n,v in geo['votes'].items()}
    local={key(c['name']):int(c['votes']) for c in race['candidates']}
    assert set(dos)==set(local),(src,set(dos)^set(local))
    delta={n:local[n]-dos[n] for n in local}
    assert all(0<=d<=50 for d in delta.values()),(src,delta)
    assert max(dos,key=dos.get)==max(local,key=local.get),(src,'leader changed')
    checks.append({'race':src,'maxDelta':max(delta.values()),'leaderPreserved':True})
assert len(checks)==8,checks
race=next(r for r in data['races'] if 'Representative in Congress - District 9' in r['name'])
local={key(c['name']):int(c['votes']) for c in race['candidates']}
geo=next(g for r in d9['races'] for g in r.get('geography',[]) if g.get('county')=='Osceola')
dos={key(n):int(v) for n,v in geo['votes'].items()}
assert set(dos)==set(local),(set(dos)^set(local))
delta={n:local[n]-dos[n] for n in local}
assert all(0<=d<=10 for d in delta.values()),delta
assert max(dos,key=dos.get)==max(local,key=local.get),'District 9 leader changed'
data['validation']={'status':'passed','statewideOverlapChecks':checks,'district9MaxDelta':max(delta.values()),'note':'Official Osceola Clarity browser JSON snapshot is slightly later than protected Florida DOS snapshots; only small nonnegative deltas are allowed and leaders must match.'}
data['coverageComplete']=True
data['frozenElection']=False
data['displayStatus']='unofficial-complete'
Path('data/osceola.json').write_text(json.dumps(data,indent=2)+'\n')
manifest['counties']['Osceola']={'connected':True,'file':'data/osceola.json','sourceUrl':data['sourceUrl'],'races':len(data['races']),'adapter':'v2-osceola-browser-json-validated','validationFailed':False,'frozenElection':False,'coverageComplete':True,'displayStatus':'unofficial-complete','clarityVersion':'378698','validatedAgainst':'Osceola official Clarity browser JSON + Florida DOS statewide county geography + District 9 geography'}
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
report={'passed':True,'races':len(data['races']),'statewideChecks':checks,'district9MaxDelta':max(delta.values()),'coverageComplete':True,'certified':False}
Path('osceola-final-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
