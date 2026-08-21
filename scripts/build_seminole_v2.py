#!/usr/bin/env python3
# isolated build; promotes only after official-page and DOS validation
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup
URL='https://www.livevoterturnout.com/ENR/semflenr/21/en/Index_21.html'; COUNTY='Seminole'
def undouble(s):
    s=' '.join(str(s or '').split()); w=s.split()
    if len(w)%2==0 and w[:len(w)//2]==w[len(w)//2:]: return ' '.join(w[:len(w)//2])
    return s
def party_for(n): return 'REP' if n.startswith('REP ') else 'DEM' if n.startswith('DEM ') else 'NON'
def find_contest(t):
    for prev in t.find_all_previous(limit=40):
        txt=' '.join(prev.stripped_strings)
        if not txt or len(txt)>350: continue
        m=re.search(r'Contest:\s*(.+?),\s*Precincts Reported:\s*(\d+)\s*of\s*(\d+)',txt,re.I)
        if m:return m.group(1).strip(),int(m.group(2)),int(m.group(3))
        m=re.search(r'^(.+?)\s+Precinct Reported:\s*(\d+)\s*of\s*(\d+)',txt,re.I)
        if m:return m.group(1).strip(),int(m.group(2)),int(m.group(3))
def norm(s):return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def office_key(n):
    s=re.sub(r'^(REP|DEM)\s+','',n,flags=re.I).lower()
    if 'united states senator' in s:return 'United States Senator'
    if s=='governor' or 'governor and lieutenant' in s:return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s:return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s:return 'Commissioner of Agriculture'
r=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'});r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser');page=' '.join(soup.stripped_strings)
assert '2026 Primary Election' in page and 'Official Election Results' in page
races=[];seen=set();pts=[]
for t in soup.find_all('table'):
    if t.get('id')=='ModalSelectOptions':continue
    ct=find_contest(t)
    if not ct:continue
    name,reported,total=ct;cands=[]
    for tr in t.find_all('tr'):
        cells=[' '.join(c.stripped_strings) for c in tr.find_all(['th','td'])]
        if len(cells)<5 or cells[1].strip().lower()=='candidate name':continue
        nm=undouble(cells[1]);vv=re.sub(r'[^0-9]','',cells[3]);pc=re.sub(r'[^0-9.]','',cells[4])
        if nm and vv:cands.append({'name':nm,'party':party_for(name),'votes':int(vv),'percent':float(pc or 0)})
    if not cands:continue
    key=(name,tuple((c['name'],c['votes']) for c in cands))
    if key in seen:continue
    seen.add(key);races.append({'name':name,'candidates':cands,'precinctsReporting':reported,'precinctsTotal':total});pts.append((name,reported,total))
assert races and all(a==b and b>0 for _,a,b in pts),pts
assert all(a==b==82 for n,a,b in pts if any(x in n for x in ['United States Senator','Governor','Chief Financial Officer','Commissioner of Agriculture'])),pts
state=json.loads(Path('data/statewide.json').read_text());checks=[]
for sr in state['races']:
    office=sr['office'];party=sr['party'];lr=next((x for x in races if office_key(x['name'])==office and party_for(x['name'])==party),None);assert lr,(office,party)
    geo=next(g for g in sr['geography'] if g.get('county')==COUNTY);expected={norm(k):int(v) for k,v in geo['votes'].items()};actual={norm(c['name']):int(c['votes']) for c in lr['candidates']}
    st=sum(expected.values());ct=sum(actual.values());delta=ct-st;dp=abs(delta)/st*100 if st else 0
    assert delta>=0 and dp<0.25,(office,party,delta,dp)
    assert max(actual.values())>=max(expected.values())
    checks.append({'office':office,'party':party,'dosVotes':st,'countyVotes':ct,'delta':delta,'deltaPct':round(dp,4)})
out={'schemaVersion':2,'county':COUNTY,'election':'2026 Primary Election','electionDate':'2026-08-18','source':'Seminole County Supervisor of Elections - Official Election Results','sourceUrl':URL,'precinctsReporting':82,'precinctsTotal':82,'coverageComplete':True,'frozenElection':True,'races':races,'validation':{'sourcePageOfficial':True,'allContestsFullyReported':True,'statewideOverlapChecks':checks}}
Path('data/seminole.json').write_text(json.dumps(out,indent=2)+'\n');manifest=json.loads(Path('data/manifest.json').read_text());ent=manifest['counties'].setdefault(COUNTY,{});ent.update({'connected':True,'file':'data/seminole.json','sourceUrl':URL,'races':len(races),'adapter':'v2-seminole-official-html','validationFailed':False,'frozenElection':True,'validatedAgainst':'Seminole official HTML + Florida DOS statewide sanity checks'});ent.pop('error',None);Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');Path('seminole-v2-report.json').write_text(json.dumps({'status':'passed','races':len(races),'countywidePrecincts':'82/82','allContestsFullyReported':True,'statewideChecks':len(checks)},indent=2)+'\n');print('Seminole v2 built:',len(races),'races')
