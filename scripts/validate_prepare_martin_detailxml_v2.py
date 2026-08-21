#!/usr/bin/env python3
import json,re
from pathlib import Path

def key(s):
    s=str(s or '').lower()
    s=s.replace('david jolly and gwen graham','david jolly')
    s=s.replace("'",'').replace('"','')
    return re.sub(r'[^a-z0-9]+','',s)

def party(r):
    ps={str(c.get('party','')).upper() for c in r.get('candidates',[]) if c.get('party')}
    return next(iter(ps)) if len(ps)==1 else None

m=json.loads(Path('data/martin.json').read_text())
s=json.loads(Path('data/statewide.json').read_text())
assert m['county']=='Martin' and m['coverageComplete'] is True
assert m['precinctsReporting']==29 and m['precinctsTotal']==29
assert len(m['races'])==20
assert all(r.get('precinctsReporting')==r.get('precinctsTotal') for r in m['races'])
checks=[]
state_races=[r for r in s.get('races',[]) if r.get('type')=='statewide']
assert len(state_races)==8, len(state_races)
for sr in state_races:
    office=sr['office']; p=str(sr['party']).upper()
    matches=[r for r in m['races'] if r['name']==office and party(r)==p]
    assert len(matches)==1,(office,p,len(matches))
    mr=matches[0]
    geo=[g for g in sr.get('geography',[]) if g.get('county')=='Martin']
    assert len(geo)==1,(office,p,'missing Martin geography')
    dv={key(n):int(v) for n,v in geo[0]['votes'].items()}
    cv={key(c['name']):int(c['votes']) for c in mr['candidates']}
    assert set(dv)==set(cv),(office,p,set(dv)-set(cv),set(cv)-set(dv))
    diffs={n:cv[n]-dv[n] for n in dv}
    assert all(v>=0 for v in diffs.values()),(office,p,'county export behind DOS',diffs)
    dos_total=sum(dv.values()); county_total=sum(cv.values()); delta=county_total-dos_total
    limit=max(25,round(dos_total*0.002))
    assert delta<=limit,(office,p,'delta too large',dos_total,county_total,delta,limit)
    dos_leader=max(dv,key=dv.get); county_leader=max(cv,key=cv.get)
    assert dos_leader==county_leader,(office,p,'leader mismatch')
    checks.append({'office':office,'party':p,'dosVotes':dos_total,'countyVotes':county_total,'delta':delta,'deltaPct':round((delta/dos_total*100) if dos_total else 0,4),'leaderMatch':True,'candidateSetMatch':True})
assert len(checks)==8
m['validation']['statewideOverlapChecks']=checks
m['validation']['validationStatus']='passed'
Path('data/martin.json').write_text(json.dumps(m,indent=2)+'\n')
mp=Path('data/manifest.json'); manifest=json.loads(mp.read_text())
manifest['counties']['Martin']={'connected':True,'file':'data/martin.json','sourceUrl':'https://results.enr.clarityelections.com/FL/Martin/126768/','races':20,'adapter':'v2-martin-official-detailxml','validationFailed':False,'frozenElection':True,'validatedAgainst':'Martin official Clarity Detail XML export + Florida DOS statewide county geography'}
mp.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(checks,indent=2))
print('Martin Detail XML validation passed: 20 races, 29/29 countywide, 8/8 statewide checks')
