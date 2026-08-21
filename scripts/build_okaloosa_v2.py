#!/usr/bin/env python3
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup

URL='https://enrarchive.electionsfl.org/OKA/4026/Summary/'
COUNTY='Okaloosa'

def norm(s):
    return re.sub(r'[^a-z0-9]','',str(s or '').lower())

def office_key(name):
    s=name.lower()
    if 'united states senator' in s: return 'United States Senator'
    if 'governor and lieutenant governor' in s: return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s: return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s: return 'Commissioner of Agriculture'
    return None

r=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
page=' '.join(soup.stripped_strings)
assert '2026 Primary Election' in page
assert 'OFFICIAL RESULTS' in page
assert re.search(r'Precincts Reporting:\s*52\s*/\s*52',page,re.I)
for marker in ('Election Day: Completely Reported','Early Votes: Completely Reported','Vote By Mail: Completely Reported'):
    assert marker in page

# Each race is delimited in this archived ENR summary by the favorite-race control text.
chunks=[c.strip() for c in page.split('Add or Take Out of Favorite Races') if '(Vote For 1)' in c and 'Choice Percent Votes' in c]
races=[]
for chunk in chunks:
    # Keep the last plausible title immediately before (Vote For 1).
    pre=chunk.split('(Vote For 1)',1)[0].strip()
    # Remove page/header residue on the first chunk.
    for marker in ('OFFICIAL RESULTS Summary Results Favorite Races Summary Results Favorite Races','Summary Results Favorite Races'):
        if marker in pre: pre=pre.split(marker)[-1].strip()
    title=pre
    body=chunk.split('Choice Percent Votes',1)[1]
    cands=[]
    pat=re.compile(r'(.+?)\s+\((REP|DEM|NON|NPA)\)\s+([0-9]+(?:\.[0-9]+)?)%\s+([0-9][0-9,]*)')
    for m in pat.finditer(body):
        name=' '.join(m.group(1).split()).strip()
        party=m.group(2).upper().replace('NPA','NON')
        cands.append({'name':name,'party':party,'votes':int(m.group(4).replace(',','')),'percent':float(m.group(3))})
    if cands:
        races.append({'name':title,'candidates':cands})

# Remove accidental duplicate race chunks if vendor markup repeats controls.
unique=[]; seen=set()
for race in races:
    sig=(race['name'],tuple((c['name'],c['votes']) for c in race['candidates']))
    if sig not in seen:
        seen.add(sig); unique.append(race)
races=unique
assert len(races)>=11, len(races)

state=json.loads(Path('data/statewide.json').read_text())
checks=[]
for sr in state.get('races',[]):
    office=sr.get('office'); party=sr.get('party')
    lr=next((x for x in races if office_key(x['name'])==office and any(c['party']==party for c in x['candidates'])),None)
    assert lr,(office,party)
    actual={norm(c['name']):int(c['votes']) for c in lr['candidates'] if c['party']==party}
    geo=next(g for g in sr.get('geography',[]) if g.get('county')==COUNTY)
    expected={norm(k):int(v) for k,v in geo.get('votes',{}).items()}
    assert set(actual)==set(expected),(office,party,actual,expected)
    deltas={k:actual[k]-expected[k] for k in expected}
    assert all(v>=0 for v in deltas.values()),(office,party,deltas)
    st=sum(expected.values()); ct=sum(actual.values()); dp=((ct-st)/st*100) if st else 0
    assert dp<0.25,(office,party,dp)
    assert max(actual,key=actual.get)==max(expected,key=expected.get)
    checks.append({'office':office,'party':party,'dosVotes':st,'countyVotes':ct,'delta':ct-st,'deltaPct':round(dp,4),'leaderMatch':True})
assert len(checks)==8,len(checks)

out={'schemaVersion':2,'county':COUNTY,'election':'2026 Primary Election','electionDate':'2026-08-18','source':'Okaloosa County Supervisor of Elections - Official VoterFocus Archive','sourceUrl':URL,'precinctsReporting':52,'precinctsTotal':52,'coverageComplete':True,'frozenElection':True,'races':races,'validation':{'sourcePageOfficial':True,'allPrecinctsReported':True,'statewideOverlapChecks':checks}}
Path('data/okaloosa.json').write_text(json.dumps(out,indent=2)+'\n')
manifest=json.loads(Path('data/manifest.json').read_text()); ent=manifest['counties'].setdefault(COUNTY,{})
ent.update({'connected':True,'file':'data/okaloosa.json','sourceUrl':URL,'races':len(races),'adapter':'v2-okaloosa-voterfocus-archive','validationFailed':False,'frozenElection':True,'validatedAgainst':'Okaloosa official VoterFocus archive + Florida DOS statewide sanity checks'}); ent.pop('error',None)
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('okaloosa-v2-report.json').write_text(json.dumps({'status':'passed','races':len(races),'precincts':'52/52','statewideChecks':len(checks)},indent=2)+'\n')
print('Okaloosa v2 built',len(races),'races')
