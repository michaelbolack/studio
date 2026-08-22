"""Georgia county/local ENR normalization.

Local pages are treated independently from the statewide election page. County
identity is required and aggregate leaders remain withheld until local reporting
is complete.
"""
from __future__ import annotations
from typing import Any
from .georgia_normalizer import normalize_georgia_contest


def normalize_georgia_county(county: str, fips: str, contests: list[dict[str, Any]]) -> dict[str, Any]:
    name = county.strip()
    code = fips.strip()
    if not name or len(code) != 5 or not code.isdigit() or not code.startswith("13"):
        raise ValueError("valid Georgia county name and FIPS are required")
    normalized = [normalize_georgia_contest(c, scope="local") for c in contests]
    complete = bool(normalized) and all(c["reporting"]["complete"] for c in normalized)
    return {
        "state": "GA",
        "scope": "local",
        "county": name,
        "fips": code,
        "jurisdictionId": f"GA-{code}",
        "status": "research-only",
        "publishable": False,
        "complete": complete,
        "contests": normalized,
    }


def validate_georgia_local_collection(counties: list[dict[str, Any]], expected_fips: set[str]) -> dict[str, Any]:
    seen = [str(c.get("fips", "")) for c in counties]
    if len(seen) != len(set(seen)):
        raise ValueError("duplicate Georgia county payload")
    missing = sorted(expected_fips - set(seen))
    unexpected = sorted(set(seen) - expected_fips)
    complete = not missing and not unexpected and all(c.get("complete") is True for c in counties)
    return {
        "state": "GA",
        "scope": "local",
        "expectedCount": len(expected_fips),
        "receivedCount": len(seen),
        "complete": complete,
        "missing": missing,
        "unexpected": unexpected,
        "publishable": False,
    }
