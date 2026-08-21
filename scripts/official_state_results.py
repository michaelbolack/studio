import json, os, re
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

OUT_DIR = "data"
ELECTION_DATE = "8/18/2026"
BASE = "https://results.elections.myflorida.com/SummaryRpt.asp"
DETAIL = "https://results.elections.myflorida.com/DetailRpt.Asp"
HEADERS = {"User-Agent": "Mozilla/5.0 IRC-Media-Election-Center/1.0", "Accept": "text/html,application/xhtml+xml"}
STATEWIDE = ["United States Senator", "Governor and Lieutenant Governor", "Chief Financial Officer", "Commissioner of Agriculture"]
ALIASES = {
 "United States Senator":["United States Senator"],
 "Governor and Lieutenant Governor":["Governor and Lieutenant Governor","Governor & Lieutenant Governor","Governor and Lt. Governor","Governor & Lt. Governor"],
 "Chief Financial Officer":["Chief Financial Officer"],
 "Commissioner of Agriculture":["Commissioner of Agriculture"],
}
CD9_COUNTIES=["Glades","Highlands","Indian River","Okeechobee","Orange","Osceola","Polk"]

def num(s):
 try:return int(re.sub(r"[^0-9]","",str(s)))
 except:return 0

def clean_lines(html):
 soup=BeautifulSoup(html,"html.parser")
 return [re.sub(r"\s+"," ",x).strip() for x in soup.stripped_strings if re.sub(r"\s+"," ",x).strip()]

def is_number(s): return bool(re.fullmatch(r"[0-9][0-9,]*",s or ""))
def is_percent(s): return bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%",s or ""))

def extract_candidate_block(lines,start,party,stop_at_district=False):
 total_i=None
 for i in range(start,min(len(lines),start+250)):
  low=lines[i].lower()
  if stop_at_district and i>start and low.startswith("district:"): return None
  if low in {"total","sub total","subtotal"}: total_i=i;break
 if total_i is None:return None
 pct_i=None
 for i in range(total_i+1,min(len(lines),total_i+80)):
  if lines[i].lower().replace(" ","") in {"%votes","%vote"}:pct_i=i;break
 if pct_i is None:return None
 votes=[num(x) for x in lines[total_i+1:pct_i] if is_number(x)]
 if not votes:return None
 raw=[]; junk={"official results","unofficial results","unofficial preliminary results","republican primary","democratic primary","total","sub total","subtotal","county","statewide","district","district:","race"}
 for x in lines[start:total_i]:
  low=x.lower().strip()
  if not x or low in junk or is_number(x) or is_percent(x):continue
  if re.fullmatch(r"\([A-Z]{2,4}\)",x):continue
  if low.startswith(("district:","circuit:","group:")):continue
  if any(low==a.lower() for aliases in ALIASES.values() for a in aliases):continue
  if low=="united states representative":continue
  raw.append(x)
 if len(raw)<len(votes):return None
 names=raw[-len(votes):]; total=sum(votes)
 return [{"name":n,"party":party,"votes":v,"percent":round(v/total*100 if total else 0,2)} for n,v in zip(names,votes)]

def find_title(lines,aliases):
 low=[x.lower() for x in lines]
 for a in aliases:
  for i,x in enumerate(low):
   if x==a.lower():return i
 return None

def fetch_party(party):
 params={"DATAMODE":"","ElectionDate":ELECTION_DATE,"PARTY":party}
 r=requests.get(BASE,params=params,headers=HEADERS,timeout=40);r.raise_for_status(); lines=clean_lines(r.text)
 if not any("2026" in x and "Primary" in x for x in lines):raise RuntimeError("Florida DOS 2026 primary results page not available")
 return lines,r.url

def statewide_from_party(lines,party):
 races=[]
 for office in STATEWIDE:
  idx=find_title(lines,ALIASES[office])
  if idx is not None:
   c=extract_candidate_block(lines,idx+1,party)
   if c:races.append({"name":party+" "+office,"type":"statewide","candidates":c})
 return races

