#!/usr/bin/env python3
"""Direct Florida Election Watch headline result collector for Nov. 3, 2026.

Uses Florida Election Watch contest pages directly for statewide/federal/multicounty
headline races, avoiding dependency on all 67 county adapters.
"""
from __future__ import annotations

import json, re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
HEADERS={"User-Agent":"Mozilla/5.0 IRC-Media-Election-Center/1.0","Accept":"text/html,application/xhtml+xml"}
PAGES={
 "federal":"https://floridaelectionwatch.gov/FederalOffices",
 "state":"https://floridaelectionwatch.gov/StateOffices/",
 "house":"https://floridaelectionwatch.gov/DistrictOffices/StateRepresentative",
 "judicial":"https://floridaelectionwatch.gov/judicialoffices",
 "amendments":"https://floridaelectionwatch.gov/Amendments",
}
RACES=[
 {"scope":"florida","name":"United States Senator","page":"federal","need":["Ashley Moody","Angie Nixon"],"allowed":["Ashley Moody","Angie Nixon","Neil J. Gillespie"]},
 {"scope":"florida","name":"Governor and Lieutenant Governor","page":"state","need":["Byron Donalds","David Jolly"],"allowed":["Byron Donalds","David Jolly","Scott Eckhard Jewett","Charles Burkett","Frank J. Russo","Moliere","Dean Ocean Abrams","Jeffrey Peter","Write-in","Kathy Anderson","Erik Morris"]},
 {"scope":"florida","name":"Attorney General","page":"state","need":["James Uthmeier","Jose Javier Rodriguez"],"allowed":["James Uthmeier","Jose Javier Rodriguez"]},
 {"scope":"florida","name":"Chief Financial Officer","page":"state","need":["Blaise Ingoglia","Annette Taddeo"],"allowed":["Blaise Ingoglia","Annette Taddeo"]},
 {"scope":"florida","name":"Commissioner of Agriculture","page":"state","need":["Wilton Simpson","Joey Mendoza Atkins"],"allowed":["Wilton Simpson","Joey Mendoza Atkins","Kyle"]},
 {"scope":"district","name":"Representative in Congress, District 9","page":"federal","need":["Dan Green","Darren Soto"],"allowed":["Dan Green","Darren Soto"],"countiesIncluded":7},
 {"scope":"district","name":"State Representative, District 34","page":"house","need":["Robert Brackett","Jordyn Guadalupe Balderas"],"allowed":["Robert Brackett","Jordyn Guadalupe Balderas"],"countiesIncluded":2},
 {"scope":"florida","name":"Shall Justice Carlos G. Muñiz be retained in Office?","page":"judicial","title":"Shall Justice Carlos G. Muñiz be retained in Office?","need":["Yes","No"],"allowed":["Yes","No"]},
 {"scope":"florida","name":"Budget Stabilization Fund","page":"amendments","title":"Budget Stabilization Fund","need":["Yes for Approval","No for Rejection"],"allowed":["Yes for Approval","No for Rejection"]},
 {"scope":"florida","name":"Exemption of Tangible Personal Property on Agricultural Land From Taxation","page":"amendments","title":"Exemption of Tangible Personal Property on Agricultural Land From Taxation","need":["Yes for Approval","No for Rejection"],"allowed":["Yes for Approval","No for Rejection"]},
 {"scope":"florida","name":"Increased Homestead Exemption; Lower Cap On Increases In Non-Homestead Property Assessments","page":"amendments","title":"Increased Homestead Exemption; Lower Cap On Increases In Non-Homestead Property Assessments","need":["Yes for Approval","No for Rejection"],"allowed":["Yes for Approval","No for Rejection"]},
]

def n(s):
 s=re.sub(r"[^0-9]","",s or "")
 return int(s) if s else 0

def clean(s):
 return re.sub(r"\s+"," ",s or "").strip()

def canonical(name):
 raw=clean(name)
 rules=[
  ("Ashley Moody","Ashley Moody"),("Angie Nixon","Angie Nixon"),("Neil J. Gillespie","Neil J. Gillespie"),
  ("Byron Donalds","Byron Donalds"),("David Jolly","David Jolly"),("Scott Eckhard Jewett","Scott Eckhard Jewett"),
  ("Charles Burkett","Charles Burkett"),("Frank J. Russo","Frank J. Russo"),("Moliere","Moliere \"Moe\" Dimanche"),
  ("Dean Ocean Abrams","Dean Ocean Abrams"),("Jeffrey Peter","Jeffrey Peter \"Dr. Jeff\" Datto"),
  ("Kathy Anderson","Kathy Anderson"),("Erik Morris","Erik Morris"),("James Uthmeier","James Uthmeier"),
  ("Jose Javier Rodriguez","Jose Javier Rodriguez"),("Blaise Ingoglia","Blaise Ingoglia"),("Annette Taddeo","Annette Taddeo"),
  ("Wilton Simpson","Wilton Simpson"),("Joey Mendoza Atkins","Joey Mendoza Atkins"),("Kyle","Kyle \"KC\" Gibson"),
  ("Dan Green","Dan Green"),("Darren Soto","Darren Soto"),("Robert Brackett","Robert Brackett"),
  ("Jordyn Guadalupe Balderas","Jordyn Guadalupe Balderas"),
 ]
 for needle,out in rules:
  if needle.lower() in raw.lower(): return out
 if "write" in raw.lower(): return "Write-in"
 return raw

