"""Research-only Georgia result validation helpers.

These helpers are deliberately not a StateElectionAdapter and are not registered in
the adapter factory. They let us exercise Georgia's official county-breakout shape
against the 159-county reference index while Georgia remains disabled.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .local import LocalJurisdiction, index_local_jurisdictions
from .onboarding import load_onboarding_profile
from .registry import RegistryError, get_jurisdiction

DEFAULT_LOCAL_INDEX = Path(__file__).resolve().parents[2] / "data" / "jurisdictions" / "ga" / "local.json"


def load_georgia_research_counties(path: Path | str = DEFAULT_LOCAL_INDEX) -> list[dict[str, Any]]:
    """Load Georgia's reference counties without activating Georgia."""
    jurisdiction = get_jurisdiction("GA")
    if jurisdiction.get("enabled"):
        raise RegistryError("Georgia research loader must not be used after activation")
    profile = load_onboarding_profile("GA")
    payload = json.loads(Path(path).read_text())
    if payload.get("state") != "GA":
        raise RegistryError("Georgia local research index state mismatch")
    raw = payload.get("jurisdictions")
    if not isinstance(raw, list) or not raw:
        raise RegistryError("Georgia local research index is empty")
    items = [LocalJurisdiction("GA", x["name"], x.get("type", "county"), x.get("fips"), x.get("slug")) for x in raw]
    indexed = index_local_jurisdictions(items)
    counties = list(indexed.values())
    if len(counties) != profile["expectedLocalJurisdictions"]:
        raise RegistryError(
            f"Georgia local research index count mismatch: {len(counties)} != {profile['expectedLocalJurisdictions']}"
        )
    return counties


def validate_georgia_county_breakout(payload: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless a research contest contains all 159 Georgia counties.

    Expected fixture shape:
      {"contest": str, "candidates": [str, ...], "counties": {name: [votes, ...]},
       "officialTotals": [votes, ...]}
    """
    if not isinstance(payload, dict):
        raise RegistryError("Georgia research payload must be an object")
    contest = payload.get("contest")
    candidates = payload.get("candidates")
    county_votes = payload.get("counties")
    official = payload.get("officialTotals")
    if not isinstance(contest, str) or not contest.strip():
        raise RegistryError("Georgia research contest name is required")
    if not isinstance(candidates, list) or not candidates or any(not isinstance(x, str) or not x.strip() for x in candidates):
        raise RegistryError("Georgia research candidates are required")
    if len(set(candidates)) != len(candidates):
        raise RegistryError("Georgia research candidate names must be unique")
    if not isinstance(county_votes, dict):
        raise RegistryError("Georgia research county breakout is required")
    expected = load_georgia_research_counties()
    expected_names = {item["name"] for item in expected}
    actual_names = set(county_votes)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise RegistryError(f"Georgia county coverage mismatch: missing={missing}; unexpected={unexpected}")
    width = len(candidates)
    calculated = [0] * width
    for county in sorted(expected_names):
        row = county_votes[county]
        if not isinstance(row, list) or len(row) != width:
            raise RegistryError(f"Georgia county candidate-width mismatch: {county}")
        for i, value in enumerate(row):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise RegistryError(f"Georgia county vote must be a nonnegative integer: {county}")
            calculated[i] += value
    if not isinstance(official, list) or len(official) != width:
        raise RegistryError("Georgia official totals are required and must match candidate width")
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in official):
        raise RegistryError("Georgia official totals must be nonnegative integers")
    if calculated != official:
        raise RegistryError(f"Georgia county checksum failed: counties={calculated}; official={official}")
    return {
        "state": "GA",
        "status": "research-validated",
        "publishable": False,
        "contest": contest.strip(),
        "countyCoverage": f"{len(expected)}/{len(expected)}",
        "coverageComplete": True,
        "checksum": "passed",
        "calculatedTotals": calculated,
        "officialTotals": official,
    }
