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
assert pin['precinctsReporting']==286 and pin['precinctsTotal']==288
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
pin['validation']={'statewideOverlapChecks':checks,'status':'passed','note':'Official Pinellas browser JSON snapshot is slightly later than DOS statewide county geography; only small nonnegative deltas allowed and leaders must match.'}
Path('data/pinellas.json').write_text(json.dumps(pin,indent=2)+'\n')
manifest=json.load(open('data/manifest.json'))
manifest['counties']['Pinellas']={
  'connected':True,
  'file':'data/pinellas.json',
  'sourceUrl':pin['sourceUrl'],
  'races':len(pin['races']),
  'adapter':'v2-pinellas-browser-json-snapshot',
  'validationFailed':False,
  'frozenElection':False,
  'coverageComplete':False,
  'reportingLabel':'286 of 288 precincts in current official snapshot',
  'validatedAgainst':'Pinellas official Clarity browser JSON + Florida DOS statewide county geography'
}
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('data/pinellas-validation.json').write_text(json.dumps({'status':'passed','checks':checks},indent=2)+'\n')
print(json.dumps({'status':'passed','checks':checks},indent=2))
