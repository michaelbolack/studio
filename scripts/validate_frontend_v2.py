#!/usr/bin/env python3
"""Static integration guard for the preserved Election Center frontend.

Confirms the page loads verified statewide, congressional, and legislative v2 data,
retains exact district matching/geography gates, and fails closed. JavaScript syntax
is checked separately by the workflow with Node.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def require_safe_mapping(mapping: dict, label: str, unmatched_key: str, ambiguous_key: str) -> None:
    if mapping.get("status") != "passed":
        raise RuntimeError(f"published {label} mapping validation is not passed")
    if mapping.get(ambiguous_key):
        raise RuntimeError(f"published {label} mapping contains ambiguous county races")
    if mapping.get(unmatched_key):
        raise RuntimeError(f"published {label} mapping contains unmatched county races")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, default=Path("index.html"))
    parser.add_argument("--congressional", type=Path, default=Path("data/congressional.json"))
    parser.add_argument("--legislative", type=Path, default=Path("data/legislative.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    html = args.html.read_text()
    congressional = json.loads(args.congressional.read_text())
    legislative = json.loads(args.legislative.read_text())

    required = {
        "loads_congressional": "data/congressional.json" in html,
        "loads_legislative": "data/legislative.json" in html,
        "congressional_mapping_gate": "congressional?.frontendMappingValidation?.status==='passed'" in html,
        "legislative_mapping_gate": "legislative?.frontendMappingValidation?.status==='passed'" in html,
        "congressional_exact_candidate_match": "ck.length===keys.length&&ck.every((v,i)=>v===keys[i])" in html,
        "legislative_exact_candidate_match": "lk.length===keys.length&&lk.every((v,i)=>v===keys[i])" in html,
        "congressional_county_geography_gate": "cr.countyNames.includes(currentCounty)" in html,
        "legislative_county_geography_gate": "lr.countyNames.includes(currentCounty)" in html,
        "generic_congressional_label": "Congressional District ${cr.district} — Districtwide" in html,
        "generic_legislative_label": "${lr.office} District ${lr.district} — Districtwide" in html,
        "congressional_fail_closed": "aggregateMessage('Congressional district',null)" in html,
        "legislative_fail_closed": "aggregateMessage(`${lo} district`,null)" in html,
        "us_senate_typo_exclusion": "o.includes('united state senator')" in html,
        "cd9_fallback_retained": "if(isCD9(r)&&cd9race)" in html,
        "statewide_load_retained": "data/statewide.json" in html,
        "county_manifest_retained": "data/manifest.json" in html,
    }
    failed = [name for name, ok in required.items() if not ok]
    if failed:
        raise RuntimeError("frontend integration requirements missing: " + ", ".join(failed))

    congress_mapping = congressional.get("frontendMappingValidation") or {}
    require_safe_mapping(
        congress_mapping,
        "congressional",
        "unmatchedCountyHouseRaces",
        "ambiguousCountyHouseRaces",
    )
    if congress_mapping.get("proofs", {}).get("indianRiverRepDistrict") != 9:
        raise RuntimeError("published Indian River -> District 9 proof missing")

    legislative_mapping = legislative.get("frontendMappingValidation") or {}
    require_safe_mapping(
        legislative_mapping,
        "legislative",
        "unmatchedCountyLegislativeRaces",
        "ambiguousCountyLegislativeRaces",
    )
    if legislative_mapping.get("uniqueMappings", 0) <= 0:
        raise RuntimeError("published legislative mapping contains no verified county mappings")

    script_match = re.search(r"<script>(.*?)</script>", html, re.S | re.I)
    if not script_match:
        raise RuntimeError("Election Center inline script not found")
    script_path = args.output.with_suffix(".js")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_match.group(1).strip() + "\n")

    result = {
        "status": "passed",
        "checks": required,
        "congressionalMapping": {
            "status": congress_mapping.get("status"),
            "connectedCountiesInspected": congress_mapping.get("connectedCountiesInspected"),
            "countyHouseRacesSeen": congress_mapping.get("countyHouseRacesSeen"),
            "uniqueMappings": congress_mapping.get("uniqueMappings"),
            "unmatched": len(congress_mapping.get("unmatchedCountyHouseRaces") or []),
            "ambiguous": len(congress_mapping.get("ambiguousCountyHouseRaces") or []),
            "indianRiverRepDistrict": congress_mapping.get("proofs", {}).get("indianRiverRepDistrict"),
        },
        "legislativeMapping": {
            "status": legislative_mapping.get("status"),
            "connectedCountiesInspected": legislative_mapping.get("connectedCountiesInspected"),
            "countyStateHouseRacesSeen": legislative_mapping.get("countyStateHouseRacesSeen"),
            "countyStateSenateRacesSeen": legislative_mapping.get("countyStateSenateRacesSeen"),
            "uniqueMappings": legislative_mapping.get("uniqueMappings"),
            "unmatched": len(legislative_mapping.get("unmatchedCountyLegislativeRaces") or []),
            "ambiguous": len(legislative_mapping.get("ambiguousCountyLegislativeRaces") or []),
        },
        "javascriptPath": str(script_path),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: Election Center frontend is wired to verified statewide/congressional/legislative v2 data and fails closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
