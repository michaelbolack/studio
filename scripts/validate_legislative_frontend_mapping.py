#!/usr/bin/env python3
"""Prove county State House/Senate races map uniquely to verified districtwide v2 races."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def office_base(name: str) -> str:
    name = re.sub(r"^(REP|DEM)\s+", "", str(name or ""), flags=re.I)
    name = re.sub(r"\s*\((REP|DEM)\)\s*$", "", name, flags=re.I)
    name = re.sub(r"\s*\(Vote For \d+\)\s*$", "", name, flags=re.I)
    return name.strip()


def office_for(race: dict) -> str:
    name = office_base(race.get("name") or "").lower()
    # County feeds are not perfectly consistent. Washington County currently uses
    # "United State Senator" (singular State), which must never be mistaken for a
    # Florida State Senate contest merely because it contains "state senator".
    if "united states senator" in name or "united state senator" in name or "u.s. senator" in name or "us senator" in name:
        return ""
    if "state representative" in name:
        return "State Representative"
    if "state senator" in name or "state senate" in name:
        return "State Senator"
    return ""


def party_for(race: dict) -> str:
    parties = {str(c.get("party") or "").upper() for c in race.get("candidates") or [] if c.get("party")}
    if len(parties) == 1:
        party = next(iter(parties))
        if party in {"REP", "DEM"}:
            return party
    match = re.match(r"^(REP|DEM)\b", str(race.get("name") or ""), re.I)
    return match.group(1).upper() if match else ""


def candidate_key(race: dict) -> tuple[str, ...]:
    names = [key(c.get("name")) for c in race.get("candidates") or []]
    return tuple(sorted(name for name in names if name))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--legislative", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    legislative = json.loads(args.legislative.read_text())
    if legislative.get("coverageComplete") is not True or legislative.get("displayStatus") != "complete":
        raise RuntimeError("published legislative payload is not safe")

    index: dict[tuple[str, str, tuple[str, ...]], list[dict]] = {}
    for race in legislative.get("races") or []:
        identity = (race.get("office"), str(race.get("party") or "").upper(), candidate_key(race))
        index.setdefault(identity, []).append(race)

    mappings = []
    unmatched = []
    ambiguous = []
    house_seen = 0
    senate_seen = 0
    connected = 0
    for county, entry in (manifest.get("counties") or {}).items():
        if not entry.get("connected") or not entry.get("file"):
            continue
        connected += 1
        path = Path(entry["file"])
        if not path.exists():
            raise RuntimeError(f"connected county file missing: {county}: {path}")
        data = json.loads(path.read_text())
        for race in data.get("races") or []:
            office = office_for(race)
            if not office:
                continue
            if office == "State Representative":
                house_seen += 1
            else:
                senate_seen += 1
            party = party_for(race)
            candidates = candidate_key(race)
            matches = index.get((office, party, candidates), [])
            record = {
                "county": county,
                "countyRace": race.get("name"),
                "office": office,
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
                        f"candidate-set match puts {county} outside {office} District {match.get('district')} geography"
                    )
                mappings.append(record)
            elif not matches:
                unmatched.append(record)
            else:
                record["matchingRaceIds"] = [m.get("id") for m in matches]
                ambiguous.append(record)

    if ambiguous:
        raise RuntimeError(f"ambiguous legislative mappings: {ambiguous}")
    if unmatched:
        raise RuntimeError(f"unmatched connected-county legislative races: {unmatched}")
    if not mappings:
        raise RuntimeError("no connected-county legislative races were mapped")

    result = {
        "status": "passed",
        "matchingRule": "office + party + exact normalized candidate set; matched county must belong to official district geography",
        "connectedCountiesInspected": connected,
        "countyStateHouseRacesSeen": house_seen,
        "countyStateSenateRacesSeen": senate_seen,
        "uniqueMappings": len(mappings),
        "unmatchedCountyLegislativeRaces": unmatched,
        "ambiguousCountyLegislativeRaces": ambiguous,
        "mappings": mappings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS: {len(mappings)} county legislative races uniquely mapped; zero unmatched/ambiguous")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
