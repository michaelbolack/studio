#!/usr/bin/env python3
"""Election ingestion v2: deterministic, fail-closed canonical builder.

This migrated compatibility collector preserves the proven Florida CD9 checksum path
while the national registry is introduced. New state adapters should be configured
through data/jurisdictions.json rather than adding new state assumptions here.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

ELECTION_DATE = "2026-08-18"
DEFAULT_OUT = Path("data-v2")
ELECTION_WATCH_BASE = "https://floridaelectionwatch.gov"
CD9_CONTEST_URL = f"{ELECTION_WATCH_BASE}/ContestResultsByCounty/140091"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
CD9_COUNTIES = ["Glades", "Highlands", "Indian River", "Okeechobee", "Orange", "Osceola", "Polk"]


def integer(value: str) -> int:
    text = (value or "").strip()
    if not text:
        raise ValueError("empty vote cell")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        raise ValueError(f"invalid vote cell: {value!r}")
    return int(digits)


@dataclass
class Candidate:
    name: str
    party: str
    votes: int

    def as_json(self, total: int) -> dict:
        return {"name": self.name, "party": self.party, "votes": self.votes,
                "percent": round((self.votes / total * 100) if total else 0, 2)}


def fetch_cd9() -> dict:
    response = requests.get(CD9_CONTEST_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    required = ("2026 Primary Election", "Representative in Congress, District 9", "Republican", "Contest Results by County")
    missing_markers = [x for x in required if x.lower() not in page_text.lower()]
    if missing_markers:
        raise RuntimeError("Florida Election Watch CD9 page missing expected markers: " + ", ".join(missing_markers))
    table = next((t for t in soup.find_all("table") if "County" in " ".join(t.stripped_strings) and "Osceola" in " ".join(t.stripped_strings) and "Total" in " ".join(t.stripped_strings)), None)
    if table is None:
        raise RuntimeError("Florida Election Watch CD9 county table not found")
    rows = []
    for tr in table.find_all("tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    header_index = next((i for i, row in enumerate(rows) if row and row[0].lower() == "county"), None)
    if header_index is None:
        raise RuntimeError("County header missing from Election Watch CD9 table")
    candidate_names = [x.strip() for x in rows[header_index][1:] if x.strip()]
    if not candidate_names:
        raise RuntimeError("Candidate header missing from Election Watch CD9 table")
    county_votes: Dict[str, List[int]] = {}
    official_total = None
    for row in rows[header_index + 1:]:
        label = row[0].strip().rstrip(":")
        vote_cells = row[1:1 + len(candidate_names)]
        if label in CD9_COUNTIES:
            if len(vote_cells) != len(candidate_names):
                raise RuntimeError(f"Malformed county row for {label}")
            county_votes[label] = [integer(v) for v in vote_cells]
        elif label.lower() == "total":
            if len(vote_cells) != len(candidate_names):
                raise RuntimeError("Malformed official total row")
            official_total = [integer(v) for v in vote_cells]
    missing = [x for x in CD9_COUNTIES if x not in county_votes]
    if missing:
        raise RuntimeError("Missing required county rows: " + ", ".join(missing))
    if official_total is None:
        raise RuntimeError("Authoritative Election Watch Total row missing")
    calculated = [sum(county_votes[c][i] for c in CD9_COUNTIES) for i in range(len(candidate_names))]
    if calculated != official_total:
        raise RuntimeError(f"Checksum failed: counties={calculated}, ElectionWatch={official_total}")
    total_votes = sum(official_total)
    candidates = [Candidate(n, "REP", v).as_json(total_votes) for n, v in zip(candidate_names, official_total)]
    geography = [{"level": "county", "id": c, "county": c, "name": c,
                  "votes": {candidate_names[i]: county_votes[c][i] for i in range(len(candidate_names))}}
                 for c in CD9_COUNTIES]
    return {"party": "REP", "candidates": candidates, "geography": geography,
            "sourceUrl": response.url, "calculatedTotals": calculated, "officialTotals": official_total}


def build() -> dict:
    result = fetch_cd9()
    race = {"id": "FL-US-HOUSE-09-REP-2026-PRIMARY", "office": "United States Representative", "district": 9,
            "party": result["party"], "candidates": result["candidates"], "geography": result["geography"],
            "source": {"authority": "Florida Department of State - Florida Election Watch", "url": result["sourceUrl"]},
            "validation": {"coverage": "7/7", "coverageComplete": True, "checksum": "passed",
                           "calculatedTotals": result["calculatedTotals"], "officialTotals": result["officialTotals"]}}
    return {"schemaVersion": 2, "generatedAt": datetime.now(timezone.utc).isoformat(),
            "election": {"name": "2026 Florida Primary Election", "date": ELECTION_DATE, "state": "FL",
                         "resultStatus": "Unofficial Election Night Results"},
            "scope": {"type": "congressional-district", "district": 9, "counties": CD9_COUNTIES},
            "status": "publishable", "coverageComplete": True, "countiesIncluded": len(CD9_COUNTIES),
            "countyNames": CD9_COUNTIES, "mapReady": True, "races": [race]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical Election Center v2 data")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = build()
    except Exception as exc:
        failure = {"schemaVersion": 2, "generatedAt": datetime.now(timezone.utc).isoformat(), "status": "withheld",
                   "coverageComplete": False, "mapReady": False, "reason": str(exc), "races": []}
        (args.output_dir / "district-9.json").write_text(json.dumps(failure, indent=2) + "\n")
        print(f"WITHHELD: {exc}", file=sys.stderr)
        return 1
    (args.output_dir / "district-9.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("PUBLISHABLE: CD9 Florida Election Watch 7/7 checksum passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
