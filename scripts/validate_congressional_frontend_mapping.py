#!/usr/bin/env python3
"""Prove county U.S. House races map uniquely to verified districtwide v2 races.

This is an integration guard, not an ingestion source. It reads the existing county
frontend files named by data/manifest.json and matches House races to the verified
congressional publication payload by party plus exact normalized candidate set.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def party_for(race: dict) -> str:
    parties = {str(c.get("party") or "").upper() for c in race.get("candidates") or [] if c.get("party")}
    if len(parties) == 1:
        party = next(iter(parties))
        if party in {"REP", "DEM"}:
            return party
    name = str(race.get("name") or "")
    match = re.match(r"^(REP|DEM)\b", name, re.I)
    return match.group(1).upper() if match else ""


def candidate_key(race: dict) -> tuple[str, ...]:
    names = [key(c.get("name")) for c in race.get("candidates") or []]
    names = [name for name in names if name]
    return tuple(sorted(names))


def is_house_race(race: dict) -> bool:
    name = str(race.get("name") or "").lower()
    return "representative in congress" in name and "state representative" not in name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--congressional", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    congressional = json.loads(args.congressional.read_text())
    if congressional.get("coverageComplete") is not True or congressional.get("displayStatus") != "complete":
        raise RuntimeError("published congressional payload is not safe")

    district_index: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
    for race in congressional.get("races") or []:
        party = str(race.get("party") or "").upper()
        candidates = candidate_key(race)
        if not party or not candidates:
            raise RuntimeError(f"invalid congressional race identity: {race.get('id')}")
        district_index.setdefault((party, candidates), []).append(race)

    mappings = []
    unmatched = []
    ambiguous = []
    connected_counties = 0
    house_races_seen = 0

    for county, entry in (manifest.get("counties") or {}).items():
        if not entry.get("connected") or not entry.get("file"):
            continue
        connected_counties += 1
        county_file = Path(entry["file"])
        if not county_file.exists():
            raise RuntimeError(f"connected county file missing: {county}: {county_file}")
        data = json.loads(county_file.read_text())
        for race in data.get("races") or []:
            if not is_house_race(race):
                continue
            house_races_seen += 1
            party = party_for(race)
            candidates = candidate_key(race)
            matches = district_index.get((party, candidates), [])
            record = {
                "county": county,
                "countyRace": race.get("name"),
                "party": party,
                "candidateKey": list(candidates),
            }
            if len(matches) == 1:
                match = matches[0]
                record.update({
                    "district": match.get("district"),
                    "districtRaceId": match.get("id"),
                    "districtCounties": match.get("countyNames") or [],
                })
                if county not in set(match.get("countyNames") or []):
                    raise RuntimeError(
                        f"candidate-set match puts {county} outside District {match.get('district')} geography"
                    )
                mappings.append(record)
            elif not matches:
                unmatched.append(record)
            else:
                record["matchingRaceIds"] = [m.get("id") for m in matches]
                ambiguous.append(record)

    if ambiguous:
        raise RuntimeError(f"ambiguous congressional mappings: {ambiguous}")

    indian = [m for m in mappings if m["county"] == "Indian River" and m["party"] == "REP"]
    if len(indian) != 1 or indian[0].get("district") != 9:
        raise RuntimeError(f"Indian River REP congressional proof failed: {indian}")

    result = {
        "status": "passed",
        "matchingRule": "party + exact normalized candidate set; matched county must belong to official district geography",
        "connectedCountiesInspected": connected_counties,
        "countyHouseRacesSeen": house_races_seen,
        "uniqueMappings": len(mappings),
        "unmatchedCountyHouseRaces": unmatched,
        "ambiguousCountyHouseRaces": ambiguous,
        "mappings": mappings,
        "proofs": {
            "indianRiverRepDistrict": indian[0]["district"],
            "indianRiverRepRaceId": indian[0]["districtRaceId"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"PASS: {len(mappings)}/{house_races_seen} county House races uniquely mapped; "
        f"{len(unmatched)} unmatched; Indian River REP -> District 9"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
