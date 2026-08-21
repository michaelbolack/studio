#!/usr/bin/env python3
"""Translate validated statewide v2 output into the preserved Election Center contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_OFFICES = {
    "United States Senator",
    "Governor and Lieutenant Governor",
    "Chief Financial Officer",
    "Commissioner of Agriculture",
}
EXPECTED_PARTIES = {"REP", "DEM"}


def validate(data: dict) -> None:
    if data.get("status") != "publishable":
        raise RuntimeError("statewide v2 payload is not publishable")
    if data.get("coverageComplete") is not True or data.get("countiesIncluded") != 67:
        raise RuntimeError("statewide v2 coverage is incomplete")
    counties = data.get("countyNames") or []
    if len(counties) != 67 or len(set(counties)) != 67:
        raise RuntimeError("statewide v2 county list is not exactly 67 unique counties")
    if data.get("mapReady") is not True:
        raise RuntimeError("statewide v2 payload is not map-ready")

    races = data.get("races") or []
    if len(races) != 8:
        raise RuntimeError(f"expected 8 statewide primary races, found {len(races)}")
    combos = {(r.get("office"), r.get("party")) for r in races}
    expected = {(office, party) for office in EXPECTED_OFFICES for party in EXPECTED_PARTIES}
    if combos != expected:
        raise RuntimeError(f"statewide office/party coverage mismatch: {sorted(combos)}")

    expected_counties = set(counties)
    for race in races:
        validation = race.get("validation") or {}
        if validation.get("coverage") != "67/67" or validation.get("coverageComplete") is not True:
            raise RuntimeError(f"incomplete race coverage: {race.get('id')}")
        if validation.get("checksum") != "passed":
            raise RuntimeError(f"race checksum failed: {race.get('id')}")
        if validation.get("calculatedTotals") != validation.get("officialTotals"):
            raise RuntimeError(f"race totals disagree: {race.get('id')}")
        geography = race.get("geography") or []
        if {g.get("county") for g in geography} != expected_counties:
            raise RuntimeError(f"race geography incomplete: {race.get('id')}")
        if not race.get("candidates"):
            raise RuntimeError(f"race candidates missing: {race.get('id')}")


def frontend_payload(data: dict) -> dict:
    election = data.get("election") or {}
    races = []
    for race in data.get("races") or []:
        races.append({
            "id": race.get("id"),
            "name": f"{race.get('party')} {race.get('office')}",
            "office": race.get("office"),
            "party": race.get("party"),
            "type": "statewide",
            "candidates": race.get("candidates") or [],
            "geography": race.get("geography") or [],
            "source": race.get("source"),
            "validation": race.get("validation"),
        })

    return {
        "schemaVersion": data.get("schemaVersion", 2),
        "scope": "Florida",
        "election": election.get("name", "2026 Florida Primary Election"),
        "electionDate": election.get("date", "2026-08-18"),
        "source": "Florida Department of State - Florida Election Watch",
        "sourceUrl": "https://floridaelectionwatch.gov/",
        "countiesIncluded": 67,
        "countiesExpected": 67,
        "countiesDiscovered": 67,
        "countyNames": data.get("countyNames") or [],
        "coverageComplete": True,
        "mapReady": True,
        "lastUpdated": data.get("generatedAt"),
        "generatedAt": data.get("generatedAt"),
        "displayStatus": "complete",
        "races": races,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.input.read_text())
    validate(data)
    output = frontend_payload(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("PUBLISHED: validated statewide v2 -> existing Election Center contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
