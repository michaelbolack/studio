"""Fail-closed readiness rules for district geography research.

Relationship files are convenient but are not required to begin safe onboarding.
When current-vintage TIGER geometry exists, research may proceed to geometry
intersection. Publication remains blocked until district membership is resolved.
"""
from __future__ import annotations
from typing import Any
from .registry import RegistryError, get_jurisdiction

VALID_METHODS = {"relationship-file", "geometry-intersection", "official-district-results"}


def assess_district_geography_readiness(
    *, state: str, district_type: str, vintage: str, method: str,
    source_available: bool, membership_resolved: bool,
) -> dict[str, Any]:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code)
    if jurisdiction.get("enabled"):
        raise RegistryError(f"research geography readiness is only for disabled jurisdictions: {code}")
    if district_type not in {"congressional", "state-senate", "state-house"}:
        raise RegistryError(f"unsupported district type: {district_type}")
    if method not in VALID_METHODS:
        raise RegistryError(f"unsupported geography method: {method}")
    if not vintage.strip():
        raise RegistryError("district geography vintage is required")
    if not source_available:
        return {"state": code, "status": "blocked-source-unavailable", "publishable": False}
    if not membership_resolved:
        return {
            "state": code,
            "status": "research-ready-membership-unresolved",
            "method": method,
            "vintage": vintage,
            "publishable": False,
        }
    return {
        "state": code,
        "status": "research-validated",
        "method": method,
        "vintage": vintage,
        "publishable": False,
    }
