#!/usr/bin/env python3
"""Translate validated legislative v2 output into the preserved Election Center contract."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def validate(data: dict) -> None:
    if data.get("status") != "publishable":
        raise RuntimeError("legislative v2 payload is not publishable")
    if data.get("coverageComplete") is not True or data.get("mapReady") is not True:
        raise RuntimeError("legislative v2 payload is incomplete")
    races = data.get("races") or []
    if not races or len(races) != data.get("contestsDiscovered"):
        raise RuntimeError("legislative discovery count mismatch")
    combos = [(r.get("office"), r.get("district"), r.get("party")) for r in races]
    if len(combos) != len(set(combos)):
        raise RuntimeError("duplicate legislative office/district/party contests")
    for race in races:
        if race.get("office") not in {"State Representative", "State Senator"}:
            raise RuntimeError(f"unexpected legislative office: {race.get('office')}")
        validation = race.get("validation") or {}
        if validation.get("checksum") != "passed":
            raise RuntimeError(f"checksum failed: {race.get('id')}")
        if validation.get("calculatedTotals") != validation.get("officialTotals"):
            raise RuntimeError(f"checksum totals disagree: {race.get('id')}")
        geography = race.get("geography") or []
        if not geography or {g.get("county") for g in geography} != set(race.get("countyNames") or []):
            raise RuntimeError(f"geography mismatch: {race.get('id')}")


def frontend_payload(data: dict) -> dict:
    election = data.get("election") or {}
    races = []
    for race in data.get("races") or []:
        count = race.get("countiesIncluded") or len(race.get("geography") or [])
        races.append({
            "id": race.get("id"),
            "name": f"{race.get('party')} {race.get('office')}, District {race.get('district')}",
            "office": race.get("office"),
            "district": race.get("district"),
            "party": race.get("party"),
            "type": "legislative",
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
        "scope": "Florida Legislative Districts",
        "election": election.get("name", "2026 Florida Primary Election"),
        "electionDate": election.get("date", "2026-08-18"),
        "source": "Florida Department of State - Florida Election Watch",
        "sourceUrl": "https://floridaelectionwatch.gov/DistrictOffices",
        "coverageComplete": True,
        "mapReady": True,
        "contestsDiscovered": data.get("contestsDiscovered"),
        "houseDistrictsCovered": data.get("houseDistrictsCovered") or [],
        "senateDistrictsCovered": data.get("senateDistrictsCovered") or [],
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

    mapping_path = args.output.with_name("legislative-mapping.json")
    validator = Path(__file__).with_name("validate_legislative_frontend_mapping.py")
    subprocess.run([
        sys.executable, str(validator),
        "--manifest", "data/manifest.json",
        "--legislative", str(args.output),
        "--output", str(mapping_path),
    ], check=True)
    mapping = json.loads(mapping_path.read_text())
    output["frontendMappingValidation"] = {
        "status": mapping.get("status"),
        "matchingRule": mapping.get("matchingRule"),
        "connectedCountiesInspected": mapping.get("connectedCountiesInspected"),
        "countyStateHouseRacesSeen": mapping.get("countyStateHouseRacesSeen"),
        "countyStateSenateRacesSeen": mapping.get("countyStateSenateRacesSeen"),
        "uniqueMappings": mapping.get("uniqueMappings"),
        "unmatchedCountyLegislativeRaces": mapping.get("unmatchedCountyLegislativeRaces") or [],
        "ambiguousCountyLegislativeRaces": mapping.get("ambiguousCountyLegislativeRaces") or [],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"PUBLISHED: validated legislative v2; {mapping.get('uniqueMappings')} county races uniquely mapped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
