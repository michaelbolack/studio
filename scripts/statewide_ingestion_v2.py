#!/usr/bin/env python3
"""Authoritative Florida statewide primary ingestion for Election Center v2.

Builds only from Florida Department of State Election Watch county-detail tables.
Every statewide race fails closed unless all 67 counties are present and the sum of
all county candidate votes exactly matches Election Watch's authoritative Total row.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

BASE = "https://floridaelectionwatch.gov"
ELECTION_DATE = "2026-08-18"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

COUNTIES = [
    "Alachua", "Baker", "Bay", "Bradford", "Brevard", "Broward", "Calhoun", "Charlotte",
    "Citrus", "Clay", "Collier", "Columbia", "DeSoto", "Dixie", "Duval", "Escambia",
    "Flagler", "Franklin", "Gadsden", "Gilchrist", "Glades", "Gulf", "Hamilton", "Hardee",
    "Hendry", "Hernando", "Highlands", "Hillsborough", "Holmes", "Indian River", "Jackson",
    "Jefferson", "Lafayette", "Lake", "Lee", "Leon", "Levy", "Liberty", "Madison", "Manatee",
    "Marion", "Martin", "Miami-Dade", "Monroe", "Nassau", "Okaloosa", "Okeechobee", "Orange",
    "Osceola", "Palm Beach", "Pasco", "Pinellas", "Polk", "Putnam", "Santa Rosa", "Sarasota",
    "Seminole", "St. Johns", "St. Lucie", "Sumter", "Suwannee", "Taylor", "Union", "Volusia",
    "Wakulla", "Walton", "Washington",
]
COUNTY_ALIASES = {"Desoto": "DeSoto"}

CONTESTS = [
    {"id": "120001", "office": "United States Senator", "party": "REP", "marker": "United States Senator"},
    {"id": "120002", "office": "United States Senator", "party": "DEM", "marker": "United States Senator"},
    {"id": "160001", "office": "Governor and Lieutenant Governor", "party": "REP", "marker": "Governor"},
    {"id": "160002", "office": "Governor and Lieutenant Governor", "party": "DEM", "marker": "Governor"},
    {"id": "160501", "office": "Chief Financial Officer", "party": "REP", "marker": "Chief Financial Officer"},
    {"id": "160502", "office": "Chief Financial Officer", "party": "DEM", "marker": "Chief Financial Officer"},
    {"id": "160801", "office": "Commissioner of Agriculture", "party": "REP", "marker": "Commissioner of Agriculture"},
    {"id": "160802", "office": "Commissioner of Agriculture", "party": "DEM", "marker": "Commissioner of Agriculture"},
]


def integer(value: str) -> int:
    text = (value or "").strip()
    if not text:
        raise ValueError("empty vote cell")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        raise ValueError(f"invalid vote cell: {value!r}")
    return int(digits)


def canonical_county(label: str) -> str:
    label = label.strip().rstrip(":")
    return COUNTY_ALIASES.get(label, label)


def fetch_contest(config: dict) -> dict:
    url = f"{BASE}/ContestResultsByCounty/{config['id']}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)

    for marker in ("2026 Primary Election", "August 18, 2026", config["marker"]):
        if marker.lower() not in page_text.lower():
            raise RuntimeError(f"contest {config['id']} missing marker: {marker}")
    expected_party = "Republican" if config["party"] == "REP" else "Democrat"
    if expected_party.lower() not in page_text.lower():
        raise RuntimeError(f"contest {config['id']} missing party marker: {expected_party}")

    table = next(
        (
            t for t in soup.find_all("table")
            if "County" in " ".join(t.stripped_strings)
            and "Total" in " ".join(t.stripped_strings)
            and "Alachua" in " ".join(t.stripped_strings)
            and "Washington" in " ".join(t.stripped_strings)
        ),
        None,
    )
    if table is None:
        raise RuntimeError(f"contest {config['id']} county table not found")

    rows: List[List[str]] = []
    for tr in table.find_all("tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    header_index = next((i for i, row in enumerate(rows) if row and row[0].lower() == "county"), None)
    if header_index is None:
        raise RuntimeError(f"contest {config['id']} County header missing")
    candidate_names = [x.strip() for x in rows[header_index][1:] if x.strip()]
    if not candidate_names:
        raise RuntimeError(f"contest {config['id']} candidate header missing")

    county_votes: Dict[str, List[int]] = {}
    official_total: List[int] | None = None
    for row in rows[header_index + 1 :]:
        raw_label = row[0].strip().rstrip(":")
        label = canonical_county(raw_label)
        vote_cells = row[1 : 1 + len(candidate_names)]
        if label in COUNTIES:
            if len(vote_cells) != len(candidate_names):
                raise RuntimeError(f"contest {config['id']} malformed county row: {label}")
            try:
                county_votes[label] = [integer(v) for v in vote_cells]
            except ValueError as exc:
                raise RuntimeError(f"contest {config['id']} invalid {label} vote data: {exc}") from exc
        elif raw_label.lower() == "total":
            if len(vote_cells) != len(candidate_names):
                raise RuntimeError(f"contest {config['id']} malformed Total row")
            official_total = [integer(v) for v in vote_cells]

    missing = [county for county in COUNTIES if county not in county_votes]
    extras = sorted(set(county_votes) - set(COUNTIES))
    if missing or extras or len(county_votes) != 67:
        raise RuntimeError(
            f"contest {config['id']} county coverage invalid: {len(county_votes)}/67; "
            f"missing={missing}; extras={extras}"
        )
    if official_total is None:
        raise RuntimeError(f"contest {config['id']} authoritative Total row missing")

    calculated = [sum(county_votes[c][i] for c in COUNTIES) for i in range(len(candidate_names))]
    if calculated != official_total:
        raise RuntimeError(
            f"contest {config['id']} checksum failed: counties={calculated}, ElectionWatch={official_total}"
        )

    grand_total = sum(official_total)
    candidates = [
        {
            "name": name,
            "party": config["party"],
            "votes": votes,
            "percent": round((votes / grand_total * 100) if grand_total else 0, 2),
        }
        for name, votes in zip(candidate_names, official_total)
    ]
    geography = [
        {
            "level": "county",
            "id": county,
            "county": county,
            "name": county,
            "votes": {candidate_names[i]: county_votes[county][i] for i in range(len(candidate_names))},
        }
        for county in COUNTIES
    ]

    return {
        "id": f"FL-{re.sub(r'[^A-Z0-9]+', '-', config['office'].upper()).strip('-')}-{config['party']}-2026-PRIMARY",
        "office": config["office"],
        "party": config["party"],
        "candidates": candidates,
        "geography": geography,
        "source": {"authority": "Florida Department of State - Florida Election Watch", "url": response.url},
        "validation": {
            "coverage": "67/67",
            "coverageComplete": True,
            "checksum": "passed",
            "calculatedTotals": calculated,
            "officialTotals": official_total,
        },
    }


def build() -> dict:
    races = [fetch_contest(config) for config in CONTESTS]
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": 2,
        "generatedAt": now,
        "election": {
            "name": "2026 Florida Primary Election",
            "date": ELECTION_DATE,
            "state": "FL",
            "resultStatus": "Unofficial Election Night Results",
        },
        "scope": {"type": "statewide", "state": "FL", "counties": COUNTIES},
        "status": "publishable",
        "coverageComplete": True,
        "countiesIncluded": 67,
        "countyNames": COUNTIES,
        "mapReady": True,
        "races": races,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data-v2"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "statewide.json"
    try:
        payload = build()
    except Exception as exc:
        withheld = {
            "schemaVersion": 2,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "status": "withheld",
            "coverageComplete": False,
            "mapReady": False,
            "reason": str(exc),
            "races": [],
        }
        path.write_text(json.dumps(withheld, indent=2) + "\n")
        print(f"WITHHELD: {exc}", file=sys.stderr)
        return 1

    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("PUBLISHABLE: Florida statewide Election Watch 8 races, 67/67 checksums passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
