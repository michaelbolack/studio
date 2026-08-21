#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL='https://results.browardvotes.gov/ENR/browardflenr/239/en/Index_239.html'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)'}
def clean(x):return re.sub(r'\s+',' ',str(x or '')).strip()
def norm(x):return re.sub(r'[^a-z0-9]','',clean(x).lower())
def number(x):
    s=clean(x).replace(',','');return int(s) if re.fullmatch(r'\d+',s) else None

def candidate(cell):
    text=clean(cell)
    m=re.match(r'^(.*?)\s*\((REP|DEM|NPA|NON)\)',text,re.I)
    if m:return clean(m.group(1)),m.group(2).upper().replace('NPA','NON')
    # Nonpartisan vendor rows can omit a party code; take text before duplicated party label.
    text=re.split(r',\s*(?:REPUBLICAN|DEMOCRATIC|NO PARTY|NONPARTISAN)\s+PARTY',text,flags=re.I)[0]
    return clean(text),'NON'

def parse_table(table):
    out=[]
    for tr in table.find_all('tr'):
        cells=[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])]
        if not cells or any('Candidate Name' in c for c in cells):continue
        pct=next((i for i,c in enumerate(cells) if re.fullmatch(r'\d+(?:\.\d+)?%',c)),None)
        if pct is None:continue
        nums=[number(c) for c in cells[:pct] if number(c) is not None]
        if not nums:continue
        namecell=next((c for c in cells if re.search(r'\((REP|DEM|NPA|NON)\)',c,re.I)),None)
        if not namecell:
            # Candidate name is the first meaningful nonnumeric cell in vendor tables.
            namecell=next((c for c in cells if c and not re.fullmatch(r'[-0-9,.%]+',c) and c.lower()!='candidate name'),None)
        if not namecell:continue
        name,party=candidate(namecell)
        if name:out.append((name,party,nums[-1]))
    return out

def context(table):
    contest='';precinct=''
    for s in table.find_all_previous(string=True,limit=180):
        t=clean(s)
        if not contest:
            if 'Contest:' in t:contest=clean(t.split('Contest:',1)[1])
            elif re.match(r'^[A-Z0-9]+\s+-\s+.+',t) and len(t)<180:contest=clean(t.split(' - ',1)[1])
        if not precinct:
            m=re.search(r'(?:Reporting )?Precinct:\s*([A-Z0-9]+)',t,re.I)
            if m:precinct=m.group(1).upper()
            else:
                m=re.match(r'^([A-Z][0-9]{3})\s+-\s+',t)
                if m:precinct=m.group(1)
        if contest and precinct:break
    return contest,precinct

