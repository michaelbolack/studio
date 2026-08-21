#!/usr/bin/env python3
"""Build the fail-closed 2026 General Election county source inventory."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


EXPECTED_COUNTIES = 67
GENERAL_ELECTION_ID = "2026-fl-general"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def source_family(county, source_url):
    host = urlparse(source_url or "").netloc.lower()
    if "clarityelections.com" in host or "votepinellas.gov" in host:
        return "clarity-browser-session"
    if county == "Broward":
        return "broward-html"
    if county == "Seminole":
        return "seminole-html"
    return "standard-florida-enr"


def preserved_general_fields(existing):
    if not isinstance(existing, dict):
        return {
            "status": "not-discovered",
            "sourceUrl": None,
            "electionId": None,
            "validatedAt": None,
            "validationEvidence": None,
        }
    return {
        "status": existing.get("status", "not-discovered"),
        "sourceUrl": existing.get("sourceUrl"),
        "electionId": existing.get("electionId"),
        "validatedAt": existing.get("validatedAt"),
        "validationEvidence": existing.get("validationEvidence"),
    }


def build_inventory(manifest, existing=None, generated_at=None):
    existing_counties = (existing or {}).get("counties", {})
    counties = {}
    for county, entry in sorted(manifest.get("counties", {}).items()):
        baseline_url = entry.get("sourceUrl")
        general = preserved_general_fields(existing_counties.get(county, {}).get("generalElection"))
        counties[county] = {
            "sourceFamily": source_family(county, baseline_url),
            "baselineElection": "2026-fl-primary",
            "baselineSourceUrl": baseline_url,
            "baselineAdapter": entry.get("adapter"),
            "productionDataFile": entry.get("file"),
            "geographyPreserved": bool(entry.get("file")),
            "generalElection": general,
        }

    family_counts = Counter(entry["sourceFamily"] for entry in counties.values())
    discovered = sum(
        1 for entry in counties.values()
        if entry["generalElection"]["status"] in {"discovered", "validated"}
    )
    validated = sum(
        1 for entry in counties.values()
        if entry["generalElection"]["status"] == "validated"
    )
    clarity_validated = sum(
        1 for entry in counties.values()
        if entry["sourceFamily"] == "clarity-browser-session"
        and entry["generalElection"]["status"] == "validated"
    )

    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": 1,
        "electionId": GENERAL_ELECTION_ID,
        "electionDate": "2026-11-03",
        "generatedAt": generated_at,
        "activationPolicy": "fail-closed",
        "summary": {
            "countiesInventoried": len(counties),
            "countiesExpected": EXPECTED_COUNTIES,
            "allCountiesInventoried": len(counties) == EXPECTED_COUNTIES,
            "generalSourcesDiscovered": discovered,
            "generalSourcesValidated": validated,
            "claritySourcesValidated": clarity_validated,
            "claritySourcesExpected": 3,
            "allGeneralSourcesValidated": validated == EXPECTED_COUNTIES,
            "sourceFamilies": dict(sorted(family_counts.items())),
        },
        "counties": counties,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/manifest.json")
    parser.add_argument("--output", default="data/general-source-readiness.json")
    args = parser.parse_args()

    output_path = Path(args.output)
    existing = load_json(output_path) if output_path.exists() else None
    inventory = build_inventory(load_json(args.manifest), existing=existing)
    atomic_json_write(output_path, inventory)
    print(json.dumps(inventory["summary"], indent=2))


if __name__ == "__main__":
    main()
