#!/usr/bin/env python3
"""Fail-closed validation for official Florida voter information."""

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "voter-information.json"
OPTIONAL_COUNTY_URL_FIELDS = (
    "registrationUrl",
    "voteByMailUrl",
    "earlyVotingUrl",
    "precinctUrl",
    "sampleBallotUrl",
    "contactUrl",
)


def is_https_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_document(document: dict, today: date | None = None) -> list[str]:
    """Return every contract violation without accepting partial data."""
    del today  # Reserved for freshness rules added with the repository dataset.
    errors = []
    if not isinstance(document, dict):
        return ["document must be an object"]

    if document.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not str(document.get("generatedAt", "")).strip():
        errors.append("generatedAt is required")

    election = document.get("election")
    if not isinstance(election, dict):
        errors.append("election is required")
    else:
        try:
            date.fromisoformat(str(election.get("date", "")))
        except ValueError:
            errors.append("election.date must be ISO YYYY-MM-DD")
        if not str(election.get("name", "")).strip():
            errors.append("election.name is required")
        if election.get("timeZone") != "America/New_York":
            errors.append("election.timeZone must be America/New_York")

    statewide = document.get("statewide")
    if not isinstance(statewide, dict):
        errors.append("statewide is required")
    else:
        if not str(statewide.get("sourceUrl", "")).strip():
            errors.append("statewide.sourceUrl is required")
        elif not is_https_url(statewide.get("sourceUrl")):
            errors.append("statewide.sourceUrl must be an HTTPS URL")
        if not str(statewide.get("officeName", "")).strip():
            errors.append("statewide.officeName is required")
        try:
            date.fromisoformat(str(statewide.get("verifiedAt", "")))
        except ValueError:
            errors.append("statewide.verifiedAt must be ISO YYYY-MM-DD")

    counties = document.get("counties")
    if not isinstance(counties, list):
        return errors + ["counties must be an array"]
    if len(counties) != 67:
        errors.append("counties must contain exactly 67 records")

    names = [str(county.get("name", "")).strip() for county in counties if isinstance(county, dict)]
    ids = [str(county.get("id", "")).strip() for county in counties if isinstance(county, dict)]
    if len({name.casefold() for name in names}) != len(names):
        errors.append("county names must be unique")
    if len(set(ids)) != len(ids):
        errors.append("county ids must be unique")
    if "indian river" not in {name.casefold() for name in names}:
        errors.append("Indian River County is required")

    for index, county in enumerate(counties):
        if not isinstance(county, dict):
            errors.append(f"county {index + 1} must be an object")
            continue
        name = str(county.get("name", "")).strip() or f"county {index + 1}"
        if not str(county.get("id", "")).strip():
            errors.append(f"{name}: id is required")
        if not str(county.get("name", "")).strip():
            errors.append(f"{name}: name is required")
        if not str(county.get("officeName", "")).strip():
            errors.append(f"{name}: officeName is required")
        if not str(county.get("officeUrl", "")).strip():
            errors.append(f"{name}: officeUrl is required")
        elif not is_https_url(county.get("officeUrl")):
            errors.append(f"{name}: officeUrl must be an HTTPS URL")
        for field in OPTIONAL_COUNTY_URL_FIELDS:
            value = county.get(field)
            if value is not None and not is_https_url(value):
                errors.append(f"{name}: {field} must be an HTTPS URL or null")

    return errors


def main():
    try:
        document = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = {"feature": "voter-information", "errors": [str(exc)], "passed": False}
        print(json.dumps(report, indent=2))
        raise SystemExit("Voter-information validation failed closed.") from exc

    errors = validate_document(document)
    counties = document.get("counties", []) if isinstance(document, dict) else []
    report = {
        "feature": "voter-information",
        "countiesValidated": len(counties) if isinstance(counties, list) else 0,
        "officialOfficeLinks": sum(
            1 for county in counties
            if isinstance(county, dict) and is_https_url(county.get("officeUrl"))
        ) if isinstance(counties, list) else 0,
        "errors": errors,
        "passed": not errors,
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Voter-information validation failed closed.")


if __name__ == "__main__":
    main()
