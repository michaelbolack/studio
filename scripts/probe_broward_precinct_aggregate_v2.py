#!/usr/bin/env python3
from __future__ import annotations
import json,re
from collections import defaultdict
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL='https://results.browardvotes.gov/ENR/browardflenr/239/en/Index_239.html'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)'}
def clean(x):return re.sub(r'\s+',' ',str(x or '')).strip()
def norm(x):return re.sub(r'[^a-z0-9]','',clean(x).lower())
def number(x):
    s=clean(x).replace(',','');return int(s) if re.fullmatch(r'\d+',s) else None

def candidate_name(cell):
    m=re.match(r'^(.*?)\s*\((REP|DEM|NPA|NON)\)',clean(cell),re.I)
    return clean(m.group(1)) if m else ''

def parse_table(table):
    rows=[]
    for tr in table.find_all('tr'):
        cells=[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])]
        if not cells or any('Candidate Name' in c for c in cells):continue
        pct=next((i for i,c in enumerate(cells) if re.fullmatch(r'\d+(?:\.\d+)?%',c)),None)
        if pct is None:continue
        nums=[number(c) for c in cells[:pct] if number(c) is not None]
        namecell=next((c for c in cells if re.search(r'\((REP|DEM|NPA|NON)\)',c,re.I)),None)
        if nums and namecell:
            rows.append((candidate_name(namecell),nums[-1]))
    return rows

def contest_context(table):
    # Vendor prints labels such as "A001 - Contest: United States Senator" before each table.
    for s in table.find_all_previous(string=True,limit=180):
        t=clean(s)
        m=re.search(r'(?:Contest:\s*)?(.+?)$',t)
        if 'Contest:' in t:
            return clean(t.split('Contest:',1)[1])
        if re.match(r'^[A-Z0-9]+\s+-\s+.+',t) and len(t)<180:
            return clean(t.split(' - ',1)[1])
    return ''

def precinct_context(table):
    for s in table.find_all_previous(string=True,limit=180):
        t=clean(s)
        m=re.search(r'(?:Reporting )?Precinct:\s*([A-Z0-9]+)',t,re.I)
        if m:return m.group(1).upper()
        m=re.match(r'^([A-Z][0-9]{3})\s+-\s+',t)
        if m:return m.group(1)
    return ''

def main():
    statewide=json.loads(Path('validation-output/statewide.json').read_text())
    refs={}
    for r in statewide['races']:
        geo=next((g for g in r.get('geography',[]) if g.get('county')=='Broward'),None)
        if geo:
            sig=tuple(sorted(norm(k) for k in geo['votes']))
            refs[sig]={'office':r.get('office'),'party':r.get('party'),'votes':{norm(k):int(v) for k,v in geo['votes'].items()}}
    html=requests.get(URL,headers=HEADERS,timeout=60);html.raise_for_status();soup=BeautifulSoup(html.text,'html.parser')
    groups={}
    duplicate_precincts=[]
    examples=[]
    candidate_tables=0
    for idx,table in enumerate(soup.find_all('table')):
        text=clean(table.get_text(' ',strip=True))
        if 'Candidate Name' not in text or 'Total Percentage' not in text:continue
        rows=parse_table(table)
        if not rows:continue
        candidate_tables+=1
        sig=tuple(sorted(norm(n) for n,_ in rows))
        g=groups.setdefault(sig,{'candidateNames':{norm(n):n for n,_ in rows},'totals':defaultdict(int),'precincts':set(),'contexts':defaultdict(int),'tables':0})
        precinct=precinct_context(table);contest=contest_context(table)
        if precinct and precinct in g['precincts']:
            duplicate_precincts.append({'signature':sig,'precinct':precinct,'contest':contest,'tableIndex':idx})
        if precinct:g['precincts'].add(precinct)
        if contest:g['contexts'][contest]+=1
        for n,v in rows:g['totals'][norm(n)]+=v
        g['tables']+=1
        if len(examples)<6:examples.append({'tableIndex':idx,'precinct':precinct,'contest':contest,'rows':rows})
    report=[]
    for sig,g in groups.items():
        ref=refs.get(sig)
        totals=dict(g['totals'])
        report.append({
          'signature':list(sig),'candidateNames':g['candidateNames'],'tables':g['tables'],'precinctCount':len(g['precincts']),
          'topContexts':sorted(g['contexts'].items(),key=lambda x:-x[1])[:5],
          'summedTotals':totals,
          'dosReference':ref,
          'dosMatch':bool(ref and totals==ref['votes'])
        })
    matched=[x for x in report if x['dosMatch']]
    payload={'status':'complete','candidateTables':candidate_tables,'groups':len(report),'dosMatchedGroups':len(matched),'duplicatePrecinctEntries':duplicate_precincts[:50],'examples':examples,'groupReport':report}
    p=Path('validation-output/broward-precinct-aggregate-v2.json');p.write_text(json.dumps(payload,indent=2,default=list)+'\n')
    print(f"tables={candidate_tables} groups={len(report)} DOS-matched={len(matched)} duplicates={len(duplicate_precincts)}")
if __name__=='__main__':main()
