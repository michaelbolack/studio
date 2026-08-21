#!/usr/bin/env python3
"""Translate validated congressional v2 output into the preserved Election Center contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(data: dict) -> None:
    if data.get("status") != "publishable":
        raise RuntimeError("congressional v2 payload is not publishable")
    if data.get("coverageComplete") is not True or data.get("mapReady") is not True:
        raise RuntimeError("congressional v2 payload is incomplete")
    races = data.get("races") or []
    if not races or len(races) != data.get("contestsDiscovered"):
        raise RuntimeError("congressional contest discovery count mismatch")
    combos = [(r.get("district"), r.get("party")) for r in races]
    if len(combos) != len(set(combos)):
        raise RuntimeError("duplicate congressional district/party contests")
    for race in races:
        validation = race.get("validation") or {}
        if validation.get("checksum") != "passed":
            raise RuntimeError(f"checksum failed: {race.get('id')}")
        if validation.get("calculatedTotals") != validation.get("officialTotals"):
            raise RuntimeError(f"checksum totals disagree: {race.get('id')}")
        geography = race.get("geography") or []
        county_names = race.get("countyNames") or []
        if not geography or {g.get("county") for g in geography} != set(county_names):
            raise RuntimeError(f"geography mismatch: {race.get('id')}")
        if race.get("countiesIncluded") != len(geography):
            raise RuntimeError(f"county count mismatch: {race.get('id')}")


def frontend_payload(data: dict) -> dict:
    election = data.get("election") or {}
    races = []
    for race in data.get("races") or []:
        count = race.get("countiesIncluded") or len(race.get("geography") or [])
        races.append({
            "id": race.get("id"),
            "name": f"{race.get('party')} Representative in Congress, District {race.get('district')}",
            "office": race.get("office"),
            "district": race.get("district"),
            "party": race.get("party"),
            "type": "congress",
            "candidates": race.get("candidates") or [],
            "geography": race.get("geography") or [],
            "countyNames": race.get("countyNames") or [],
            "countiesIncluded": count,
            "countiesExpected": count,
            "coverageComplete": True,
            "source": race.get("source"),
            "validation": race.get("validation"),
        })
    return {
        "schemaVersion": data.get("schemaVersion", 2),
        "scope": "Florida Congressional Districts",
        "election": election.get("name", "2026 Florida Primary Election"),
        "electionDate": election.get("date", "2026-08-18"),
        "source": "Florida Department of State - Florida Election Watch",
        "sourceUrl": "https://floridaelectionwatch.gov/FederalOffices/USRepresentative",
        "coverageComplete": True,
        "mapReady": True,
        "contestsDiscovered": data.get("contestsDiscovered"),
        "districtsCovered": data.get("districtsCovered") or [],
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
    print("PUBLISHED: validated congressional v2 -> existing Election Center contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
