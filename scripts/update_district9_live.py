#!/usr/bin/env python3
"""Fast-path Congressional District 9 General Election aggregate.

Builds data/district-9.json only from current Nov. 3 county files already in the repo.
Wrong-election county files are ignored. This prevents stale Aug. 18 primary data from
reappearing in the live District 9 card.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "district-9.json"

COUNTIES = ["Glades","Highlands","Indian River","Okeechobee","Orange","Osceola","Polk"]
CANDIDATES = {
    "dangreen": {"name":"Dan Green","party":"REP","votes":0},
    "darrensoto": {"name":"Darren Soto","party":"DEM","votes":0},
}

def key(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+","",str(s or "").lower())

def main() -> int:
    included = []
    geography = []
    totals = {k: dict(v) for k,v in CANDIDATES.items()}
    latest = ""

    for county in COUNTIES:
        path = DATA / (county.lower().replace(" ","-") + ".json")
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(data.get("electionDate") or "") != "2026-11-03":
            continue

        matched = None
        for race in data.get("races") or []:
            names = {key(c.get("name")) for c in race.get("candidates") or []}
            if {"dangreen","darrensoto"}.issubset(names):
                matched = race
                break
        if not matched:
            continue

        county_votes = {}
        for c in matched.get("candidates") or []:
            ck = key(c.get("name"))
            if ck not in totals:
                continue
            votes = int(c.get("votes") or 0)
            totals[ck]["votes"] += votes
            county_votes[totals[ck]["name"]] = votes

        included.append(county)
        geography.append({"county": county, "votes": county_votes})
        latest = max(latest, str(data.get("generatedAt") or data.get("lastUpdated") or ""))

    candidates = [totals["dangreen"], totals["darrensoto"]]
    grand = sum(c["votes"] for c in candidates)
    for c in candidates:
        c["percent"] = round((c["votes"]/grand*100) if grand else 0, 2)

    payload = {
        "scope":"Florida Congressional District 9",
        "district":9,
        "election":"2026 General Election",
        "electionDate":"2026-11-03",
        "source":"Aggregated official county Election Night Reporting feeds for Congressional District 9",
        "countiesIncluded":len(included),
        "countiesExpected":len(COUNTIES),
        "countyNames":included,
        "coverageComplete":set(included)==set(COUNTIES),
        "displayStatus":"complete" if set(included)==set(COUNTIES) else "partial-live",
        "integrityMessage":f"Congressional District 9 is updating live from official county feeds ({len(included)}/{len(COUNTIES)} counties included).",
        "lastUpdated":latest or datetime.now(timezone.utc).isoformat(),
        "races":[{
            "name":"Representative in Congress District 9",
            "type":"congress",
            "district":9,
            "candidates":candidates,
            "geography":geography,
        }],
        "generatedAt":datetime.now(timezone.utc).isoformat(),
    }

    if len(included) == 0:
        raise RuntimeError("No current Nov. 3 District 9 county files available")

    OUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "countiesIncluded":len(included),
        "countiesExpected":len(COUNTIES),
        "Dan Green":totals["dangreen"]["votes"],
        "Darren Soto":totals["darrensoto"]["votes"],
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
