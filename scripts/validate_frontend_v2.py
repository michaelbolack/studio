#!/usr/bin/env python3
"""Static integration guard for the preserved Election Center frontend.

Confirms the page loads verified statewide/congressional v2 data and retains the
fail-closed district matching gate. JavaScript syntax is checked separately by the
workflow with Node.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, default=Path("index.html"))
    parser.add_argument("--congressional", type=Path, default=Path("data/congressional.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    html = args.html.read_text()
    congressional = json.loads(args.congressional.read_text())

    required = {
        "loads_congressional": "data/congressional.json" in html,
        "mapping_gate": "frontendMappingValidation?.status==='passed'" in html,
        "exact_candidate_match": "ck.length===keys.length&&ck.every((v,i)=>v===keys[i])" in html,
        "county_geography_gate": "cr.countyNames.includes(currentCounty)" in html,
        "generic_district_label": "Congressional District ${cr.district} — Districtwide" in html,
        "district_fail_closed": "aggregateMessage('Congressional district',null)" in html,
        "cd9_fallback_retained": "if(isCD9(r)&&cd9race)" in html,
        "statewide_load_retained": "data/statewide.json" in html,
        "county_manifest_retained": "data/manifest.json" in html,
    }
    failed = [name for name, ok in required.items() if not ok]
    if failed:
        raise RuntimeError("frontend integration requirements missing: " + ", ".join(failed))

    mapping = congressional.get("frontendMappingValidation") or {}
    if mapping.get("status") != "passed":
        raise RuntimeError("published congressional mapping validation is not passed")
    if mapping.get("ambiguousCountyHouseRaces"):
        raise RuntimeError("published congressional mapping contains ambiguous county races")
    if mapping.get("unmatchedCountyHouseRaces"):
        raise RuntimeError("published congressional mapping contains unmatched county races")
    if mapping.get("proofs", {}).get("indianRiverRepDistrict") != 9:
        raise RuntimeError("published Indian River -> District 9 proof missing")

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
            "status": mapping.get("status"),
            "connectedCountiesInspected": mapping.get("connectedCountiesInspected"),
            "countyHouseRacesSeen": mapping.get("countyHouseRacesSeen"),
            "uniqueMappings": mapping.get("uniqueMappings"),
            "unmatched": len(mapping.get("unmatchedCountyHouseRaces") or []),
            "ambiguous": len(mapping.get("ambiguousCountyHouseRaces") or []),
            "indianRiverRepDistrict": mapping.get("proofs", {}).get("indianRiverRepDistrict"),
        },
        "javascriptPath": str(script_path),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: Election Center frontend is wired to verified statewide/congressional v2 data and fails closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
