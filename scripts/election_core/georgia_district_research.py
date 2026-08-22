"""Research-only Georgia district coverage validation.

This module validates district contests against an explicit set of Georgia counties.
It does not register Georgia as an adapter and never marks research output publishable.
"""
from __future__ import annotations
from typing import Any
from .georgia_research import load_georgia_research_counties
from .registry import RegistryError, get_jurisdiction

VALID_DISTRICT_TYPES = {"congressional", "state-senate", "state-house"}


def validate_georgia_district_breakout(
    *,
    district_type: str,
    district: int | str,
    expected_counties: list[str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate a Georgia district contest against explicitly expected counties."""
    if get_jurisdiction("GA").get("enabled"):
        raise RegistryError("Georgia district research validator must not be used after activation")
    if district_type not in VALID_DISTRICT_TYPES:
        raise RegistryError(f"unsupported Georgia district research type: {district_type}")
    district_text = str(district).strip()
    if not district_text:
        raise RegistryError("Georgia district identifier is required")
    if not isinstance(expected_counties, list) or not expected_counties:
        raise RegistryError("Georgia expected district counties are required")
    if len(set(expected_counties)) != len(expected_counties):
        raise RegistryError("Georgia expected district counties must be unique")

    valid_names = {item["name"] for item in load_georgia_research_counties()}
    unknown_expected = sorted(set(expected_counties) - valid_names)
    if unknown_expected:
        raise RegistryError("Georgia district expectation includes unknown counties: " + ", ".join(unknown_expected))

    if not isinstance(payload, dict):
        raise RegistryError("Georgia district research payload must be an object")
    contest = payload.get("contest")
    candidates = payload.get("candidates")
    county_votes = payload.get("counties")
    official = payload.get("officialTotals")
    if not isinstance(contest, str) or not contest.strip():
        raise RegistryError("Georgia district research contest name is required")
    if not isinstance(candidates, list) or not candidates or any(not isinstance(x, str) or not x.strip() for x in candidates):
        raise RegistryError("Georgia district research candidates are required")
    if len(set(candidates)) != len(candidates):
        raise RegistryError("Georgia district research candidate names must be unique")
    if not isinstance(county_votes, dict):
        raise RegistryError("Georgia district county breakout is required")

    expected = set(expected_counties)
    actual = set(county_votes)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise RegistryError(f"Georgia district coverage mismatch: missing={missing}; unexpected={unexpected}")

    width = len(candidates)
    calculated = [0] * width
    for county in sorted(expected):
        row = county_votes[county]
        if not isinstance(row, list) or len(row) != width:
            raise RegistryError(f"Georgia district candidate-width mismatch: {county}")
        for i, value in enumerate(row):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise RegistryError(f"Georgia district vote must be a nonnegative integer: {county}")
            calculated[i] += value

    if not isinstance(official, list) or len(official) != width:
        raise RegistryError("Georgia district official totals are required and must match candidate width")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in official):
        raise RegistryError("Georgia district official totals must be nonnegative integers")
    if calculated != official:
        raise RegistryError(f"Georgia district checksum failed: counties={calculated}; official={official}")

    return {
        "state": "GA",
        "status": "research-validated",
        "publishable": False,
        "districtType": district_type,
        "district": district_text,
        "contest": contest.strip(),
        "coverageComplete": True,
        "countyCoverage": f"{len(expected)}/{len(expected)}",
        "countyNames": sorted(expected),
        "checksum": "passed",
        "calculatedTotals": calculated,
        "officialTotals": official,
    }
