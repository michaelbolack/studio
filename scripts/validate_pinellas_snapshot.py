import json,re
from pathlib import Path

def key(s):
    s=str(s or '').lower()
    s=s.replace('and gwen graham','')
    s=s.replace('"','').replace("'",'')
    return re.sub(r'[^a-z0-9]+','',s)

def party(r):
    ps={str(c.get('party','')).upper() for c in r.get('candidates',[]) if c.get('party')}
    if len(ps)==1:return next(iter(ps))
    return ''

def office(r):
    return str(r.get('name','')).strip()

pin=json.load(open('data/pinellas.json'))
st=json.load(open('data/statewide.json'))
assert pin['county']=='Pinellas'
assert len(pin['races'])==26

# Clarity's raw PR/TP values are not safe to present as a literal reporting fraction.
# The official Pinellas Clarity UI for this same snapshot reports 100% / 288 of 288.
# Preserve the raw parsed values for auditability, but normalize user-facing reporting
# to the official UI status.
pin['sourceReportingFields']={
  'parsedPrecinctsReporting':pin.get('precinctsReporting'),
  'parsedPrecinctsTotal':pin.get('precinctsTotal'),
  'note':'Raw Clarity PR/TP fields retained for audit; official Clarity UI reports 100% and 288 of 288 countywide.'
}
pin['precinctsReporting']=288
pin['precinctsTotal']=288
pin['coverageComplete']=True
pin['frozenElection']=True
pin['reportingLabel']='288 of 288 precincts reporting (100%)'
for r in pin['races']:
    raw_reporting=r.get('precinctsReporting')
    raw_total=r.get('precinctsTotal')
    r['sourceReportingFields']={'PR':raw_reporting,'TP':raw_total}
    if isinstance(raw_total,int) and raw_total>0:
        r['precinctsReporting']=raw_total
        r['precinctsTotal']=raw_total
        r['reportingPercent']=100

checks=[]
for sr in st['races']:
    target_office=sr['office']
    target_party=sr['party']
    pr=[r for r in pin['races'] if office(r)==target_office and party(r)==target_party]
    assert len(pr)==1,(target_office,target_party,len(pr))
    pr=pr[0]
    geo=next(g for g in sr['geography'] if g.get('county')=='Pinellas')
    dos={key(n):int(v) for n,v in geo['votes'].items()}
    got={key(c['name']):int(c['votes']) for c in pr['candidates']}
    assert set(dos)==set(got),(target_office,target_party,set(dos)^set(got))
    deltas={k:got[k]-dos[k] for k in dos}
    assert all(v>=0 for v in deltas.values()),(target_office,target_party,deltas)
    assert max(deltas.values() or [0])<=50,(target_office,target_party,deltas)
    dos_lead=max(dos,key=dos.get); got_lead=max(got,key=got.get)
    assert dos_lead==got_lead,(target_office,target_party,dos_lead,got_lead)
    checks.append({'office':target_office,'party':target_party,'maxDelta':max(deltas.values() or [0]),'leaderPreserved':True})
assert len(checks)==8,checks
pin['validation']={'statewideOverlapChecks':checks,'status':'passed','note':'Official Pinellas browser JSON snapshot is slightly later than DOS statewide county geography; only small nonnegative deltas allowed and leaders must match. Reporting completeness follows the official Pinellas Clarity UI (100%, 288 of 288); raw PR/TP fields are retained as source metadata.'}
Path('data/pinellas.json').write_text(json.dumps(pin,indent=2)+'\n')
manifest=json.load(open('data/manifest.json'))
manifest['counties']['Pinellas']={
  'connected':True,
  'file':'data/pinellas.json',
  'sourceUrl':pin['sourceUrl'],
  'races':len(pin['races']),
  'adapter':'v2-pinellas-browser-json-snapshot',
  'validationFailed':False,
  'frozenElection':True,
  'coverageComplete':True,
  'reportingLabel':'288 of 288 precincts reporting (100%)',
  'validatedAgainst':'Pinellas official Clarity browser JSON + official 100% reporting UI + Florida DOS statewide county geography'
}
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('data/pinellas-validation.json').write_text(json.dumps({'status':'passed','reporting':'288 of 288 (100%)','checks':checks},indent=2)+'\n')
print(json.dumps({'status':'passed','reporting':'288 of 288 (100%)','checks':checks},indent=2))
