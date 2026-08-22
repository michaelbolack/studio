#!/usr/bin/env python3
"""Florida U.S. House adapter using the state-agnostic Election Center core."""
from __future__ import annotations
import argparse,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from election_core import DistrictScope, checksum_geographies, make_race_id
BASE='https://floridaelectionwatch.gov'; INDEX_URL=f'{BASE}/FederalOffices/USRepresentative'; ELECTION_DATE='2026-08-18'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'}
ALIASES={'Desoto':'DeSoto'}
def integer(v):
 t=(v or '').strip(); d=re.sub(r'[^0-9]','',t)
 if not t or not d: raise ValueError(f'invalid vote cell: {v!r}')
 return int(d)
def discover_contests():
 r=requests.get(INDEX_URL,headers=HEADERS,timeout=30); r.raise_for_status(); s=BeautifulSoup(r.text,'html.parser'); text=' '.join(s.stripped_strings)
 for m in ('2026 Primary Election','August 18, 2026','U.S. Representative'):
  if m.lower() not in text.lower(): raise RuntimeError(f'U.S. House index missing marker: {m}')
 contests=[]; seen=set()
 for a in s.find_all('a'):
  label=' '.join(a.stripped_strings); href=a.get('href') or ''
  if 'Contest Results by County' not in label or '/ContestResultsByCounty/' not in href: continue
  district=None; party=None
  for prev in a.find_all_previous(string=True,limit=80):
   t=re.sub(r'\s+',' ',str(prev)).strip()
   if party is None:
    if t=='Republican': party='REP'
    elif t=='Democrat': party='DEM'
   m=re.fullmatch(r'Representative in Congress, District\s+(\d+)',t,re.I)
   if m: district=int(m.group(1)); break
  if district is None or party is None: raise RuntimeError(f'could not identify district/party for {href}')
  key=(district,party)
  if key in seen: raise RuntimeError(f'duplicate U.S. House contest: District {district} {party}')
  seen.add(key); contests.append({'contestId':href.rstrip('/').split('/')[-1],'district':district,'party':party,'url':urljoin(BASE,href)})
 if not contests: raise RuntimeError('Election Watch exposed no contested U.S. House primaries')
 return sorted(contests,key=lambda x:(x['district'],x['party']))
def fetch_contest(c):
 r=requests.get(c['url'],headers=HEADERS,timeout=30); r.raise_for_status(); s=BeautifulSoup(r.text,'html.parser'); text=' '.join(s.stripped_strings)
 for m in ('2026 Primary Election','August 18, 2026',f"Representative in Congress, District {c['district']}",'Republican' if c['party']=='REP' else 'Democrat'):
  if m.lower() not in text.lower(): raise RuntimeError(f"contest {c['contestId']} missing marker: {m}")
 table=next((t for t in s.find_all('table') if 'County' in ' '.join(t.stripped_strings) and 'Total' in ' '.join(t.stripped_strings)),None)
 if table is None: raise RuntimeError(f"contest {c['contestId']} county table not found")
 rows=[]
 for tr in table.find_all('tr'):
  cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)).strip() for x in tr.find_all(['th','td'])]
  if cells: rows.append(cells)
 hi=next((i for i,row in enumerate(rows) if row and row[0].lower()=='county'),None)
 if hi is None: raise RuntimeError(f"contest {c['contestId']} County header missing")
 names=[x.strip() for x in rows[hi][1:] if x.strip()]; county_votes={}; official=None
 if not names: raise RuntimeError(f"contest {c['contestId']} candidate header missing")
 for row in rows[hi+1:]:
  raw=row[0].strip().rstrip(':'); label=ALIASES.get(raw,raw); cells=row[1:1+len(names)]
  if raw.lower()=='total': official=[integer(v) for v in cells]
  elif raw and len(cells)==len(names):
   try: parsed=[integer(v) for v in cells]
   except ValueError: continue
   if label in county_votes: raise RuntimeError(f"contest {c['contestId']} duplicate county row: {label}")
   county_votes[label]=parsed
 if not county_votes: raise RuntimeError(f"contest {c['contestId']} has no county vote rows")
 if official is None: raise RuntimeError(f"contest {c['contestId']} authoritative Total row missing")
 validation=checksum_geographies(county_votes,official)
 if not validation.publishable: raise RuntimeError(f"contest {c['contestId']} checksum failed: counties={list(validation.calculated_totals)}, ElectionWatch={list(validation.official_totals)}")
 scope=DistrictScope('FL','congressional-district',str(c['district']))
 grand=sum(official); candidates=[{'name':n,'party':c['party'],'votes':v,'percent':round((v/grand*100) if grand else 0,2)} for n,v in zip(names,official)]
 return {'id':make_race_id('FL','US House',scope,c['party'],'2026-primary'),'office':'United States Representative','district':c['district'],'party':c['party'],'scope':scope.as_json(),'candidates':candidates,'countyNames':list(county_votes),'countiesIncluded':len(county_votes),'source':{'authority':'Florida Department of State - Florida Election Watch','url':r.url},'validation':validation.as_json()}
def build():
 discovered=discover_contests(); races=[fetch_contest(c) for c in discovered]
 return {'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'election':{'name':'2026 Florida Primary Election','date':ELECTION_DATE,'state':'FL','resultStatus':'Unofficial Election Night Results'},'scope':{'type':'congressional','state':'FL'},'status':'publishable','coverageComplete':True,'mapReady':True,'contestsDiscovered':len(discovered),'districtsCovered':sorted({r['district'] for r in races}),'races':races}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output-dir',type=Path,default=Path('data-v2')); a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True); path=a.output_dir/'congressional.json'
 try: payload=build()
 except Exception as e:
  path.write_text(json.dumps({'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'status':'withheld','coverageComplete':False,'mapReady':False,'reason':str(e),'races':[]},indent=2)+'\n'); print(f'WITHHELD: {e}',file=sys.stderr); return 1
 path.write_text(json.dumps(payload,indent=2)+'\n'); print(f"PUBLISHABLE: {payload['contestsDiscovered']} Florida U.S. House primary contests checksummed"); return 0
if __name__=='__main__': raise SystemExit(main())
