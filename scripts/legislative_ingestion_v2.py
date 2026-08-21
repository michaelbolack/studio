#!/usr/bin/env python3
"""Generic Florida State House/Senate primary ingestion for Election Center v2.

Discovers contested legislative primaries from Florida Election Watch and fails closed
for any contest whose county contributions do not exactly checksum to the official
Total row. County geography is retained for map-ready district data.
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
ELECTION_DATE = "2026-08-18"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
COUNTY_ALIASES = {"Desoto": "DeSoto"}
OFFICE_INDEXES = [
    ("State Representative", f"{BASE}/DistrictOffices/StateRepresentative"),
    ("State Senator", f"{BASE}/DistrictOffices/StateSenator"),
]


def integer(value: str) -> int:
    text = (value or "").strip()
    if not text:
        raise ValueError("empty vote cell")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        raise ValueError(f"invalid vote cell: {value!r}")
    return int(digits)


def discover_office(office: str, index_url: str) -> list[dict]:
    response = requests.get(index_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    for marker in ("2026 Primary Election", "August 18, 2026", office):
        if marker.lower() not in page_text.lower():
            raise RuntimeError(f"{office} index missing marker: {marker}")

    contests = []
    seen = set()
    label_re = re.compile(rf"{re.escape(office)}, District\s+(\d+)", re.I)
    for anchor in soup.find_all("a"):
        label = " ".join(anchor.stripped_strings)
        href = anchor.get("href") or ""
        if "Contest Results by County" not in label or "/ContestResultsByCounty/" not in href:
            continue
        district = None
        party = None
        for previous in anchor.find_all_previous(string=True, limit=100):
            text = re.sub(r"\s+", " ", str(previous)).strip()
            if party is None:
                if text == "Republican":
                    party = "REP"
                elif text == "Democrat":
                    party = "DEM"
            match = label_re.fullmatch(text)
            if match:
                district = int(match.group(1))
                break
        if district is None or party is None:
            raise RuntimeError(f"could not identify {office} district/party for {href}")
        key = (district, party)
        if key in seen:
            raise RuntimeError(f"duplicate {office} contest: District {district} {party}")
        seen.add(key)
        contests.append({
            "contestId": href.rstrip("/").split("/")[-1],
            "office": office,
            "district": district,
            "party": party,
            "url": urljoin(BASE, href),
        })
    return contests


def discover_contests() -> list[dict]:
    contests = []
    for office, url in OFFICE_INDEXES:
        contests.extend(discover_office(office, url))
    if not contests:
        raise RuntimeError("Election Watch exposed no contested legislative primaries")
    contests.sort(key=lambda x: (x["office"], x["district"], x["party"]))
    return contests


def fetch_contest(config: dict) -> dict:
    response = requests.get(config["url"], headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)
    contest_marker = f"{config['office']}, District {config['district']}"
    party_marker = "Republican" if config["party"] == "REP" else "Democrat"
    for marker in ("2026 Primary Election", "August 18, 2026", contest_marker, party_marker):
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
    for row in rows[header_index + 1:]:
        raw_label = row[0].strip().rstrip(":")
        label = COUNTY_ALIASES.get(raw_label, raw_label)
        vote_cells = row[1:1 + len(names)]
        if raw_label.lower() == "total":
            if len(vote_cells) != len(names):
                raise RuntimeError(f"contest {config['contestId']} malformed Total row")
            official_total = [integer(v) for v in vote_cells]
            continue
        if not raw_label or len(vote_cells) != len(names):
            continue
        try:
            parsed = [integer(v) for v in vote_cells]
        except ValueError:
            continue
        if label in county_votes:
            raise RuntimeError(f"contest {config['contestId']} duplicate county row: {label}")
        county_votes[label] = parsed

    if not county_votes:
        raise RuntimeError(f"contest {config['contestId']} has no county rows")
    if official_total is None:
        raise RuntimeError(f"contest {config['contestId']} authoritative Total row missing")
    counties = list(county_votes)
    calculated = [sum(county_votes[c][i] for c in counties) for i in range(len(names))]
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
        for county in counties
    ]
    office_id = "STATE-HOUSE" if config["office"] == "State Representative" else "STATE-SENATE"
    return {
        "id": f"FL-{office_id}-{config['district']:03d}-{config['party']}-2026-PRIMARY",
        "office": config["office"],
        "district": config["district"],
        "party": config["party"],
        "candidates": candidates,
        "geography": geography,
        "countyNames": counties,
        "countiesIncluded": len(counties),
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
        "scope": {"type": "legislative-districts", "state": "FL"},
        "status": "publishable",
        "coverageComplete": True,
        "mapReady": True,
        "contestsDiscovered": len(discovered),
        "houseDistrictsCovered": sorted({r["district"] for r in races if r["office"] == "State Representative"}),
        "senateDistrictsCovered": sorted({r["district"] for r in races if r["office"] == "State Senator"}),
        "races": races,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data-v2"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "legislative.json"
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
    print(f"PUBLISHABLE: {payload['contestsDiscovered']} Florida legislative primaries checksummed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
