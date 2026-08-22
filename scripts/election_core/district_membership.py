"""Research-safe district membership model with split-county awareness.

Districts do not necessarily follow county boundaries. A county that is only partly
inside a district makes whole-county aggregation unsafe. This module records that
fact explicitly so downstream result code cannot silently sum full county totals.
"""
from __future__ import annotations
from typing import Any
from .registry import RegistryError

VALID_RELATIONS = {"whole", "partial"}


def validate_district_membership(
    *,
    state: str,
    district_type: str,
    district: int | str,
    members: list[dict[str, Any]],
    valid_counties: set[str],
) -> dict[str, Any]:
    code = state.strip().upper()
    district_id = str(district).strip()
    if len(code) != 2:
        raise RegistryError("district membership state must be a two-character code")
    if not district_id:
        raise RegistryError("district membership identifier is required")
    if not isinstance(members, list) or not members:
        raise RegistryError("district membership requires at least one county")

    normalized = []
    seen = set()
    partial = []
    for item in members:
        if not isinstance(item, dict):
            raise RegistryError("district membership entries must be objects")
        county = item.get("county")
        relation = item.get("relation")
        if not isinstance(county, str) or not county.strip():
            raise RegistryError("district membership county is required")
        county = county.strip()
        if county not in valid_counties:
            raise RegistryError(f"district membership contains unknown county: {county}")
        if county in seen:
            raise RegistryError(f"district membership contains duplicate county: {county}")
        if relation not in VALID_RELATIONS:
            raise RegistryError(f"district membership relation must be whole or partial: {county}")
        seen.add(county)
        normalized.append({"county": county, "relation": relation})
        if relation == "partial":
            partial.append(county)

    return {
        "state": code,
        "districtType": district_type,
        "district": district_id,
        "members": normalized,
        "countyCount": len(normalized),
        "partialCount": len(partial),
        "partialCounties": sorted(partial),
        "countyAggregateSafe": not partial,
    }


def require_county_aggregate_safe(membership: dict[str, Any]) -> None:
    """Fail closed if full-county totals cannot represent the district exactly."""
    if membership.get("countyAggregateSafe") is not True:
        counties = membership.get("partialCounties") or []
        raise RegistryError(
            "district cannot be aggregated from whole-county totals; split counties: "
            + ", ".join(counties)
        )