def party_from_text(text):
 m=re.search(r"\b(REP|DEM|NPA|LPF|WRI|NON|NOP)\b",text or "",re.I)
 return m.group(1).upper() if m else "NON"

def fetch_pages():
 out={}
 for key,url in PAGES.items():
  r=requests.get(url,headers=HEADERS,timeout=40)
  r.raise_for_status()
  if "2026 General Election" not in r.text and "November 3, 2026" not in r.text:
   raise RuntimeError(f"{key} page is not the 2026 General Election")
  out[key]=BeautifulSoup(r.text,"html.parser")
 return out

def table_for(soup,required,title=None):
 if title:
  target=soup.find(string=lambda x: isinstance(x,str) and title.lower() in clean(x).lower())
  if target:
   table=target.find_parent().find_next("table") if target.find_parent() else None
   if table:
    return table
 for table in soup.find_all("table"):
  text=clean(table.get_text(" ",strip=True))
  if all(x.lower() in text.lower() for x in required):
   return table
 raise RuntimeError("result table not found for "+(title or ", ".join(required)))

def parse_table(table,spec):
 candidates=[]
 for tr in table.find_all("tr"):
  cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
  if not cells: continue
  joined=" | ".join(cells)
  matched=None
  for token in spec["allowed"]:
   if token.lower() in joined.lower():
    matched=token;break
  if not matched: continue
  name=canonical(joined)
  nums=[]
  for cell in cells:
   if re.fullmatch(r"[0-9][0-9,]*",cell):
    nums.append(n(cell))
  votes=max(nums) if nums else 0
  if name and votes>=0:
   candidates.append({"name":name,"party":party_from_text(joined),"votes":votes})
 seen={}
 for c in candidates:
  seen[c["name"]]=c
 candidates=list(seen.values())
 required=[canonical(x) for x in spec["need"]]
 names={c["name"] for c in candidates}
 if not all(x in names for x in required):
  raise RuntimeError(f"required candidates missing for {spec['name']}: {sorted(names)}")
 total=sum(c["votes"] for c in candidates)
 if total<=0: raise RuntimeError("zero total for "+spec["name"])
 for c in candidates:c["percent"]=round(c["votes"]/total*100,2)
 return candidates,total

def main():
 DATA.mkdir(exist_ok=True)
 soups=fetch_pages()
 now=datetime.now(timezone.utc).isoformat()
 races=[]
 for spec in RACES:
  table=table_for(soups[spec["page"]],spec["need"],spec.get("title"))
  candidates,total=parse_table(table,spec)
  race={
   "scope":spec["scope"],"name":spec["name"],"status":"unofficial","totalVotes":total,
   "candidates":candidates,"sourceUrl":PAGES[spec["page"]],"sourceFetchedAt":now,
  }
  if "countiesIncluded" in spec: race["countiesIncluded"]=spec["countiesIncluded"]
  races.append(race)

 headline={"electionId":"2026-fl-general","electionDate":"2026-11-03","fetchedAt":now,"status":"unofficial","races":races}
 (DATA/"official-headline-results.json").write_text(json.dumps(headline,indent=2)+"\n")

 statewide_races=[]
 for r in races:
  if r["scope"]=="florida":
   statewide_races.append({"name":r["name"],"type":"statewide","candidates":r["candidates"]})
 statewide={
  "scope":"Florida","election":"2026 General Election","electionDate":"2026-11-03",
  "source":"Florida Department of State - Florida Election Watch direct contest totals",
  "sourceUrl":"https://floridaelectionwatch.gov/","countiesIncluded":67,"countiesDiscovered":67,
  "coverageComplete":True,"displayStatus":"complete","lastUpdated":now,"generatedAt":now,"races":statewide_races,
 }
 (DATA/"statewide.json").write_text(json.dumps(statewide,indent=2)+"\n")

 cd9=next(r for r in races if r["name"]=="Representative in Congress, District 9")
 district9={
  "scope":"Florida Congressional District 9","district":9,"election":"2026 General Election","electionDate":"2026-11-03",
  "source":"Florida Department of State - Florida Election Watch direct contest total",
  "sourceUrl":PAGES["federal"],"countiesIncluded":7,"countiesExpected":7,"coverageComplete":True,
  "displayStatus":"complete","lastUpdated":now,"generatedAt":now,
  "races":[{"name":"Representative in Congress District 9","type":"congress","district":9,"candidates":cd9["candidates"]}],
 }
 (DATA/"district-9.json").write_text(json.dumps(district9,indent=2)+"\n")
 print(json.dumps({"races":len(races),"cd9Total":cd9["totalVotes"],"statewide":len(statewide_races)},indent=2))

if __name__=="__main__":
 main()