def page_int(text,label):
    m=re.search(re.escape(label)+r'\s+([0-9,]+)',text,re.I)
    return int(m.group(1).replace(',','')) if m else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--statewide',type=Path,default=Path('validation-output/statewide.json'));ap.add_argument('--output',type=Path,default=Path('build/broward-v2.json'));a=ap.parse_args()
    state=json.loads(a.statewide.read_text())
    r=requests.get(URL,headers=HEADERS,timeout=75);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser');page=clean(soup.get_text(' ',strip=True))
    required=['August 18, 2026 Primary Election','Vote By Mail: Complete','Early Votes: Complete','Election Day: Complete','Precincts Reporting 100%']
    missing=[x for x in required if x.lower() not in page.lower()]
    if missing:raise RuntimeError('Broward page completeness markers missing: '+', '.join(missing))
    registered=page_int(page,'Registered Voters');ballots=page_int(page,'Ballots Counted');fully=page_int(page,'Fully Reporting');total_precincts=page_int(page,'Total Precincts')
    if fully!=346 or total_precincts!=346:raise RuntimeError(f'Broward precinct completeness failed: {fully}/{total_precincts}')
    groups={};duplicates=[]
    for table in soup.find_all('table'):
        txt=clean(table.get_text(' ',strip=True))
        if 'Candidate Name' not in txt or 'Total Percentage' not in txt:continue
        rows=parse_table(table)
        if not rows:continue
        contest,precinct=context(table)
        if not contest or not precinct:continue
        # Contest + party is stable even if two contests happen to share candidate names.
        parties=sorted(set(p for _,p,_ in rows));party=parties[0] if len(parties)==1 else 'NON'
        key=(contest,party,tuple(sorted(norm(n) for n,_,_ in rows)))
        g=groups.setdefault(key,{'contest':contest,'party':party,'names':{},'totals':defaultdict(int),'precincts':set()})
        if precinct in g['precincts']:duplicates.append({'contest':contest,'party':party,'precinct':precinct})
        g['precincts'].add(precinct)
        for name,p,v in rows:g['names'][norm(name)]=name;g['totals'][norm(name)]+=v
    if duplicates:raise RuntimeError(f'Duplicate precinct tables detected: {duplicates[:5]}')
    if len(groups)!=28:raise RuntimeError(f'Expected 28 Broward contests, found {len(groups)}')
    races=[]
    for (_contest,_party,_sig),g in groups.items():
        total=sum(g['totals'].values())
        cands=[{'name':g['names'][k],'party':g['party'],'votes':v,'percent':round((v/total*100) if total else 0,2)} for k,v in g['totals'].items()]
        races.append({'name':(('REP ' if g['party']=='REP' else 'DEM ' if g['party']=='DEM' else '')+g['contest']).strip(),'candidates':cands,'precinctsIncluded':len(g['precincts'])})
    # DOS sanity check: all eight statewide primaries must have same candidate sets/leader;
    # Broward's newer county page may include additional provisional ballots, so small nonnegative deltas are allowed.
    checks=[]
    for sr in state['races']:
        geo=next((x for x in sr.get('geography',[]) if x.get('county')=='Broward'),None)
        if not geo:continue
        sig=tuple(sorted(norm(k) for k in geo['votes']))
        match=next((g for (_c,p,s),g in groups.items() if p==sr.get('party') and s==sig),None)
        if not match:raise RuntimeError(f"Missing Broward overlap for {sr.get('party')} {sr.get('office')}")
        vendor={k:int(v) for k,v in match['totals'].items()};dos={norm(k):int(v) for k,v in geo['votes'].items()}
        if any(vendor[k]<dos[k] for k in dos):raise RuntimeError(f"Broward vendor older/lower than DOS for {sr.get('office')} {sr.get('party')}")
        denom=max(1,sum(dos.values()));delta=sum(vendor.values())-sum(dos.values());ratio=delta/denom
        if ratio>0.005:raise RuntimeError(f"Broward/DOS delta too large for {sr.get('office')} {sr.get('party')}: {ratio:.3%}")
        vleader=max(vendor,key=vendor.get);dleader=max(dos,key=dos.get)
        if vleader!=dleader:raise RuntimeError(f"Leader mismatch for {sr.get('office')} {sr.get('party')}")
        checks.append({'office':sr.get('office'),'party':sr.get('party'),'dosTotal':sum(dos.values()),'countyTotal':sum(vendor.values()),'delta':delta,'deltaPct':round(ratio*100,4),'leaderMatch':True})
    if len(checks)<8:raise RuntimeError(f'Expected 8 statewide overlap checks, got {len(checks)}')
    updated=''
    m=re.search(r'Website Updated:\s*([^R]+?)\s+Refresh',page,re.I)
    if m:updated=clean(m.group(1))
    payload={'county':'Broward','election':'2026 Primary Election','electionDate':'2026-08-18','source':'Broward County Supervisor of Elections - official precinct results','sourceUrl':URL,'registeredVoters':registered,'ballotsCast':ballots,'precinctsReporting':fully,'precinctsTotal':total_precincts,'lastUpdated':updated,'coverageComplete':True,'validation':{'contestCount':len(races),'noDuplicatePrecincts':True,'statewideOverlapChecks':checks},'races':races,'generatedAt':datetime.now(timezone.utc).isoformat()}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2)+'\n')
    print(f"PUBLISHABLE: Broward {len(races)} contests, {fully}/{total_precincts}, {len(checks)} DOS sanity checks")
if __name__=='__main__':main()
