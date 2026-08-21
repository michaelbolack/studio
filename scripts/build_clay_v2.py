#!/usr/bin/env python3
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup

URL='https://enr.electionsfl.org/CLA/3990/Summary/Scrolling/Banner/'
COUNTY='Clay'

def norm(s):
    k=re.sub(r'[^a-z0-9]','',str(s or '').lower())
    aliases={'davidjollygwengraham':'davidjollyandgwengraham'}
    return aliases.get(k,k)
def party_from_name(name):
    m=re.search(r'\((REP|DEM|NPA|NON)\)\s*$',name,re.I)
    return (m.group(1).upper().replace('NPA','NON') if m else 'NON')
def clean_name(name): return re.sub(r'\s*\((REP|DEM|NPA|NON)\)\s*$','',name,flags=re.I).strip()
def office_key(name):
    s=name.lower()
    if 'united states senator' in s: return 'United States Senator'
    if 'governor and lieutenant governor' in s or s.strip()=='governor': return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s: return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s: return 'Commissioner of Agriculture'
    return None

r=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
page=' '.join(soup.stripped_strings)
assert '2026 Primary Election' in page
assert 'Official Results' in page
assert re.search(r'Precincts Reporting:\s*48\s*/\s*48',page,re.I)
assert 'Election Day: Completely Reported' in page and 'Early Votes: Completely Reported' in page and 'Vote By Mail: Completely Reported' in page

races=[]
for table in soup.find_all('table'):
    headers=[' '.join(x.stripped_strings) for x in table.find_all('th')]
    if 'Total Votes' not in headers or 'Percentage' not in headers: continue
    title=None
    for prev in table.find_all_previous(limit=20):
        txt=' '.join(prev.stripped_strings)
        if not txt or len(txt)>180: continue
        if any(k in txt.lower() for k in ['senator','governor','representative','financial officer','agriculture','judge','school board','county commissioner','referendum','mayor','council']):
            title=txt; break
    if not title: continue
    title=re.sub(r'^\s*\[?Input\]?\s*','',title).strip()
    cands=[]
    for tr in table.find_all('tr'):
        cells=[' '.join(c.stripped_strings) for c in tr.find_all(['th','td'])]
        if len(cells)<7 or cells[0].strip().lower() in ('choice',''): continue
        name=cells[0].strip(); votes=re.sub(r'[^0-9]','',cells[-2]); pct=re.sub(r'[^0-9.]','',cells[-1])
        if not votes: continue
        cands.append({'name':clean_name(name),'party':party_from_name(name),'votes':int(votes),'percent':float(pct or 0)})
    if cands:
        key=(title,tuple((c['name'],c['votes']) for c in cands))
        if not any((x['name'],tuple((c['name'],c['votes']) for c in x['candidates']))==key for x in races):
            races.append({'name':title,'candidates':cands})
assert len(races)>=8, len(races)

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

out={'schemaVersion':2,'county':COUNTY,'election':'2026 Primary Election','electionDate':'2026-08-18','source':'Clay County Supervisor of Elections - Official Results','sourceUrl':URL,'precinctsReporting':48,'precinctsTotal':48,'coverageComplete':True,'frozenElection':True,'races':races,'validation':{'sourcePageOfficial':True,'allPrecinctsReported':True,'statewideOverlapChecks':checks}}
Path('data/clay.json').write_text(json.dumps(out,indent=2)+'\n')
manifest=json.loads(Path('data/manifest.json').read_text()); ent=manifest['counties'].setdefault(COUNTY,{})
ent.update({'connected':True,'file':'data/clay.json','sourceUrl':URL,'races':len(races),'adapter':'v2-clay-official-scrolling','validationFailed':False,'frozenElection':True,'validatedAgainst':'Clay official scrolling results + Florida DOS statewide sanity checks'}); ent.pop('error',None)
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('clay-v2-report.json').write_text(json.dumps({'status':'passed','races':len(races),'precincts':'48/48','statewideChecks':len(checks)},indent=2)+'\n')
print('Clay v2 built',len(races),'races')
