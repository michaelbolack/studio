#!/usr/bin/env python3
"""Inventory the county/local ingestion boundary for Election Center v2.

This does not run or repair the legacy county pipeline. It records the current safe
coverage baseline: normalized county feeds versus official-source fallback. Every one
of Florida's 67 counties must have an official results destination even when inline
normalization is unavailable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

COUNTIES = [
    "Alachua", "Baker", "Bay", "Bradford", "Brevard", "Broward", "Calhoun", "Charlotte",
    "Citrus", "Clay", "Collier", "Columbia", "DeSoto", "Dixie", "Duval", "Escambia",
    "Flagler", "Franklin", "Gadsden", "Gilchrist", "Glades", "Gulf", "Hamilton", "Hardee",
    "Hendry", "Hernando", "Highlands", "Hillsborough", "Holmes", "Indian River", "Jackson",
    "Jefferson", "Lafayette", "Lake", "Lee", "Leon", "Levy", "Liberty", "Madison", "Manatee",
    "Marion", "Martin", "Miami-Dade", "Monroe", "Nassau", "Okaloosa", "Okeechobee", "Orange",
    "Osceola", "Palm Beach", "Pasco", "Pinellas", "Polk", "Putnam", "Santa Rosa", "Sarasota",
    "Seminole", "St. Johns", "St. Lucie", "Sumter", "Suwannee", "Taylor", "Union", "Volusia",
    "Wakulla", "Walton", "Washington",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    entries = manifest.get("counties") or {}
    missing_counties = [c for c in COUNTIES if c not in entries]
    extra_counties = sorted(set(entries) - set(COUNTIES))
    if missing_counties or extra_counties:
        raise RuntimeError(f"manifest county set mismatch: missing={missing_counties}; extra={extra_counties}")

    normalized = []
    fallback = []
    missing_source = []
    invalid_source = []
    for county in COUNTIES:
        entry = entries[county]
        url = str(entry.get("sourceUrl") or "").strip()
        if not url:
            missing_source.append(county)
        else:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                invalid_source.append({"county": county, "sourceUrl": url})
        if entry.get("connected") and entry.get("file"):
            normalized.append({
                "county": county,
                "file": entry.get("file"),
                "sourceUrl": url,
                "adapter": entry.get("adapter"),
                "races": entry.get("races"),
            })
        else:
            fallback.append({
                "county": county,
                "sourceUrl": url,
                "reason": entry.get("error") or "normalized feed unavailable",
                "validationFailed": bool(entry.get("validationFailed")),
            })

    missing_files = [x for x in normalized if not Path(x["file"]).exists()]
    if missing_source or invalid_source or missing_files:
        raise RuntimeError(
            f"county fallback contract invalid: missingSource={missing_source}; "
            f"invalidSource={invalid_source}; missingFiles={[x['county'] for x in missing_files]}"
        )

    output = {
        "status": "passed",
        "scope": "Florida county/local ingestion baseline",
        "policy": "Use normalized county Supervisor of Elections results when safely available; otherwise fail closed to the county's official results destination.",
        "countiesExpected": 67,
        "countiesWithOfficialDestination": 67,
        "normalizedCounties": len(normalized),
        "officialFallbackCounties": len(fallback),
        "normalized": normalized,
        "officialFallback": fallback,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"PASS: 67/67 official county destinations; {len(normalized)} normalized; {len(fallback)} official fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
