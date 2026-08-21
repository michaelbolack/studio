#!/usr/bin/env python3
"""Publish validated Election Ingestion v2 output into the existing frontend contract.

This adapter intentionally does not fetch or repair election data. It accepts only a
canonical v2 payload that has already passed ingestion validation and translates it
for the preserved Election Center frontend.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_CD9 = {"Glades", "Highlands", "Indian River", "Okeechobee", "Orange", "Osceola", "Polk"}


def validate_cd9(data: dict) -> None:
    counties = set(data.get("countyNames") or [])
    if data.get("status") != "publishable":
        raise RuntimeError("v2 payload is not publishable")
    if data.get("coverageComplete") is not True:
        raise RuntimeError("v2 payload coverage is incomplete")
    if data.get("countiesIncluded") != 7 or counties != EXPECTED_CD9:
        raise RuntimeError(f"v2 payload county coverage mismatch: {sorted(counties)}")
    if "Osceola" not in counties:
        raise RuntimeError("Osceola missing from v2 payload")
    if data.get("mapReady") is not True:
        raise RuntimeError("v2 payload is not map-ready")

    races = data.get("races") or []
    if not races:
        raise RuntimeError("v2 payload contains no races")
    for race in races:
        validation = race.get("validation") or {}
        if validation.get("checksum") != "passed":
            raise RuntimeError("v2 race checksum did not pass")
        if validation.get("calculatedTotals") != validation.get("officialTotals"):
            raise RuntimeError("v2 race checksum totals disagree")
        geography = race.get("geography") or []
        if {g.get("county") for g in geography} != EXPECTED_CD9:
            raise RuntimeError("v2 race geography is incomplete")


def frontend_payload(data: dict) -> dict:
    election = data.get("election") or {}
    races = []
    for race in data.get("races") or []:
        races.append(
            {
                "id": race.get("id"),
                "name": "REP Representative in Congress, District 9",
                "office": race.get("office"),
                "district": race.get("district"),
                "party": race.get("party"),
                "candidates": race.get("candidates") or [],
                "geography": race.get("geography") or [],
                "source": race.get("source"),
                "validation": race.get("validation"),
            }
        )

    return {
        "schemaVersion": data.get("schemaVersion", 2),
        "scope": "Florida Congressional District 9",
        "district": 9,
        "election": election.get("name", "2026 Florida Primary Election"),
        "electionDate": election.get("date", "2026-08-18"),
        "source": "Florida Department of State - Florida Election Watch",
        "sourceUrl": races[0].get("source", {}).get("url") if races else None,
        "countiesIncluded": 7,
        "countiesExpected": 7,
        "countyNames": sorted(EXPECTED_CD9),
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
    validate_cd9(data)
    published = frontend_payload(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(published, indent=2) + "\n")
    print("PUBLISHED: validated v2 CD9 -> existing Election Center contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
