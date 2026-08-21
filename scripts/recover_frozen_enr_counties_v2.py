#!/usr/bin/env python3
# validates only existing frozen county captures; never scrapes or changes aggregates
import json,re
from pathlib import Path

TARGETS=['Alachua','Bay','Clay','DeSoto','Escambia','Flagler','Franklin','Hamilton','St. Lucie','Suwannee']

def norm(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def party(r):
    ps={str(c.get('party','')).upper() for c in r.get('candidates',[]) if c.get('party')}
    if len(ps)==1: return next(iter(ps))
    m=re.search(r'\((REP|DEM)',r.get('name',''),re.I)
    return m.group(1).upper() if m else None

def office(r):
    s=r.get('name','').lower()
    for noise in ['add or take out of favorite races','rep ','dem ']: s=s.replace(noise,'')
    if 'united states senator' in s: return 'United States Senator'
    if 'governor' in s: return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s: return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s: return 'Commissioner of Agriculture'
    return None

def votes_map(r): return {norm(c.get('name')):int(c.get('votes') or 0) for c in r.get('candidates',[])}

manifest=json.loads(Path('data/manifest.json').read_text())
state=json.loads(Path('data/statewide.json').read_text())
state_index={(r.get('office'),r.get('party')):r for r in state.get('races',[])}
report=[]
for county in TARGETS:
    slug=county.lower().replace(' ','-').replace('.','')
    p=Path('data')/(slug+'.json')
    row={'county':county,'file':str(p),'passed':False,'checks':[]}
    if not p.exists(): row['error']='county JSON missing'; report.append(row); continue
    d=json.loads(p.read_text())
    if not d.get('races'): row['error']='no races'; report.append(row); continue
    if d.get('precinctsTotal') and d.get('precinctsReporting')!=d.get('precinctsTotal'):
        row['error']=f"precincts incomplete {d.get('precinctsReporting')}/{d.get('precinctsTotal')}"; report.append(row); continue
    local={(office(r),party(r)):r for r in d.get('races',[]) if office(r) and party(r) in ('REP','DEM')}
    failures=[]
    checked=0
    for key,sr in state_index.items():
        lr=local.get(key)
        if not lr: failures.append(f'missing statewide race {key}'); continue
        geo=next((g for g in sr.get('geography',[]) if g.get('county')==county),None)
        if not geo: failures.append(f'missing DOS geography {key}'); continue
        expected={norm(k):int(v) for k,v in (geo.get('votes') or {}).items()}
        actual=votes_map(lr)
        if actual!=expected and sorted(actual.values())!=sorted(expected.values()):
            failures.append(f'vote mismatch {key}: local={actual} dos={expected}')
        else: checked+=1
    row['checks']=failures
    row['statewideRacesValidated']=checked
    if not failures and checked==len(state_index):
        row['passed']=True
        ent=manifest['counties'].setdefault(county,{})
        ent.update({'connected':True,'file':f'data/{slug}.json','races':len(d.get('races',[])),'adapter':'v2-frozen-enr-validated','validationFailed':False,'frozenElection':True,'validatedAgainst':'Florida DOS Election Watch statewide county geography'})
        ent.pop('error',None)
report_obj={'targets':len(TARGETS),'passed':sum(1 for r in report if r['passed']),'failed':sum(1 for r in report if not r['passed']),'counties':report}
Path('frozen-enr-recovery-report.json').write_text(json.dumps(report_obj,indent=2)+'\n')
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(report_obj,indent=2))
if report_obj['failed']:
    raise SystemExit(1)
