"""Parse rendered AlabamaVotes county election-night results text."""
from __future__ import annotations
import re
from typing import Any

BOXES=re.compile(r"Boxes Reported:\s*([0-9]+(?:\.[0-9]+)?)%",re.I)
CANDIDATE=re.compile(r"^(.+?)\s+\(([A-Z]{2,5})\)\s+(?:Image:\s*progressBar\s+)?([0-9]+(?:\.[0-9]+)?)%\s+([0-9][0-9,]*)$")
DISTRICT=re.compile(r"(?:CONGRESSIONAL DISTRICT|DISTRICT NO\.?|DISTRICT)\s*(\d+)",re.I)

def _scope(title:str)->str:
    u=title.upper()
    if "UNITED STATES REPRESENTATIVE" in u: return "congressional"
    if "STATE SENATE" in u or "STATE REPRESENTATIVE" in u or "HOUSE OF REPRESENTATIVES" in u: return "legislative"
    if any(x in u for x in ("COUNTY","SHERIFF","BOARD OF EDUCATION")): return "local"
    return "statewide"

def parse_alabama_county_text(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip(): raise ValueError("Alabama county results text is required")
    m=BOXES.search(text)
    if not m: raise ValueError("Boxes Reported is required")
    pct=float(m.group(1))
    if pct<0 or pct>100: raise ValueError("invalid Boxes Reported percentage")
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    contests=[]; current=None
    for line in lines:
        cm=CANDIDATE.match(line)
        if cm and current is not None:
            current["candidates"].append({"name":cm.group(1).strip(),"party":cm.group(2),"votes":int(cm.group(4).replace(",",""))})
            continue
        if line in {"Percent Votes","Page: 1 of 1","<< Prev Next >>","<< Prev   Next >>"}: continue
        if line.startswith(("Total Ballots Cast:","Election results from","The election results presented","Unofficial Election Night Results","You may browse")): continue
        if re.fullmatch(r"[0-9][0-9,]*",line): continue
        if any(token in line for token in ("Statewide Results","County Results","Export Data","Boxes Reported:")): continue
        # Contest headings are uppercase in AlabamaVotes rendered output.
        if line==line.upper() and any(c.isalpha() for c in line) and len(line)>4:
            if current and current["candidates"]: contests.append(current)
            dm=DISTRICT.search(line)
            current={"title":line,"scope":_scope(line),"district":dm.group(1) if dm else None,"candidates":[]}
    if current and current["candidates"]: contests.append(current)
    if not contests: raise ValueError("no Alabama contests parsed")
    return {"boxesReportedPercent":pct,"complete":pct==100.0,"contests":contests}
