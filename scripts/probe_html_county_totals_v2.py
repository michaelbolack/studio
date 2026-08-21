#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
import requests
from bs4 import BeautifulSoup,Tag

TARGETS={
 'Broward':'https://results.browardvotes.gov/ENR/browardflenr/239/en/Index_239.html',
 'Seminole':'https://www.livevoterturnout.com/ENR/semflenr/21/en/Index_21.html',
}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)'}
def clean(x): return re.sub(r'\s+',' ',str(x or '')).strip()
def number(x):
    s=re.sub(r'[^0-9]','',clean(x)); return int(s) if s else None

def senate_reference(statewide,county):
    race=next(r for r in statewide['races'] if r.get('office')=='United States Senator' and r.get('party')=='REP')
    geo=next(g for g in race['geography'] if g.get('county')==county)
    return {k:int(v) for k,v in geo['votes'].items()}

def candidate_name(cell):
    text=clean(cell)
    # First visible form is "Name (REP) Name, REPUBLICAN PARTY".
    m=re.match(r'^(.*?)\s*\((REP|DEM|NPA|NON)\)',text,re.I)
    if m:return clean(m.group(1))
    text=re.split(r',\s*(?:REPUBLICAN|DEMOCRATIC|NO PARTY|NONPARTISAN)\s+PARTY',text,flags=re.I)[0]
    return clean(text)

def table_candidates(table):
    rows=[]
    for tr in table.find_all('tr'):
        cells=[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])]
        if not cells or any('Candidate Name' in c for c in cells):continue
        pct_idx=next((i for i,c in enumerate(cells) if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?%',c)),None)
        if pct_idx is None:continue
        numeric=[number(c) for c in cells[:pct_idx] if re.fullmatch(r'[0-9,]+',c)]
        if not numeric:continue
        name_cell=next((c for c in cells if re.search(r'\((REP|DEM|NPA|NON)\)',c,re.I)),None)
        if not name_cell:continue
        rows.append({'name':candidate_name(name_cell),'votes':numeric[-1],'cells':cells})
    return rows

def context(table):
    ancestors=[];node=table
    for _ in range(7):
        node=node.parent
        if not isinstance(node,Tag):break
        attrs={k:(' '.join(v) if isinstance(v,list) else str(v)) for k,v in node.attrs.items() if k in ('id','class','data-contest','data-precinct','data-title')}
        ancestors.append({'tag':node.name,'attrs':attrs,'text':clean(node.get_text(' ',strip=True))[:700]})
    prev=[];node=table
    for _ in range(30):
        node=node.find_previous()
        if not node:break
        if isinstance(node,Tag) and node.name in ('h1','h2','h3','h4','h5','h6','div','span'):
            t=clean(node.get_text(' ',strip=True))
            if t and len(t)<300:prev.append({'tag':node.name,'attrs':{k:(' '.join(v) if isinstance(v,list) else str(v)) for k,v in node.attrs.items() if k in ('id','class')},'text':t})
            if len(prev)>=12:break
    return {'tableAttrs':{k:(' '.join(v) if isinstance(v,list) else str(v)) for k,v in table.attrs.items()},'ancestors':ancestors,'previous':prev}

def main():
    statewide=json.loads(Path('validation-output/statewide.json').read_text())
    output=[]
    for county,url in TARGETS.items():
        ref=senate_reference(statewide,county)
        r=requests.get(url,headers=HEADERS,timeout=45);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
        matches=[];all_candidate_tables=0
        for idx,table in enumerate(soup.find_all('table')):
            txt=clean(table.get_text(' ',strip=True))
            if 'Candidate Name' not in txt or 'Total Percentage' not in txt:continue
            all_candidate_tables+=1
            rows=table_candidates(table);got={x['name']:x['votes'] for x in rows}
            norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
            if {norm(k):v for k,v in got.items()}=={norm(k):v for k,v in ref.items()}:
                matches.append({'tableIndex':idx,'reference':ref,'parsed':got,'rows':rows,'context':context(table)})
        output.append({'county':county,'url':url,'candidateTables':all_candidate_tables,'senateReference':ref,'exactCountyTotalMatches':matches})
    p=Path('validation-output/html-county-total-probe-v2.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'status':'complete','counties':output},indent=2)+'\n')
    print(json.dumps({x['county']:len(x['exactCountyTotalMatches']) for x in output}))
if __name__=='__main__':main()

# trigger v2
