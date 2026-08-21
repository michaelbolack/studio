#!/usr/bin/env python3
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup

URL='https://enr.electionsfl.org/FLA/4029/Summary/'
COUNTY='Flagler'

def norm(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def clean_num(s): return int(re.sub(r'[^0-9]','',str(s or '')) or 0)
def office_key(name):
    s=re.sub(r'^(REP|DEM)\s+','',name,flags=re.I).lower()
    if 'united states senator' in s:return 'United States Senator'
    if 'governor and lieutenant governor' in s:return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s:return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s:return 'Commissioner of Agriculture'
    return None

def party_for(name):
    return 'REP' if name.startswith('REP ') else 'DEM' if name.startswith('DEM ') else 'NON'

def race_title(inp):
    for attr in ('aria-label','title','value'):
        v=' '.join(str(inp.get(attr) or '').split())
        if v and not v.lower().startswith('select'): return v
    parent=inp.find_parent()
    for node in inp.find_all_previous(['h2','h3','h4','label','div','span'],limit=25):
        txt=' '.join(node.stripped_strings)
        if txt and len(txt)<180 and any(k in txt.lower() for k in ('senator','governor','representative','commissioner','judge','school board','county commissioners','council member')):
            return txt
    return None

def candidate_from_row(tr, race_name):
    cells=[' '.join(c.stripped_strings) for c in tr.find_all(['td','th'])]
    if len(cells)<3:return None
    txt=' '.join(cells)
    m=re.search(r'(.+?)\s*\((REP|DEM|NON|NPA)\)',txt,re.I)
    if not m:return None
    name=' '.join(m.group(1).split())
    party=m.group(2).upper().replace('NPA','NON')
    pct=None; votes=None
    for c in cells:
        if pct is None:
            pm=re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)%\s*',c)
            if pm: pct=float(pm.group(1)); continue
        if votes is None and re.fullmatch(r'\s*[0-9][0-9,]*\s*',c): votes=clean_num(c)
    if votes is None:
        nums=re.findall(r'(?<![.%])\b[0-9][0-9,]*\b',txt)
        if nums:votes=clean_num(nums[-1])
    if votes is None:return None
    return {'name':name,'party':party,'votes':votes,'percent':pct or 0.0}

r=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser'); page=' '.join(soup.stripped_strings)
assert '2026 Primary Election' in page
assert '21 / 21' in page
assert page.lower().count('completely reported')>=3

races=[]; seen=set()
for inp in soup.find_all('input'):
    title=race_title(inp)
    if not title or title in seen:continue
    block=[]
    for el in inp.find_all_next(limit=250):
        if el is not inp and getattr(el,'name',None)=='input':break
        if getattr(el,'name',None)=='tr': block.append(el)
    cands=[]
    for tr in block:
        c=candidate_from_row(tr,title)
        if c and not any(norm(x['name'])==norm(c['name']) for x in cands):cands.append(c)
    if not cands:continue
    total=sum(c['votes'] for c in cands)
    if total<=0:continue
    if not title.startswith(('REP ','DEM ')):
        parties={c['party'] for c in cands}
        if len(parties)==1 and next(iter(parties)) in ('REP','DEM'):title=f"{next(iter(parties))} {title}"
    races.append({'name':title,'candidates':cands});seen.add(title)
assert len(races)>=15, len(races)

state=json.loads(Path('data/statewide.json').read_text()); checks=[]
for sr in state['races']:
    office=sr['office'];party=sr['party']
    lr=next((x for x in races if office_key(x['name'])==office and party_for(x['name'])==party),None)
    assert lr,(office,party,[x['name'] for x in races])
    geo=next(g for g in sr['geography'] if g.get('county')==COUNTY)
    expected={norm(k):int(v) for k,v in geo['votes'].items()}; actual={norm(c['name']):int(c['votes']) for c in lr['candidates']}
    assert set(actual)==set(expected),(office,party,actual,expected)
    assert actual==expected,(office,party,actual,expected)
    checks.append({'office':office,'party':party,'matched':True,'votes':sum(actual.values())})

out={'schemaVersion':2,'county':COUNTY,'election':'2026 Primary Election','electionDate':'2026-08-18','source':'Florida Election Night Reporting - Flagler official summary','sourceUrl':URL,'precinctsReporting':21,'precinctsTotal':21,'coverageComplete':True,'frozenElection':True,'races':races,'validation':{'allPrecinctsReported':True,'allVoteTypesCompletelyReported':True,'statewideOverlapChecks':checks}}
Path('data/flagler.json').write_text(json.dumps(out,indent=2)+'\n')
manifest=json.loads(Path('data/manifest.json').read_text()); ent=manifest['counties'].setdefault(COUNTY,{})
ent.update({'connected':True,'file':'data/flagler.json','sourceUrl':URL,'races':len(races),'adapter':'v2-flagler-official-summary','validationFailed':False,'frozenElection':True,'validatedAgainst':'Flagler official summary + Florida DOS statewide county geography'});ent.pop('error',None)
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('flagler-v2-report.json').write_text(json.dumps({'status':'passed','races':len(races),'precincts':'21/21','statewideChecks':len(checks)},indent=2)+'\n')
print('Flagler v2 built',len(races),'races')