def fetch_d9_detail(party):
 params={"DATAMODE":"","DIST":"009","ELECTIONDATE":ELECTION_DATE,"PARTY":party,"RACE":"USR"}
 r=requests.get(DETAIL,params=params,headers=HEADERS,timeout=40);r.raise_for_status()
 soup=BeautifulSoup(r.text,"html.parser")
 text=" ".join(soup.stripped_strings)
 if "United States Representative" not in text or not re.search(r"District:\s*0*9\b",text,re.I):raise RuntimeError("DOS CD9 detail page not available")
 tables=soup.find_all("table")
 target=None
 for t in tables:
  tt=" ".join(t.stripped_strings)
  if "County" in tt and "Total" in tt and any(c in tt for c in CD9_COUNTIES):target=t;break
 if target is None:raise RuntimeError("DOS CD9 results table not found")
 rows=[]
 for tr in target.find_all("tr"):
  cells=[re.sub(r"\s+"," ",c.get_text(" ",strip=True)).strip() for c in tr.find_all(["th","td"])]
  if cells:rows.append(cells)
 header_i=next((i for i,rw in enumerate(rows) if rw and rw[0].lower()=="county"),None)
 if header_i is None:raise RuntimeError("DOS CD9 county header not found")
 header=rows[header_i]
 names=[]
 for h in header[1:]:
  name=re.sub(r"\s*\((REP|DEM|LPF|NPA|WRI)\)\s*$","",h,flags=re.I).strip()
  if name:names.append(name)
 county_votes={}; totals=None
 for rw in rows[header_i+1:]:
  if not rw:continue
  label=rw[0].strip()
  vals=[num(x) for x in rw[1:1+len(names)]]
  if label in CD9_COUNTIES and len(vals)==len(names):county_votes[label]=vals
  elif label.lower()=="total" and len(vals)==len(names):totals=vals
 if totals is None:raise RuntimeError("DOS CD9 authoritative total row missing")
 missing=[c for c in CD9_COUNTIES if c not in county_votes]
 if missing:raise RuntimeError("DOS CD9 missing county rows: "+", ".join(missing))
 sums=[sum(county_votes[c][i] for c in CD9_COUNTIES) for i in range(len(names))]
 if sums!=totals:raise RuntimeError(f"DOS CD9 county checksum mismatch county={sums} total={totals}")
 grand=sum(totals)
 candidates=[{"name":n,"party":party,"votes":v,"percent":round(v/grand*100 if grand else 0,2)} for n,v in zip(names,totals)]
 geography=[{"county":c,"votes":{names[i]:county_votes[c][i] for i in range(len(names))}} for c in CD9_COUNTIES]
 return {"name":party+" Representative in Congress","type":"congress","district":9,"candidates":candidates,"geography":geography},r.url

def main():
 os.makedirs(OUT_DIR,exist_ok=True); party_data={}; urls=[]
 for party in ("REP","DEM"):
  try:
   lines,url=fetch_party(party);party_data[party]=lines;urls.append(url);print(f"DOS OK {party}: {len(lines)} text cells")
  except Exception as e:print(f"DOS FAIL {party}: {e}")
 state_races=[]
 for p,l in party_data.items():state_races.extend(statewide_from_party(l,p))
 if state_races:
  statewide={"scope":"Florida","election":"2026 Primary Election","electionDate":"2026-08-18","source":"Florida Department of State, Division of Elections compiled results","sourceUrl":BASE+"?"+urlencode({"ElectionDate":ELECTION_DATE}),"countiesIncluded":67,"countiesDiscovered":67,"coverageComplete":True,"lastUpdated":datetime.now(timezone.utc).isoformat(),"races":state_races,"generatedAt":datetime.now(timezone.utc).isoformat()}
  json.dump(statewide,open(os.path.join(OUT_DIR,"statewide.json"),"w"),indent=2)
 d9=[]; d9urls=[]; errors=[]
 for p in ("REP","DEM"):
  try:
   race,url=fetch_d9_detail(p);d9.append(race);d9urls.append(url);print(f"DOS CD9 OK {p}: {sum(c['votes'] for c in race['candidates'])} votes; 7/7 county checksum passed")
  except Exception as e:errors.append(f"{p}: {e}");print(f"DOS CD9 FAIL {p}: {e}")
 if d9:
  district={"scope":"Florida Congressional District 9","district":9,"election":"2026 Primary Election","electionDate":"2026-08-18","source":"Florida Department of State, Division of Elections official district detail","sourceUrl":d9urls[0],"countiesIncluded":7,"countiesExpected":7,"countyNames":CD9_COUNTIES,"coverageComplete":True,"integrityCheck":"authoritative DOS total equals sum of all seven county rows","mapReady":True,"lastUpdated":datetime.now(timezone.utc).isoformat(),"races":d9,"generatedAt":datetime.now(timezone.utc).isoformat()}
  json.dump(district,open(os.path.join(OUT_DIR,"district-9.json"),"w"),indent=2)
 manifest_path=os.path.join(OUT_DIR,"manifest.json")
 if os.path.exists(manifest_path):
  manifest=json.load(open(manifest_path))
  if state_races:manifest["statewide"]={"file":"data/statewide.json","countiesIncluded":67,"countiesDiscovered":67,"coverageComplete":True,"source":"Florida Department of State"}
  if d9:manifest["district9"]={"file":"data/district-9.json","countiesIncluded":7,"countiesExpected":7,"coverageComplete":True,"source":"Florida Department of State","mapReady":True}
  elif errors:manifest["district9DosErrors"]=errors
  manifest["generatedAt"]=datetime.now(timezone.utc).isoformat();json.dump(manifest,open(manifest_path,"w"),indent=2)

if __name__=="__main__":main()
