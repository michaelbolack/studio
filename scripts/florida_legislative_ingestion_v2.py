#!/usr/bin/env python3
"""Florida legislative adapter for Election Center v2.

Discovers contested State Senate and State Representative primaries from Florida
Election Watch. Every race is built through the state-agnostic district core and
is withheld unless component county totals reconcile to the official aggregate.
"""
from __future__ import annotations
import argparse,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from election_core import build_district_race
BASE='https://floridaelectionwatch.gov'; ELECTION_DATE='2026-08-18'
INDEXES=[('StateSenator','State Senator','state-senate-district'),('StateRepresentative','State Representative','state-house-district')]
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'}
ALIASES={'Desoto':'DeSoto'}
def integer(v):
 t=(v or '').strip(); d=re.sub(r'[^0-9]','',t)
 if not t or not d: raise ValueError(f'invalid vote cell: {v!r}')
 return int(d)
def discover(index_slug,office_prefix,district_type):
 url=f'{BASE}/DistrictOffices/{index_slug}'; r=requests.get(url,headers=HEADERS,timeout=30); r.raise_for_status(); s=BeautifulSoup(r.text,'html.parser'); text=' '.join(s.stripped_strings)
 for marker in ('2026 Primary Election','August 18, 2026',office_prefix):
  if marker.lower() not in text.lower(): raise RuntimeError(f'{office_prefix} index missing marker: {marker}')
 contests=[]; seen=set()
 for a in s.find_all('a'):
  label=' '.join(a.stripped_strings); href=a.get('href') or ''
  if 'Contest Results by County' not in label or '/ContestResultsByCounty/' not in href: continue
  district=None; party=None
  for prev in a.find_all_previous(string=True,limit=60):
   t=re.sub(r'\s+',' ',str(prev)).strip()
   if party is None:
    if t=='Republican': party='REP'
    elif t=='Democrat': party='DEM'
   m=re.fullmatch(re.escape(office_prefix)+r', District\s+(\d+)',t,re.I)
   if m: district=m.group(1); break
  if district is None or party is None: raise RuntimeError(f'could not identify {office_prefix} district/party for {href}')
  key=(district,party)
  if key in seen: raise RuntimeError(f'duplicate {office_prefix} contest: District {district} {party}')
  seen.add(key); contests.append({'district':district,'party':party,'districtType':district_type,'office':office_prefix,'url':urljoin(BASE,href)})
 return contests
def fetch_contest(c):
 r=requests.get(c['url'],headers=HEADERS,timeout=30); r.raise_for_status(); s=BeautifulSoup(r.text,'html.parser'); text=' '.join(s.stripped_strings)
 for marker in ('2026 Primary Election','August 18, 2026',f"{c['office']}, District {c['district']}",'Republican' if c['party']=='REP' else 'Democrat'):
  if marker.lower() not in text.lower(): raise RuntimeError(f"legislative contest missing marker: {marker}")
 table=next((t for t in s.find_all('table') if 'County' in ' '.join(t.stripped_strings) and 'Total' in ' '.join(t.stripped_strings)),None)
 if table is None: raise RuntimeError(f"{c['office']} District {c['district']} county table not found")
 rows=[]
 for tr in table.find_all('tr'):
  cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)).strip() for x in tr.find_all(['th','td'])]
  if cells: rows.append(cells)
 hi=next((i for i,row in enumerate(rows) if row and row[0].lower()=='county'),None)
 if hi is None: raise RuntimeError('County header missing')
 names=[x.strip() for x in rows[hi][1:] if x.strip()]; votes={}; official=None
 if not names: raise RuntimeError('candidate header missing')
 for row in rows[hi+1:]:
  raw=row[0].strip().rstrip(':'); label=ALIASES.get(raw,raw); cells=row[1:1+len(names)]
  if raw.lower()=='total': official=[integer(v) for v in cells]
  elif raw and len(cells)==len(names):
   try: parsed=[integer(v) for v in cells]
   except ValueError: continue
   if label in votes: raise RuntimeError(f'duplicate county row: {label}')
   votes[label]=parsed
 if official is None: raise RuntimeError('authoritative Total row missing')
 return build_district_race(state='FL',district_type=c['districtType'],district=c['district'],office=c['office'],party=c['party'],election_key='2026-primary',candidate_names=names,geography_votes=votes,official_totals=official,source_authority='Florida Department of State - Florida Election Watch',source_url=r.url)
def build():
 discovered=[]
 for slug,office,dtype in INDEXES: discovered.extend(discover(slug,office,dtype))
 if not discovered: raise RuntimeError('Florida Election Watch exposed no contested legislative primaries')
 races=[fetch_contest(c) for c in discovered]
 return {'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'election':{'name':'2026 Florida Primary Election','date':ELECTION_DATE,'state':'FL','resultStatus':'Unofficial Election Night Results'},'scope':{'type':'state-legislative','state':'FL'},'status':'publishable','coverageComplete':True,'mapReady':True,'contestsDiscovered':len(discovered),'races':races}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output-dir',type=Path,default=Path('data-v2')); a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True); path=a.output_dir/'legislative.json'
 try: payload=build()
 except Exception as e:
  path.write_text(json.dumps({'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'status':'withheld','coverageComplete':False,'mapReady':False,'reason':str(e),'races':[]},indent=2)+'\n'); print(f'WITHHELD: {e}',file=sys.stderr); return 1
 path.write_text(json.dumps(payload,indent=2)+'\n'); print(f"PUBLISHABLE: {payload['contestsDiscovered']} Florida legislative contests checksummed"); return 0
if __name__=='__main__': raise SystemExit(main())
