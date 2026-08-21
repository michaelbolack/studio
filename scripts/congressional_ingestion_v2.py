#!/usr/bin/env python3
"""Generic Florida U.S. House primary ingestion for Election Center v2.

Discovers every contested U.S. House primary exposed on Florida Election Watch,
then fetches each official county-detail table. A contest is publishable only when
its county rows checksum exactly to Election Watch's authoritative Total row.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://floridaelectionwatch.gov"
INDEX_URL = f"{BASE}/FederalOffices/USRepresentative"
ELECTION_DATE = "2026-08-18"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
COUNTY_ALIASES = {"Desoto": "DeSoto"}


def integer(value: str) -> int:
    text = (value or "").strip()
    if not text:
        raise ValueError("empty vote cell")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        raise ValueError(f"invalid vote cell: {value!r}")
    return int(digits)


def discover_contests() -> list[dict]:
    response = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    for marker in ("2026 Primary Election", "August 18, 2026", "U.S. Representative"):
        if marker.lower() not in page_text.lower():
            raise RuntimeError(f"U.S. House index missing marker: {marker}")

    contests = []
    seen = set()
    for anchor in soup.find_all("a"):
        label = " ".join(anchor.stripped_strings)
        href = anchor.get("href") or ""
        if "Contest Results by County" not in label or "/ContestResultsByCounty/" not in href:
            continue

        district = None
        party = None
        for previous in anchor.find_all_previous(string=True, limit=80):
            text = re.sub(r"\s+", " ", str(previous)).strip()
            if party is None:
                if text == "Republican":
                    party = "REP"
                elif text == "Democrat":
                    party = "DEM"
            match = re.fullmatch(r"Representative in Congress, District\s+(\d+)", text, re.I)
            if match:
                district = int(match.group(1))
                break
        if district is None or party is None:
            raise RuntimeError(f"could not identify district/party for Election Watch link: {href}")

        contest_id = href.rstrip("/").split("/")[-1]
        key = (district, party)
        if key in seen:
            raise RuntimeError(f"duplicate U.S. House contest discovered: District {district} {party}")
        seen.add(key)
        contests.append({
            "contestId": contest_id,
            "district": district,
            "party": party,
            "url": urljoin(BASE, href),
        })

    if not contests:
        raise RuntimeError("Election Watch exposed no contested U.S. House primaries")
    contests.sort(key=lambda x: (x["district"], x["party"]))
    return contests


def fetch_contest(config: dict) -> dict:
    response = requests.get(config["url"], headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    district_marker = f"Representative in Congress, District {config['district']}"
    party_marker = "Republican" if config["party"] == "REP" else "Democrat"
    for marker in ("2026 Primary Election", "August 18, 2026", district_marker, party_marker):
        if marker.lower() not in page_text.lower():
            raise RuntimeError(f"contest {config['contestId']} missing marker: {marker}")

    table = next(
        (t for t in soup.find_all("table") if "County" in " ".join(t.stripped_strings) and "Total" in " ".join(t.stripped_strings)),
        None,
    )
    if table is None:
        raise RuntimeError(f"contest {config['contestId']} county table not found")

    rows = []
    for tr in table.find_all("tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    header_index = next((i for i, row in enumerate(rows) if row and row[0].lower() == "county"), None)
    if header_index is None:
        raise RuntimeError(f"contest {config['contestId']} County header missing")
    names = [x.strip() for x in rows[header_index][1:] if x.strip()]
    if not names:
        raise RuntimeError(f"contest {config['contestId']} candidate header missing")

    county_votes = {}
    official_total = None
    for row in rows[header_index + 1 :]:
        raw_label = row[0].strip().rstrip(":")
        label = COUNTY_ALIASES.get(raw_label, raw_label)
        vote_cells = row[1 : 1 + len(names)]
        if raw_label.lower() == "total":
            if len(vote_cells) != len(names):
                raise RuntimeError(f"contest {config['contestId']} malformed Total row")
            official_total = [integer(v) for v in vote_cells]
        elif raw_label and len(vote_cells) == len(names):
            try:
                parsed = [integer(v) for v in vote_cells]
            except ValueError:
                continue
            if label in county_votes:
                raise RuntimeError(f"contest {config['contestId']} duplicate county row: {label}")
            county_votes[label] = parsed

    if not county_votes:
        raise RuntimeError(f"contest {config['contestId']} has no county vote rows")
    if official_total is None:
        raise RuntimeError(f"contest {config['contestId']} authoritative Total row missing")

    county_names = list(county_votes.keys())
    calculated = [sum(county_votes[c][i] for c in county_names) for i in range(len(names))]
    if calculated != official_total:
        raise RuntimeError(
            f"contest {config['contestId']} checksum failed: counties={calculated}, ElectionWatch={official_total}"
        )

    grand = sum(official_total)
    candidates = [
        {
            "name": name,
            "party": config["party"],
            "votes": votes,
            "percent": round((votes / grand * 100) if grand else 0, 2),
        }
        for name, votes in zip(names, official_total)
    ]
    geography = [
        {
            "level": "county",
            "id": county,
            "county": county,
            "name": county,
            "votes": {names[i]: county_votes[county][i] for i in range(len(names))},
        }
        for county in county_names
    ]

    return {
        "id": f"FL-US-HOUSE-{config['district']:02d}-{config['party']}-2026-PRIMARY",
        "office": "United States Representative",
        "district": config["district"],
        "party": config["party"],
        "candidates": candidates,
        "geography": geography,
        "countyNames": county_names,
        "countiesIncluded": len(county_names),
        "source": {"authority": "Florida Department of State - Florida Election Watch", "url": response.url},
        "validation": {
            "coverageComplete": True,
            "checksum": "passed",
            "calculatedTotals": calculated,
            "officialTotals": official_total,
        },
    }


def build() -> dict:
    discovered = discover_contests()
    races = [fetch_contest(config) for config in discovered]
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
        "scope": {"type": "congressional", "state": "FL"},
        "status": "publishable",
        "coverageComplete": True,
        "mapReady": True,
        "contestsDiscovered": len(discovered),
        "districtsCovered": sorted({race["district"] for race in races}),
        "races": races,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data-v2"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "congressional.json"
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
    print(f"PUBLISHABLE: {payload['contestsDiscovered']} Florida U.S. House primary contests checksummed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
