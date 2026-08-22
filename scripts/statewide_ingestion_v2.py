#!/usr/bin/env python3
"""Florida statewide adapter using the state-agnostic Election Center core."""
from __future__ import annotations
import argparse,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from election_core import checksum_geographies, make_race_id
BASE="https://floridaelectionwatch.gov"; ELECTION_DATE="2026-08-18"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"}
COUNTIES=["Alachua","Baker","Bay","Bradford","Brevard","Broward","Calhoun","Charlotte","Citrus","Clay","Collier","Columbia","DeSoto","Dixie","Duval","Escambia","Flagler","Franklin","Gadsden","Gilchrist","Glades","Gulf","Hamilton","Hardee","Hendry","Hernando","Highlands","Hillsborough","Holmes","Indian River","Jackson","Jefferson","Lafayette","Lake","Lee","Leon","Levy","Liberty","Madison","Manatee","Marion","Martin","Miami-Dade","Monroe","Nassau","Okaloosa","Okeechobee","Orange","Osceola","Palm Beach","Pasco","Pinellas","Polk","Putnam","Santa Rosa","Sarasota","Seminole","St. Johns","St. Lucie","Sumter","Suwannee","Taylor","Union","Volusia","Wakulla","Walton","Washington"]
ALIASES={"Desoto":"DeSoto"}
CONTESTS=[{"id":"120001","office":"United States Senator","party":"REP","marker":"United States Senator"},{"id":"120002","office":"United States Senator","party":"DEM","marker":"United States Senator"},{"id":"160001","office":"Governor and Lieutenant Governor","party":"REP","marker":"Governor"},{"id":"160002","office":"Governor and Lieutenant Governor","party":"DEM","marker":"Governor"},{"id":"160501","office":"Chief Financial Officer","party":"REP","marker":"Chief Financial Officer"},{"id":"160502","office":"Chief Financial Officer","party":"DEM","marker":"Chief Financial Officer"},{"id":"160801","office":"Commissioner of Agriculture","party":"REP","marker":"Commissioner of Agriculture"},{"id":"160802","office":"Commissioner of Agriculture","party":"DEM","marker":"Commissioner of Agriculture"}]
def integer(v):
 t=(v or '').strip(); d=re.sub(r'[^0-9]','',t)
 if not t or not d: raise ValueError(f'invalid vote cell: {v!r}')
 return int(d)
def fetch_contest(c):
 r=requests.get(f"{BASE}/ContestResultsByCounty/{c['id']}",headers=HEADERS,timeout=30); r.raise_for_status(); s=BeautifulSoup(r.text,'html.parser'); text=' '.join(s.stripped_strings)
 for m in ('2026 Primary Election','August 18, 2026',c['marker']):
  if m.lower() not in text.lower(): raise RuntimeError(f"contest {c['id']} missing marker: {m}")
 party='Republican' if c['party']=='REP' else 'Democrat'
 if party.lower() not in text.lower(): raise RuntimeError(f"contest {c['id']} missing party marker: {party}")
 table=next((t for t in s.find_all('table') if 'County' in ' '.join(t.stripped_strings) and 'Total' in ' '.join(t.stripped_strings) and 'Alachua' in ' '.join(t.stripped_strings) and 'Washington' in ' '.join(t.stripped_strings)),None)
 if table is None: raise RuntimeError(f"contest {c['id']} county table not found")
 rows=[]
 for tr in table.find_all('tr'):
  cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)).strip() for x in tr.find_all(['th','td'])]
  if cells: rows.append(cells)
 hi=next((i for i,row in enumerate(rows) if row and row[0].lower()=='county'),None)
 if hi is None: raise RuntimeError(f"contest {c['id']} County header missing")
 names=[x.strip() for x in rows[hi][1:] if x.strip()]; votes={}; official=None
 if not names: raise RuntimeError(f"contest {c['id']} candidate header missing")
 for row in rows[hi+1:]:
  raw=row[0].strip().rstrip(':'); label=ALIASES.get(raw,raw); cells=row[1:1+len(names)]
  if label in COUNTIES: votes[label]=[integer(v) for v in cells]
  elif raw.lower()=='total': official=[integer(v) for v in cells]
 if official is None: raise RuntimeError(f"contest {c['id']} authoritative Total row missing")
 validation=checksum_geographies(votes,official,expected_geographies=COUNTIES)
 if not validation.coverage_complete:
  missing=sorted(set(COUNTIES)-set(votes)); unexpected=sorted(set(votes)-set(COUNTIES)); raise RuntimeError(f"contest {c['id']} county coverage invalid: {len(votes)}/67; missing={missing}; unexpected={unexpected}")
 if not validation.checksum_passed: raise RuntimeError(f"contest {c['id']} checksum failed: counties={list(validation.calculated_totals)}, ElectionWatch={list(validation.official_totals)}")
 total=sum(official); candidates=[{"name":n,"party":c['party'],"votes":v,"percent":round((v/total*100) if total else 0,2)} for n,v in zip(names,official)]
 return {"id":make_race_id('FL',c['office'],None,c['party'],'2026-primary'),"office":c['office'],"party":c['party'],"scope":{"type":"statewide","state":"FL"},"candidates":candidates,"source":{"authority":"Florida Department of State - Florida Election Watch","url":r.url},"validation":validation.as_json()}
def build():
 races=[fetch_contest(c) for c in CONTESTS]
 return {"schemaVersion":2,"generatedAt":datetime.now(timezone.utc).isoformat(),"election":{"name":"2026 Florida Primary Election","date":ELECTION_DATE,"state":"FL","resultStatus":"Unofficial Election Night Results"},"scope":{"type":"statewide","state":"FL","counties":COUNTIES},"status":"publishable","coverageComplete":True,"countiesIncluded":67,"countyNames":COUNTIES,"mapReady":True,"races":races}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output-dir',type=Path,default=Path('data-v2')); a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True); path=a.output_dir/'statewide.json'
 try: payload=build()
 except Exception as e:
  path.write_text(json.dumps({"schemaVersion":2,"generatedAt":datetime.now(timezone.utc).isoformat(),"status":"withheld","coverageComplete":False,"mapReady":False,"reason":str(e),"races":[]},indent=2)+'\n'); print(f'WITHHELD: {e}',file=sys.stderr); return 1
 path.write_text(json.dumps(payload,indent=2)+'\n'); print('PUBLISHABLE: Florida statewide Election Watch 8 races, 67/67 checksums passed'); return 0
if __name__=='__main__': raise SystemExit(main())
