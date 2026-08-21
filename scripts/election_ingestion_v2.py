#!/usr/bin/env python3
"""Election ingestion v2: deterministic, fail-closed canonical builder.

This pipeline intentionally does not run the legacy recovery-script chain. It builds
canonical statewide/district outputs from authoritative Florida DOS sources first,
then validates before publication. County/local adapters can be added behind the same
schema without changing the frontend.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

ELECTION_DATE_PARAM = "8/18/2026"
ELECTION_DATE = "2026-08-18"
OUT = Path("data-v2")
DETAIL_URL = "https://results.elections.myflorida.com/DetailRpt.Asp"
HEADERS = {"User-Agent": "IRC-Media-Election-Center/2.0", "Accept": "text/html"}
CD9_COUNTIES = ["Glades", "Highlands", "Indian River", "Okeechobee", "Orange", "Osceola", "Polk"]
PARTIES = ("REP", "DEM")


def integer(value: str) -> int:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else 0


@dataclass
class Candidate:
    name: str
    party: str
    votes: int

    def as_json(self, total: int) -> dict:
        return {
            "name": self.name,
            "party": self.party,
            "votes": self.votes,
            "percent": round((self.votes / total * 100) if total else 0, 2),
        }


def fetch_cd9_party(party: str) -> dict:
    response = requests.get(
        DETAIL_URL,
        params={"DATAMODE": "", "DIST": "009", "ELECTIONDATE": ELECTION_DATE_PARAM, "PARTY": party, "RACE": "USR"},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    if "United States Representative" not in page_text or not re.search(r"District:\s*0*9\b", page_text, re.I):
        raise RuntimeError(f"Florida DOS CD9 {party} page unavailable or wrong race")

    table = next((t for t in soup.find_all("table") if "County" in " ".join(t.stripped_strings) and "Total" in " ".join(t.stripped_strings)), None)
    if table is None:
        raise RuntimeError(f"Florida DOS CD9 {party} county table not found")

    rows: List[List[str]] = []
    for tr in table.find_all("tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    header_index = next((i for i, row in enumerate(rows) if row and row[0].lower() == "county"), None)
    if header_index is None:
        raise RuntimeError("County header missing")

    names = [re.sub(r"\s*\([A-Z]{2,4}\)\s*$", "", x).strip() for x in rows[header_index][1:]]
    names = [x for x in names if x]
    if not names:
        raise RuntimeError("Candidate header missing")

    county_votes: Dict[str, List[int]] = {}
    official_total = None
    for row in rows[header_index + 1:]:
        label = row[0].strip()
        values = [integer(x) for x in row[1:1 + len(names)]]
        if label in CD9_COUNTIES and len(values) == len(names):
            county_votes[label] = values
        elif label.lower() == "total" and len(values) == len(names):
            official_total = values

    missing = [county for county in CD9_COUNTIES if county not in county_votes]
    if missing:
        raise RuntimeError("Missing required county rows: " + ", ".join(missing))
    if official_total is None:
        raise RuntimeError("Official total row missing")

    calculated = [sum(county_votes[c][i] for c in CD9_COUNTIES) for i in range(len(names))]
    if calculated != official_total:
        raise RuntimeError(f"Checksum failed: counties={calculated}, DOS={official_total}")

    total_votes = sum(official_total)
    candidates = [Candidate(name, party, votes).as_json(total_votes) for name, votes in zip(names, official_total)]
    geography = [
        {"level": "county", "id": county, "name": county, "votes": {name: county_votes[county][i] for i, name in enumerate(names)}}
        for county in CD9_COUNTIES
    ]
    return {"party": party, "candidates": candidates, "geography": geography, "sourceUrl": response.url}


def build() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    party_results = [fetch_cd9_party(party) for party in PARTIES]
    races = [
        {
            "id": f"FL-US-HOUSE-09-{result['party']}-2026-PRIMARY",
            "office": "United States Representative",
            "district": 9,
            "party": result["party"],
            "candidates": result["candidates"],
            "geography": result["geography"],
            "source": {"authority": "Florida Department of State", "url": result["sourceUrl"]},
            "validation": {"coverage": "7/7", "checksum": "passed"},
        }
        for result in party_results
    ]
    return {
        "schemaVersion": 2,
        "generatedAt": now,
        "election": {"name": "2026 Florida Primary Election", "date": ELECTION_DATE, "state": "FL"},
        "scope": {"type": "congressional-district", "district": 9, "counties": CD9_COUNTIES},
        "status": "publishable",
        "mapReady": True,
        "races": races,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        payload = build()
    except Exception as exc:
        failure = {
            "schemaVersion": 2,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "status": "withheld",
            "reason": str(exc),
            "races": [],
        }
        (OUT / "district-9.json").write_text(json.dumps(failure, indent=2) + "\n")
        print(f"WITHHELD: {exc}", file=sys.stderr)
        return 1
    (OUT / "district-9.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("PUBLISHABLE: CD9 Florida DOS 7/7 checksum passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
